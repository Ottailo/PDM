"""Explicit bounded outbox worker; no threads or HTTP server start here."""
import hashlib
import json
import secrets
import smtplib
import ssl
import socket
import struct
import sys
import time
from datetime import timedelta
from email.message import EmailMessage
from flask import current_app
from sqlalchemy import or_, and_, text
from sqlalchemy.dialects.postgresql import insert
from app import db, create_app
from app.pilot.models import Job, Document, AuthToken, TenantSchedule, WorkerSchedule, WorkReminder, ReminderAttempt, WorkerHeartbeat, MaintenancePlan, PlanOccurrence, now
from app.pilot.storage import storage
from app.pilot.security import transaction_guard, tenant_lock
from app.pilot.sandbox_runner import parse_pdf, ParserRejected
from app.pilot.quota import reconcile_staging


class TerminalFailure(ParserRejected):
    pass


def scan_clamav(content):
    host,port = current_app.config['CLAMAV_HOST'],current_app.config['CLAMAV_PORT']
    if not host:
        raise RuntimeError('Malware scanner is not configured')
    deadline = time.monotonic()+45
    with socket.create_connection((host,port),timeout=15) as connection:
        def bounded_timeout():
            remaining = deadline-time.monotonic()
            if remaining<=0:
                raise TimeoutError('Scanner deadline exceeded')
            connection.settimeout(min(15,remaining))
        bounded_timeout()
        connection.sendall(b'zINSTREAM\0')
        for offset in range(0,len(content),65536):
            bounded_timeout()
            chunk = content[offset:offset+65536]
            connection.sendall(struct.pack('!I',len(chunk))+chunk)
        bounded_timeout()
        connection.sendall(struct.pack('!I',0))
        response = b''
        while not response.endswith(b'\0'):
            bounded_timeout()
            part = connection.recv(1024)
            if not part:
                break
            response += part
            if len(response)>4096:
                raise RuntimeError('Invalid scanner response')
    message = response.decode('utf-8',errors='replace').strip('\0\r\n')
    if message.endswith(' FOUND'):
        raise TerminalFailure('Malware detected; document remains quarantined')
    if message!='stream: OK':
        raise RuntimeError('Scanner did not return a clean verdict')
    return True


def send_mail(payload,identity):
    from app.pilot.auth import decrypt
    message = EmailMessage()
    message['From'] = current_app.config['SMTP_FROM']
    message['To'] = payload['to']
    message['Subject'] = payload['subject']
    message['Message-ID'] = f'<{hashlib.sha256(identity.encode()).hexdigest()}@machivital.local>'
    message.set_content(decrypt(payload['body_encrypted']))
    # Adapter injection is forbidden outside explicit TESTING mode.
    adapter = current_app.config.get('TEST_MAIL_ADAPTER')
    if current_app.testing and adapter:
        adapter(message)
        return
    host = current_app.config['SMTP_HOST']
    if not host:
        raise RuntimeError('SMTP delivery is not configured')
    with smtplib.SMTP(host,current_app.config['SMTP_PORT'],timeout=15) as smtp:
        smtp.ehlo()
        if current_app.config['SMTP_STARTTLS']:
            smtp.starttls(context=ssl.create_default_context())
            smtp.ehlo()
        if current_app.config.get('SMTP_USERNAME'):
            smtp.login(current_app.config['SMTP_USERNAME'],current_app.config['SMTP_PASSWORD'])
        refused = smtp.send_message(message)
        if refused:
            raise smtplib.SMTPRecipientsRefused(refused)


def ready_jobs():
    return or_(and_(Job.state=='queued',Job.available_at<=now()),and_(Job.state=='running',Job.lease_until<=now()))


def valid_mail(token,job):
    return (token is not None and token.consumed_at is None and token.expires_at>now()
            and token.company_id==job.company_id and job.identity==f'auth-token:{token.id}'
            and job.payload.get('to')==token.email)


def cancel_job(row):
    row.state,row.lease_token,row.lease_until,row.payload = 'cancelled',None,None,{}


