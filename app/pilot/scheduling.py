"""Bounded, tenant-fair anchored PM scheduler and background-safe domain operations."""
from datetime import timedelta
from flask import current_app
from sqlalchemy import func, text
from app import db
from app.models import Asset, Company, User
from app.pilot.calendar import Calendar
from app.pilot.models import (MaintenancePlan, PlanOccurrence, PlanEvent, WorkOrder, WorkReminder,
                              Job, ReminderAttempt, now)
from app.pilot.maintenance import create_work, eligible_member, MANAGERS
from app.pilot.security import APIError, transaction_guard, tenant_lock, iso

UNFINISHED = ('open','assigned','in_progress','blocked','awaiting_review')
PENDING = ('queued','running','retrying')
SCHEDULER_LOCK = 73119401003


def calendar_for(plan):
    return Calendar(plan.start_local, plan.timezone, plan.interval_unit, plan.interval_count)


def plan_event(plan, action, notes='', actor=None):
    db.session.add(PlanEvent(company_id=plan.company_id,plan_id=plan.id,action=action,
        actor_id=actor.id if actor else None,actor_name=actor.name if actor else 'Schedule',notes=notes))


def cursor(plan, index):
    plan.next_index = min(index,2147483647)
    try:
        slot = calendar_for(plan).slot(index)
    except (ValueError, OverflowError):
        plan.next_due_at = plan.next_due_local = None
        plan.blocked_reason = 'calendar_exhausted'
        return
    plan.next_due_at, plan.next_due_local = slot.scheduled_at, slot.scheduled_local


def lock_plan(identity, company_id):
    tenant_lock(company_id)
    db.session.execute(db.select(Company).where(Company.id==company_id).with_for_update()).scalar_one()
    plan = db.session.execute(db.select(MaintenancePlan).where(MaintenancePlan.id==identity,MaintenancePlan.company_id==company_id).with_for_update().execution_options(populate_existing=True)).scalar_one_or_none()
    if not plan:
        raise APIError('not_found','Record not found.',404)
    return plan


def lock_work(identity, company_id):
    tenant_lock(company_id)
    db.session.execute(db.select(Company).where(Company.id==company_id).with_for_update()).scalar_one()
    preview = db.session.execute(db.select(WorkOrder).where(WorkOrder.id==identity,WorkOrder.company_id==company_id)).scalar_one_or_none()
    if not preview:
        raise APIError('not_found','Record not found.',404)
    if preview.plan_id:
        db.session.execute(db.select(MaintenancePlan).where(MaintenancePlan.id==preview.plan_id).with_for_update()).scalar_one()
        # Same tenant fence as scheduler/worker. Jobs precede domain rows in every mutator.
        list(db.session.execute(db.select(Job).join(WorkReminder,Job.reminder_id==WorkReminder.id).where(
            WorkReminder.company_id==company_id,WorkReminder.work_order_id==identity).order_by(Job.id).with_for_update(of=Job)).scalars())
    return db.session.execute(db.select(WorkOrder).where(WorkOrder.id==identity).with_for_update().execution_options(populate_existing=True)).scalar_one()


def cancel_reminders(company_id, work_id=None, plan_id=None, recipient_id=None, stage=None):
    query = db.select(WorkReminder.id).where(WorkReminder.company_id==company_id,WorkReminder.state.in_(PENDING))
    if work_id is not None:
        query = query.where(WorkReminder.work_order_id==work_id)
    if plan_id is not None:
        query = query.join(PlanOccurrence,WorkReminder.occurrence_id==PlanOccurrence.id).where(PlanOccurrence.plan_id==plan_id)
    if recipient_id is not None:
        query = query.where(WorkReminder.recipient_id==recipient_id)
    if stage is not None:
        query = query.where(WorkReminder.stage==stage)
    ids = list(db.session.execute(query).scalars())
    if not ids:
        return
    jobs = db.session.execute(db.select(Job).where(Job.company_id==company_id,Job.reminder_id.in_(ids)).order_by(Job.id).with_for_update()).scalars().all()
    for job in jobs:
        if job.state in {'queued','running'}:
            job.state,job.payload,job.lease_token,job.lease_until = 'cancelled',{},None,None
    for reminder in db.session.execute(db.select(WorkReminder).where(WorkReminder.id.in_(ids)).order_by(WorkReminder.id).with_for_update()).scalars():
        reminder.state,reminder.error = 'cancelled',None