def claim_job(selection):
    transaction_guard()
    # Serial scheduler admission prevents two claims racing the per-tenant lease cap.
    db.session.execute(text('SELECT pg_advisory_xact_lock(73119401003)'))
    db.session.execute(insert(WorkerSchedule).values(id=1).on_conflict_do_nothing())
    scheduler = db.session.get(WorkerSchedule,1)
    if selection=='all':
        # Two service lanes rotate around the priority auth lane: auth is never queued behind PM,
        # but a continuous auth queue cannot starve documents or maintenance reminders.
        rotation = ['mail','document','mail','maintenance_mail']
        position = scheduler.rotation_cursor or 0
        kinds = rotation[position:]+rotation[:position]
    else:
        kinds = [selection]
    for kind in kinds:
        candidate = None
        if kind in {'document','maintenance_mail'}:
            db.session.execute(insert(TenantSchedule).from_select(['company_id'],db.select(Job.company_id).where(Job.kind==kind,Job.company_id.is_not(None),ready_jobs()).distinct().limit(10000)).on_conflict_do_nothing())
            candidates = db.session.execute(db.select(TenantSchedule).where(TenantSchedule.company_id.in_(db.select(Job.company_id).where(Job.kind==kind,ready_jobs()))).order_by(TenantSchedule.last_dispatched_at.asc().nullsfirst(),TenantSchedule.company_id).limit(100)).scalars().all()
            for schedule in candidates:
                cid = schedule.company_id
                live = db.session.scalar(db.select(Job.id).where(Job.company_id==cid,Job.kind==kind,Job.state=='running',Job.lease_until>now()).limit(1))
                if live:
                    continue
                candidate = db.session.execute(db.select(Job).where(Job.kind==kind,Job.company_id==cid,ready_jobs()).order_by(Job.available_at,Job.id).limit(1)).scalar_one_or_none()
                if candidate:
                    tenant_lock(cid)
                    last = db.session.scalar(db.select(db.func.max(TenantSchedule.last_dispatched_at)))
                    schedule.last_dispatched_at = max(now(),last+timedelta(microseconds=1)) if last else now()
                    break
        else:
            candidate = db.session.execute(db.select(Job).where(Job.kind=='mail',ready_jobs()).order_by(Job.available_at,Job.id).limit(1)).scalar_one_or_none()
        if not candidate:
            continue
        token = None
        if kind=='mail':
            token = db.session.execute(db.select(AuthToken).where(AuthToken.id==candidate.token_id).with_for_update()).scalar_one_or_none() if candidate.token_id else None
        if kind=='maintenance_mail':
            from app.pilot.scheduling import lock_plan
            reminder = db.session.get(WorkReminder,candidate.reminder_id) if candidate.reminder_id else None
            occurrence = db.session.get(PlanOccurrence,reminder.occurrence_id) if reminder else None
            if occurrence:
                lock_plan(occurrence.plan_id,candidate.company_id)
        row = db.session.execute(db.select(Job).where(Job.id==candidate.id).with_for_update().execution_options(populate_existing=True)).scalar_one()
        scheduler.last_kind = kind
        if selection=='all':
            scheduler.rotation_cursor = (position+kinds.index(kind)+1)%4
        if kind=='maintenance_mail':
            from app.pilot.scheduling import reminder_context
            if row.attempts>=4 and row.state=='running':
                row.state,row.lease_token,row.lease_until,row.error = 'failed',None,None,'Delivery retry limit reached.'
                if reminder and row.identity==f'pm-reminder:{reminder.id}':
                    reminder.state,reminder.error = 'failed','Delivery retry limit reached.'
            elif not reminder_context(row):
                cancel_job(row)
                if reminder and reminder.company_id==row.company_id and row.identity==f'pm-reminder:{reminder.id}' and reminder.state in {'queued','running','retrying'}:
                    reminder.state = 'cancelled'
        if kind=='mail' and not valid_mail(token,row):
            cancel_job(row)
        return row
    return None