def reminder_identity(reminder):
    return f'pm-reminder:{reminder.id}'


def reminder_context(job):
    """No payload authority: every link and current recipient is checked against durable rows."""
    if job.kind!='maintenance_mail' or job.token_id is not None or not job.reminder_id or not job.company_id:
        return None
    reminder = db.session.get(WorkReminder,job.reminder_id)
    if not reminder or reminder.company_id!=job.company_id or job.identity!=reminder_identity(reminder):
        return None
    if reminder.state not in PENDING:
        return None
    work = db.session.get(WorkOrder,reminder.work_order_id)
    occurrence = db.session.get(PlanOccurrence,reminder.occurrence_id)
    plan = db.session.get(MaintenancePlan,occurrence.plan_id) if occurrence else None
    company = db.session.get(Company,job.company_id)
    if not work or not occurrence or not plan or not company or not company.is_active or not plan.enabled:
        return None
    if not (work.company_id==occurrence.company_id==plan.company_id==job.company_id):
        return None
    if work.plan_id!=plan.id or work.occurrence_id!=occurrence.id or occurrence.work_order_id!=work.id:
        return None
    if work.status not in UNFINISHED or work.notification_generation!=reminder.notification_generation or work.due_at is None:
        return None
    asset = db.session.get(Asset,work.asset_id)
    if not asset or asset.company_id!=company.id or asset.archived_at:
        return None
    expected = work.assignee_id if reminder.stage=='due' else occurrence.snapshot.get('escalation_member_id')
    if expected!=reminder.recipient_id:
        return None
    member = eligible_member(company.id,reminder.recipient_id,MANAGERS if reminder.stage=='overdue' else None)
    if not member:
        return None
    expected_time = work.due_at + timedelta(hours=24) if reminder.stage=='overdue' else work.due_at-timedelta(hours=occurrence.snapshot['reminder_hours'])
    if reminder.scheduled_at!=expected_time or reminder.scheduled_at>now():
        return None
    user = db.session.get(User,member.user_id)
    return reminder,work,occurrence,plan,user


def mail_payload(context):
    from app.pilot.auth import encrypt
    reminder,work,occurrence,plan,user = context
    from zoneinfo import ZoneInfo
    label = 'Maintenance due' if reminder.stage=='due' else 'Maintenance overdue'
    local_due = work.due_at.astimezone(ZoneInfo(occurrence.timezone)).strftime('%Y-%m-%dT%H:%M')
    message = (f'{label}: {work.number} — {work.title}\n\n'
               f'Scheduled: {iso(work.due_at)} (UTC)\nPlant schedule: {local_due} {occurrence.timezone}\n\n'
               f"Open the assigned work in Machivital:\n{current_app.config['APP_BASE_URL'].rstrip('/')}/app/maintenance/plans/{plan.id}\n\n"
               'Email acceptance is not acknowledgment or completed maintenance. Follow your site safety procedure.')
    return {'to':user.email,'subject':f'{label}: {work.number}','body_encrypted':encrypt(message)}


def pending_count(company_id):
    return db.session.scalar(db.select(func.count()).select_from(WorkReminder).where(WorkReminder.company_id==company_id,WorkReminder.state.in_(PENDING)))


def reminder_specs(work, occurrence):
    if work.due_at is None:
        return []
    specs = []
    if eligible_member(work.company_id,work.assignee_id):
        specs.append(('due',work.assignee_id,work.due_at-timedelta(hours=occurrence.snapshot['reminder_hours'])))
    escalation = occurrence.snapshot.get('escalation_member_id')
    if eligible_member(work.company_id,escalation,MANAGERS):
        specs.append(('overdue',escalation,work.due_at+timedelta(hours=24)))
    return specs


def ensure_reminders(work, occurrence):
    plan = db.session.get(MaintenancePlan,work.plan_id)
    if not plan.enabled or work.status not in UNFINISHED:
        return
    if work.due_at is None:
        plan.blocked_reason = 'needs_due_date'
        return
    specs = reminder_specs(work,occurrence)
    missing = []
    for stage,recipient,scheduled in specs:
        exists = db.session.scalar(db.select(WorkReminder.id).where(WorkReminder.occurrence_id==occurrence.id,
            WorkReminder.stage==stage,WorkReminder.recipient_id==recipient,WorkReminder.notification_generation==work.notification_generation))
        if not exists:
            missing.append((stage,recipient,scheduled))
    if pending_count(work.company_id)+len(missing)>current_app.config['PM_PENDING_REMINDER_LIMIT']:
        plan.blocked_reason = 'reminder_capacity'
        return
    for stage,recipient,scheduled in missing:
        reminder = WorkReminder(company_id=work.company_id,occurrence_id=occurrence.id,work_order_id=work.id,
            stage=stage,recipient_id=recipient,notification_generation=work.notification_generation,scheduled_at=scheduled)
        db.session.add(reminder)
        db.session.flush()
        # Content is regenerated only from authoritative rows immediately before delivery.
        db.session.add(Job(kind='maintenance_mail',company_id=work.company_id,reminder_id=reminder.id,
            identity=reminder_identity(reminder),payload={},available_at=scheduled))
    if work.assignee_id is None or not eligible_member(work.company_id,work.assignee_id):
        plan.blocked_reason = 'needs_assignment'
    elif occurrence.snapshot.get('escalation_member_id') and not eligible_member(work.company_id,occurrence.snapshot['escalation_member_id'],MANAGERS):
        plan.blocked_reason = 'invalid_escalation'
    elif plan.blocked_reason in {'needs_assignment','needs_due_date','reminder_capacity','invalid_escalation'}:
        plan.blocked_reason = None


def refresh_work_reminders(work):
    cancel_reminders(work.company_id,work_id=work.id)
    db.session.flush()
    occurrence = db.session.get(PlanOccurrence,work.occurrence_id)
    if occurrence:
        ensure_reminders(work,occurrence)


def skipped(plan, first, last, reason):
    if last < first:
        return
    cal = calendar_for(plan)
    plan_event(plan,'missed' if reason=='unfinished_work' else 'skip',
        f'{reason}: {last-first+1} anchor slots; {iso(cal.slot(first).scheduled_at)} through {iso(cal.slot(last).scheduled_at)}.')


def work_closed(work):
    plan = db.session.get(MaintenancePlan,work.plan_id)
    cancel_reminders(work.company_id,work_id=work.id)
    cal = calendar_for(plan)
    last = cal.latest_index(now())
    skipped(plan,plan.next_index,last,'closed_work')
    cursor(plan,max(plan.next_index,last+1))
    plan_event(plan,'work_closed',f'{work.number}: {work.status}; continue at the next future anchor.')