def run_once(app,kind='all'):
    """Claim one tenant-fair job; release every authority/row lock before external I/O."""
    if kind not in {'all','mail','document','maintenance_mail'}:
        raise ValueError('Worker kind must be all, mail, document or maintenance_mail')
    # Bounded persisted-reservation cleanup also runs while the queue is idle.
    # It uses nonblocking blob fences and never scans arbitrary private files.
    reconcile_staging(app)
    with app.app_context():
        row = claim_job(kind)
        if not row:
            db.session.rollback()
            return {'processed':0}
        if row.state in {'cancelled','failed'}:
            state = row.state
            db.session.commit()
            return {'processed':1,'state':state}
        row.state = 'running'
        row.attempts += 1
        row.lease_until = now()+timedelta(minutes=3)
        lease = secrets.token_hex(24)
        row.lease_token = lease
        identity,job_id,kind,payload,cid,token_id = row.identity,row.id,row.kind,dict(row.payload),row.company_id,row.token_id
        doc = None
        reminder_id = row.reminder_id
        if kind=='maintenance_mail':
            reminder = db.session.get(WorkReminder,reminder_id)
            reminder.state = 'running'
            reminder.attempts += 1
        if kind=='document':
            doc = db.session.execute(db.select(Document).where(Document.id==payload.get('document_id')).with_for_update()).scalar_one_or_none()
            if not doc or doc.company_id!=cid or doc.status=='staging' or doc.storage_released_at or doc.deleted_at or doc.revision!=payload.get('revision') or identity!=f'document:{doc.id}:{doc.revision}':
                row.state,row.lease_token,row.lease_until,row.payload = 'cancelled',None,None,{}
                db.session.commit()
                return {'processed':1,'state':'cancelled'}
            doc.status = 'processing'
            doc.error = None
            blob_key,checksum = doc.blob_key,doc.checksum
        db.session.commit()
        error = None
        terminal = False
        pages = None
        try:
            if kind=='mail':
                # Revalidate immediately before delivery. Already-started SMTP is not recallable.
                transaction_guard()
                token = db.session.execute(db.select(AuthToken).where(AuthToken.id==token_id).with_for_update()).scalar_one_or_none()
                current = db.session.execute(db.select(Job).where(Job.id==job_id).with_for_update()).scalar_one()
                if current.lease_token!=lease or current.state!='running' or not valid_mail(token,current):
                    if current.lease_token==lease:
                        cancel_job(current)
                    db.session.commit()
                    return {'processed':1,'state':'cancelled'}
                db.session.commit()
                send_mail(payload,identity)
            elif kind=='maintenance_mail':
                from app.pilot.scheduling import lock_plan, reminder_context, mail_payload
                transaction_guard()
                tenant_lock(cid)
                reminder = db.session.get(WorkReminder,reminder_id)
                occurrence = db.session.get(PlanOccurrence,reminder.occurrence_id)
                lock_plan(occurrence.plan_id,cid)
                current = db.session.execute(db.select(Job).where(Job.id==job_id).with_for_update()).scalar_one()
                context = reminder_context(current)
                if current.lease_token!=lease or current.state!='running' or current.lease_until<=now() or not context:
                    if current.lease_token==lease:
                        cancel_job(current)
                        if reminder.state in {'queued','running','retrying'}:
                            reminder.state = 'cancelled'
                    db.session.commit()
                    return {'processed':1,'state':'cancelled'}
                payload = mail_payload(context)
                db.session.commit()  # No database/authority lock spans external SMTP.
                send_mail(payload,identity)
            elif kind=='document':
                content = storage().get(blob_key,app.config['PDF_MAX_BYTES'])
                if hashlib.sha256(content).hexdigest()!=checksum:
                    raise TerminalFailure('Stored document failed integrity verification')
                scanner = app.config.get('TEST_SCANNER') if app.testing else None
                verdict = scanner(content) if scanner else scan_clamav(content)
                if verdict is not True:
                    raise TerminalFailure('Scanner did not approve the document')
                parser = app.config.get('TEST_PARSER') if app.testing else None
                pages = parser(content) if parser else parse_pdf(content)
                if not isinstance(pages,list) or not pages or len(pages)>app.config['PDF_MAX_PAGES'] or any(not isinstance(p,str) or len(p)>100000 for p in pages) or sum(map(len,pages))>app.config['PDF_MAX_TEXT']:
                    raise TerminalFailure('Invalid parser output')
            else:
                raise TerminalFailure('Unsupported job kind')
        except Exception as failure:
            error = str(failure)[:300] or type(failure).__name__
            terminal = isinstance(failure,ParserRejected)
            if kind=='maintenance_mail':
                terminal = terminal or (isinstance(failure,smtplib.SMTPResponseException) and failure.smtp_code>=500)
                if isinstance(failure,smtplib.SMTPRecipientsRefused):
                    terminal = all(code>=500 for code,_ in failure.recipients.values())
                error = 'Recipient refused delivery.' if terminal else 'Mail delivery unavailable; retry pending.'
        db.session.expire_all()
        transaction_guard()
        if kind in {'document','maintenance_mail'}:
            tenant_lock(cid)
        if kind=='maintenance_mail':
            from app.pilot.scheduling import lock_plan
            occurrence = db.session.get(PlanOccurrence,db.session.get(WorkReminder,reminder_id).occurrence_id)
            lock_plan(occurrence.plan_id,cid)
        row = db.session.execute(db.select(Job).where(Job.id==job_id).with_for_update()).scalar_one()
        if row.lease_token!=lease or row.state!='running' or row.lease_until<=now():
            if kind=='maintenance_mail':
                db.session.add(ReminderAttempt(company_id=cid,reminder_id=reminder_id,lease_token=lease,
                    outcome='lease_lost',error='Delivery result could not be fenced.'))
                db.session.commit()
            else:
                db.session.rollback()
            return {'processed':1,'state':'lease_lost'}
        row.lease_token,row.lease_until = None,None
        if error:
            row.error = error
            row.state = 'failed' if terminal or row.attempts>=4 else 'queued'
            row.available_at = now()+timedelta(seconds=min(300,15*2**row.attempts))
        else:
            row.state,row.error,row.payload = 'done',None,{}  # Remove email-link ciphertext after acknowledgment.
        if kind=='document':
            doc = db.session.execute(db.select(Document).where(Document.id==payload['document_id']).with_for_update()).scalar_one_or_none()
            if doc and not doc.deleted_at and doc.revision==payload['revision']:
                doc.status = 'failed' if error else 'ready'
                doc.error = ('Security processing unavailable; queued for retry.' if error and row.state=='queued' else error)
                if not error:
                    doc.pages,doc.page_count = pages,len(pages)
        if kind=='maintenance_mail':
            reminder = db.session.execute(db.select(WorkReminder).where(WorkReminder.id==reminder_id).with_for_update()).scalar_one()
            reminder.state = ('failed' if row.state=='failed' else 'retrying') if error else 'accepted'
            reminder.error = error
            if not error:
                reminder.accepted_at = now()
            db.session.add(ReminderAttempt(company_id=cid,reminder_id=reminder_id,lease_token=lease,
                outcome=reminder.state,error=error))
        state = row.state
        db.session.commit()
        return {'processed':1,'state':state,'job_id':job_id}


def run_foreground(app, stop_event=None, max_cycles=None, idle_seconds=None):
    """Explicit service loop; callers own signals. No startup effects, threads or fake readiness."""
    from threading import Event
    from app.pilot.scheduling import tick
    stop = stop_event or Event()
    if max_cycles is not None and (type(max_cycles) is not int or not 1<=max_cycles<=1000000):
        raise ValueError('max_cycles must be a bounded positive integer')
    delay = app.config['WORKER_IDLE_SECONDS'] if idle_seconds is None else idle_seconds
    if not isinstance(delay,(int,float)) or not 0<delay<=60:
        raise ValueError('idle_seconds must be greater than zero and at most 60')
    identity = secrets.token_hex(24)
    cycles = processed = 0
    try:
        while not stop.is_set() and (max_cycles is None or cycles<max_cycles):
            tick(app)
            with app.app_context():
                heartbeat = db.session.get(WorkerHeartbeat,identity)
                if heartbeat is None:
                    heartbeat = WorkerHeartbeat(id=identity)
                    db.session.add(heartbeat)
                heartbeat.last_seen_at = heartbeat.last_tick_at = now()
                db.session.commit()
            result = run_once(app)
            processed += result['processed']
            cycles += 1
            if not result['processed']:
                stop.wait(delay)
    finally:
        with app.app_context():
            heartbeat = db.session.get(WorkerHeartbeat,identity)
            if heartbeat:
                heartbeat.stopped_at = now()
                db.session.commit()
    return {'cycles':cycles,'processed':processed,'worker_id':identity}


def run_service(app, seconds=None):
    """Foreground integration wrapper; optional duration is a monotonic deadline, not a test clock."""
    if seconds is not None and (not isinstance(seconds,(int,float)) or not 0<seconds<=86400):
        raise ValueError('seconds must be greater than zero and at most 86400')
    from threading import Event
    import signal
    stop = Event()
    deadline = time.monotonic()+seconds if seconds is not None else None
    class DeadlineStop:
        def is_set(self):
            return stop.is_set() or (deadline is not None and time.monotonic()>=deadline)
        def wait(self,delay):
            return stop.wait(min(delay,max(0,deadline-time.monotonic())) if deadline is not None else delay)
    previous = {}
    from threading import current_thread, main_thread
    if current_thread() is main_thread():
        for signum in (signal.SIGINT,signal.SIGTERM):
            previous[signum] = signal.getsignal(signum)
            signal.signal(signum,lambda *_:stop.set())
    try:
        return run_foreground(app,stop_event=DeadlineStop())
    finally:
        for signum,handler in previous.items():
            signal.signal(signum,handler)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Run bounded Stage 1 worker jobs explicitly')
    parser.add_argument('--max-jobs',type=int,default=1)
    parser.add_argument('--kind',choices=['mail','document','maintenance_mail','all'],default='all')
    parser.add_argument('--foreground',action='store_true')
    parser.add_argument('--seconds',type=float)
    parser.add_argument('--reconcile-staging',action='store_true')
    args = parser.parse_args()
    if not 1<=args.max_jobs<=100:
        parser.error('--max-jobs must be 1–100')
    app = create_app()
    if args.foreground:
        print(json.dumps(run_service(app,args.seconds)))
        return
    if args.seconds is not None:
        parser.error('--seconds requires --foreground')
    results = []
    reconciliation = reconcile_staging(app) if args.reconcile_staging else None
    for _ in range(args.max_jobs):
        result = run_once(app,args.kind)
        results.append(result)
        if not result['processed']:
            break
    print(json.dumps({'results':results,'reconciliation':reconciliation}))
    if any(r.get('state')=='failed' for r in results):
        sys.exit(1)


if __name__=='__main__':
    main()