def process_plan(plan, company, instant):
    plan.last_tick_at = instant
    asset = db.session.get(Asset,plan.asset_id)
    if not company.is_active or not asset or asset.archived_at:
        plan.blocked_reason = 'inactive_company' if not company.is_active else 'archived_asset'
        cancel_reminders(company.id,plan_id=plan.id)
        return False
    cal = calendar_for(plan)
    latest = cal.latest_index(instant)
    work = db.session.execute(db.select(WorkOrder).where(WorkOrder.company_id==company.id,WorkOrder.plan_id==plan.id,WorkOrder.status.in_(UNFINISHED))).scalar_one_or_none()
    if work:
        # Job locks precede mutable domain rows; all competitors hold the tenant fence.
        list(db.session.execute(db.select(Job).join(WorkReminder,Job.reminder_id==WorkReminder.id).where(
            WorkReminder.company_id==company.id,WorkReminder.work_order_id==work.id).order_by(Job.id).with_for_update(of=Job)).scalars())
        work = db.session.execute(db.select(WorkOrder).where(WorkOrder.id==work.id).with_for_update()).scalar_one()
        skipped(plan,plan.next_index,latest,'unfinished_work')
        cursor(plan,max(plan.next_index,latest+1))
        occurrence = db.session.get(PlanOccurrence,work.occurrence_id)
        ensure_reminders(work,occurrence)
        return False
    index = max(plan.next_index,latest) if latest>=plan.next_index else plan.next_index
    try:
        slot = cal.slot(index)
    except (ValueError,OverflowError):
        cursor(plan,index)
        return False
    if slot.scheduled_at>instant+timedelta(hours=plan.reminder_hours):
        cursor(plan,index)
        return False
    count = db.session.scalar(db.select(func.count()).select_from(WorkOrder).where(WorkOrder.company_id==company.id,WorkOrder.plan_id.is_not(None),WorkOrder.status.in_(UNFINISHED)))
    if count>=current_app.config['PM_OPEN_WORK_LIMIT']:
        plan.blocked_reason = 'work_capacity'
        return False
    assigned = plan.assignee_id if eligible_member(company.id,plan.assignee_id) else None
    escalation = plan.escalation_member_id if eligible_member(company.id,plan.escalation_member_id,MANAGERS) else None
    needed = int(assigned is not None)+int(escalation is not None)
    if pending_count(company.id)+needed>current_app.config['PM_PENDING_REMINDER_LIMIT']:
        plan.blocked_reason = 'reminder_capacity'
        return False
    body = {'title':plan.title,'description':plan.description,'priority':plan.priority,'checklist':plan.checklist}
    snapshot = {**body,'assignee_id':plan.assignee_id,'escalation_member_id':plan.escalation_member_id,
        'reminder_hours':plan.reminder_hours,'timezone':plan.timezone,'start_local':plan.start_local,
        'interval_unit':plan.interval_unit,'interval_count':plan.interval_count,'effective_at':iso(plan.effective_at)}
    # Validate calendar overflow before allocating a work number.
    try:
        slot.scheduled_at + timedelta(hours=24)
        slot.scheduled_at - timedelta(hours=plan.reminder_hours)
    except OverflowError:
        plan.blocked_reason = 'calendar_exhausted'
        return False
    oid = db.session.scalar(text("SELECT nextval(pg_get_serial_sequence('plan_occurrences','id'))"))
    work = create_work(company,asset,body,assigned,slot.scheduled_at,plan.id,oid)
    missed = max(0,index-plan.next_index)
    occurrence = PlanOccurrence(id=oid,company_id=company.id,plan_id=plan.id,generation=plan.generation,
        slot_index=index,scheduled_at=slot.scheduled_at,scheduled_local=slot.scheduled_local,timezone=plan.timezone,
        snapshot=snapshot,work_order_id=work.id,missed_count=missed,
        missed_from=cal.slot(plan.next_index).scheduled_at if missed else None,
        missed_through=cal.slot(index-1).scheduled_at if missed else None)
    db.session.add(occurrence)
    db.session.flush()
    skipped(plan,plan.next_index,index-1,'downtime_coalesced')
    plan_event(plan,'schedule_create',f'{work.number}; generation {plan.generation}, slot {index}.')
    cursor(plan,index+1)
    plan.blocked_reason = None
    ensure_reminders(work,occurrence)
    return True


def tick(app, limit=None):
    """One atomic bounded pass. TEST_CLOCK is the only injected clock; no HTTP time controls."""
    with app.app_context():
        maximum = app.config['PM_TICK_LIMIT'] if limit is None else limit
        if type(maximum) is not int or not 1<=maximum<=app.config['PM_TICK_LIMIT']:
            raise ValueError('Tick limit exceeds the configured bound')
        transaction_guard()
        db.session.execute(text('SELECT pg_advisory_xact_lock(:key)'),{'key':SCHEDULER_LOCK})
        instant = now()
        # Least recently examined tenant, then plan: capacity-blocked plans cannot starve others.
        tenants = db.session.execute(db.select(MaintenancePlan.company_id,func.min(MaintenancePlan.last_tick_at).label('last_tick')).where(MaintenancePlan.enabled.is_(True)).group_by(MaintenancePlan.company_id).order_by(text('last_tick ASC NULLS FIRST'),MaintenancePlan.company_id).limit(maximum)).all()
        examined = created = 0
        previous_tick = db.session.scalar(db.select(func.max(MaintenancePlan.last_tick_at)))
        dispatch_time = max(instant,previous_tick+timedelta(microseconds=1)) if previous_tick else instant
        for cid,_ in tenants:
            if examined>=maximum:
                break
            tenant_lock(cid)
            company = db.session.execute(db.select(Company).where(Company.id==cid).with_for_update()).scalar_one()
            plans = db.session.execute(db.select(MaintenancePlan).where(MaintenancePlan.company_id==cid,MaintenancePlan.enabled.is_(True)).order_by(MaintenancePlan.last_tick_at.asc().nullsfirst(),MaintenancePlan.id).limit(min(app.config['PM_TENANT_TICK_LIMIT'],maximum-examined)).with_for_update()).scalars().all()
            for plan in plans:
                created += int(process_plan(plan,company,instant))
                plan.last_tick_at = dispatch_time
                examined += 1
        db.session.commit()
        return {'examined':examined,'created':created,'at':iso(instant)}
