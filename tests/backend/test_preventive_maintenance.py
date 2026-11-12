"""Disposable PostgreSQL PM regression suite; coordinator runs it serially."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import smtplib
import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from flask_migrate import downgrade
from app import db, create_app
from app.pilot.models import (MaintenancePlan, PlanOccurrence, WorkOrder, WorkEvent, WorkReminder,
                              ReminderAttempt, Job, PlanEvent, Membership)
from app.pilot.scheduling import tick
from app.pilot.worker import run_once, run_foreground
from conftest import api, create_asset, register, ROOT


def clock(app, value='2026-01-01T08:00:00+00:00'):
    box = [datetime.fromisoformat(value)]
    app.config['TEST_CLOCK'] = lambda:box[0]
    return box


def make_plan(client, asset, member, **extra):
    payload = {'asset_id':asset['id'],'title':'Inspect drive belt','checklist':[{'text':'Check tension'}],
        'timezone':'Africa/Lagos','start_local':'2026-01-01T09:00','interval_unit':'day','interval_count':1,
        'assignee_id':member,'reminder_hours':24,**extra}
    response = api(client,'/maintenance-plans',payload,key='plan-'+str(asset['id'])+'-'+str(extra.get('title','default')).replace(' ','-'))
    assert response.status_code==201,response.get_json()
    return response.get_json()['plan']


def info(client, plan):
    response = client.get(f"/api/v1/maintenance-plans/{plan['id']}")
    assert response.status_code==200,response.get_json()
    return response.get_json()


def test_exact_contract_validation_tenant_mfa_and_replay(app,client,owner):
    asset = create_asset(client)
    box = clock(app)
    preview = api(client,'/maintenance-plans/preview',{'timezone':'Africa/Lagos','start_local':'2026-01-31T09:00','interval_unit':'month','interval_count':1})
    assert preview.status_code==200 and len(preview.get_json()['dates'])==5
    assert preview.get_json()['dates'][1]['scheduled_local']=='2026-02-28T09:00'
    assert api(client,'/maintenance-plans/preview',{'timezone':'UTC','start_local':'2026-01-01T09:00Z','interval_unit':'day','interval_count':1}).status_code==400
    plan = make_plan(client,asset,owner['membership']['id'])
    expected = {'id','asset_id','asset_name','title','description','priority','assignee_id','assignee_name','checklist',
        'timezone','start_local','interval_unit','interval_count','reminder_hours','escalation_member_id','enabled',
        'revision','generation','next_due_at','next_due_local','blocked_reason','created_at'}
    assert set(plan)==expected
    assert client.get('/api/v1/auth/me').get_json()['company']['timezone']=='Africa/Lagos'
    assert client.get('/api/v1/auth/me').get_json()['capabilities']['manage_preventive_maintenance']
    assert api(client,f"/maintenance-plans/{plan['id']}",{'revision':1,'asset_id':asset['id']},'PATCH',key='pm-edit-unknown').status_code==400
    assert api(client,f"/maintenance-plans/{plan['id']}",{'revision':99,'title':'Stale'},'PATCH',key='pm-edit-stale').status_code==409
    other = app.test_client()
    # Remove the injected past clock during real authenticator enrollment.
    app.config.pop('TEST_CLOCK')
    register(app,other,'foreign@example.test','Foreign','Other')
    assert other.get(f"/api/v1/maintenance-plans/{plan['id']}").status_code==404
    assert api(other,'/maintenance-plans',{'company_id':owner['company']['id']},key='pm-forged-tenant').status_code==400


def test_atomic_repeat_concurrent_tick_and_truthful_provenance(app,client,owner):
    asset = create_asset(client)
    clock(app)
    plan = make_plan(client,asset,owner['membership']['id'])
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _:tick(app),range(2)))
    assert sum(result['created'] for result in results)==1
    assert tick(app)['created']==0
    detail = info(client,plan)
    assert len(detail['occurrences'])==1 and len(detail['reminders'])==1
    work_id = detail['occurrences'][0]['work_order_id']
    work = client.get(f'/api/v1/work-orders/{work_id}').get_json()
    assert work['work_order']['plan_id']==plan['id']
    assert work['events'][0]['actor_kind']=='system' and work['events'][0]['actor_name']=='Schedule'
    with app.app_context():
        assert db.session.scalar(db.select(db.func.count()).select_from(WorkOrder))==1
        event = db.session.execute(db.select(WorkEvent)).scalar_one()
        assert event.actor_id is None and event.action=='schedule_create'
        # Human transitions cannot silently become null-actor events.
        db.session.add(WorkEvent(company_id=owner['company']['id'],work_order_id=work_id,actor_kind='system',actor_name='Schedule',action='approve',to_status='completed'))
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()


def test_downtime_coalesces_active_due_unchanged_and_closure_skips_backlog(app,client,owner):
    asset = create_asset(client)
    box = clock(app,'2026-01-10T08:00:00+00:00')
    plan = make_plan(client,asset,owner['membership']['id'])
    assert tick(app)['created']==1
    detail = info(client,plan)
    occurrence = detail['occurrences'][0]
    assert occurrence['missed_count']==9
    assert occurrence['missed_from']=='2026-01-01T08:00:00Z'
    assert occurrence['missed_through']=='2026-01-09T08:00:00Z'
    wid = occurrence['work_order_id']
    box[0] += timedelta(days=5)
    assert tick(app)['created']==0
    work = client.get(f'/api/v1/work-orders/{wid}').get_json()['work_order']
    assert work['due_at']=='2026-01-10T08:00:00Z'
    assert info(client,plan)['occurrences'][0]==occurrence
    response = api(client,f'/work-orders/{wid}/transition',{'revision':work['revision'],'action':'cancel','notes':'Safe cancellation'},key='pm-close-backlog')
    assert response.status_code==200,response.get_json()
    assert info(client,plan)['plan']['next_due_at']=='2026-01-16T08:00:00Z'
    assert tick(app)['created']==1  # exactly one future slot in the reminder horizon
    assert len(info(client,plan)['occurrences'])==2
    assert api(client,f'/work-orders/{wid}/transition',{'revision':2,'action':'reopen','notes':'Revisit'},key='pm-reopen-conflict').get_json()['error']['code']=='plan_work_conflict'


def test_pause_resume_edit_snapshots_and_no_cancelled_mail_resurrection(app,client,owner):
    asset = create_asset(client)
    box = clock(app)
    plan = make_plan(client,asset,owner['membership']['id'])
    tick(app)
    original = info(client,plan)
    wid = original['occurrences'][0]['work_order_id']
    with app.app_context():
        snapshot = dict(db.session.get(PlanOccurrence,original['occurrences'][0]['id']).snapshot)
    assert api(client,f"/maintenance-plans/{plan['id']}/pause",{'revision':1,'reason':'Plant shut down'},key='pm-pause-one').status_code==200
    assert run_once(app,'maintenance_mail')['processed']==0
    box[0] += timedelta(days=30)
    assert tick(app)['created']==0
    assert api(client,f"/maintenance-plans/{plan['id']}/resume",{'revision':2,'reason':'Plant reopened'},key='pm-resume-one').status_code==200
    assert tick(app)['created']==0
    assert info(client,plan)['reminders'][0]['state']=='cancelled'
    assert api(client,f"/maintenance-plans/{plan['id']}",{'revision':3,'title':'New future title','interval_unit':'month','start_local':'2026-01-31T09:00'},'PATCH',key='pm-edit-generation').status_code==200
    detail = info(client,plan)
    assert detail['plan']['generation']==2
    assert client.get(f'/api/v1/work-orders/{wid}').get_json()['work_order']['title']=='Inspect drive belt'
    with app.app_context():
        assert db.session.get(PlanOccurrence,original['occurrences'][0]['id']).snapshot==snapshot


def test_reminder_identity_not_work_revision_ack_and_completion(app,client,owner):
    asset = create_asset(client)
    clock(app)
    plan = make_plan(client,asset,owner['membership']['id'],escalation_member_id=owner['membership']['id'])
    tick(app)
    detail = info(client,plan)
    wid = detail['occurrences'][0]['work_order_id']
    rid = next(r['id'] for r in detail['reminders'] if r['stage']=='due')
    assert api(client,f'/work-orders/{wid}/transition',{'revision':1,'action':'start'},key='pm-start-one').status_code==200
    assert tick(app)['created']==0
    assert len(info(client,plan)['reminders'])==2
    result = run_once(app,'maintenance_mail')
    assert result['state']=='done'
    due = next(r for r in info(client,plan)['reminders'] if r['id']==rid)
    assert due['state']=='accepted' and due['accepted_at'] and not due['acknowledged_at']
    assert api(client,f'/maintenance-reminders/{rid}/ack',{},key='pm-ack-one').status_code==200
    assert next(r for r in info(client,plan)['reminders'] if r['id']==rid)['acknowledged_at']
    assert api(client,f'/maintenance-reminders/{rid}/retry',{'reason':'No resend'},key='pm-retry-accepted').status_code==409
    assert api(client,f'/work-orders/{wid}/transition',{'revision':2,'action':'submit','notes':'Belt safe','checklist':[{'text':'Check tension','completed':True}],'labor_minutes':12},key='pm-submit-one').status_code==200
    assert tick(app)['created']==0  # awaiting_review is unfinished
    assert api(client,f'/work-orders/{wid}/transition',{'revision':3,'action':'approve'},key='pm-approve-one').status_code==200
    overdue = next(r for r in info(client,plan)['reminders'] if r['stage']=='overdue')
    assert overdue['state']=='cancelled'
    assert run_once(app,'maintenance_mail')['processed']==0


def test_due_assignment_generation_retries_refusal_and_sanitized_history(app,client,owner):
    asset = create_asset(client)
    box = clock(app)
    plan = make_plan(client,asset,owner['membership']['id'])
    tick(app)
    wid = info(client,plan)['occurrences'][0]['work_order_id']
    assert api(client,f'/work-orders/{wid}',{'revision':1,'priority':'urgent'},'PATCH',key='pm-priority-only').status_code==200
    assert len(info(client,plan)['reminders'])==1
    assert api(client,f'/work-orders/{wid}',{'revision':2,'due_at':'2026-01-02T08:00:00Z'},'PATCH',key='pm-due-change').status_code==200
    reminders = info(client,plan)['reminders']
    assert len(reminders)==2 and reminders[1]['state']=='cancelled'
    def refuse(message):
        raise smtplib.SMTPRecipientsRefused({'secret@example.test':(550,b'private server response')})
    app.config['TEST_MAIL_ADAPTER'] = refuse
    assert run_once(app,'maintenance_mail')['state']=='failed'
    failed = info(client,plan)['reminders'][0]
    assert failed['state']=='failed' and failed['error']=='Recipient refused delivery.'
    assert 'secret' not in str(failed)
    assert api(client,f"/maintenance-reminders/{failed['id']}/retry",{'reason':'Mailbox fixed'},key='pm-retry-failed').status_code==200
    app.config['TEST_MAIL_ADAPTER'] = app.extensions['captured_mail'].append
    assert run_once(app,'maintenance_mail')['state']=='done'
    with app.app_context():
        assert len(db.session.execute(db.select(ReminderAttempt)).scalars().all())==3


def test_rescheduled_mail_local_and_utc_dates_match(app,client,owner):
    asset=create_asset(client)
    clock(app)
    plan=make_plan(client,asset,owner['membership']['id'])
    tick(app)
    wid=info(client,plan)['occurrences'][0]['work_order_id']
    assert api(client,f'/work-orders/{wid}',{'revision':1,'due_at':'2026-01-02T08:00:00Z'},'PATCH',key='pm-reschedule-mail').status_code==200
    assert run_once(app,'maintenance_mail')['state']=='done'
    message=app.extensions['captured_mail'][-1].get_content()
    assert 'Scheduled: 2026-01-02T08:00:00Z (UTC)' in message
    assert 'Plant schedule: 2026-01-02T09:00 Africa/Lagos' in message
    assert 'Plant schedule: 2026-01-01T09:00' not in message


def test_multiline_title_is_body_only_not_email_header(app,client,owner):
    asset=create_asset(client)
    clock(app)
    response=api(client,'/maintenance-plans',{'asset_id':asset['id'],'title':'Safe title\nwith body newline','checklist':[],'timezone':'Africa/Lagos','start_local':'2026-01-01T09:00','interval_unit':'day','interval_count':1,'assignee_id':owner['membership']['id'],'reminder_hours':24},key='pm-multiline-title')
    assert response.status_code==201,response.get_json()
    plan=response.get_json()['plan']
    tick(app)
    assert run_once(app,'maintenance_mail')['state']=='done'
    message=app.extensions['captured_mail'][-1]
    assert '\n' not in message['Subject'] and 'Safe title' not in message['Subject']
    assert 'Safe title\nwith body newline' in message.get_content()


def test_forged_reminder_provenance_and_archived_asset_suppressed(app,client,owner):
    asset = create_asset(client)
    clock(app)
    plan = make_plan(client,asset,owner['membership']['id'])
    tick(app)
    with app.app_context():
        real = db.session.execute(db.select(WorkReminder)).scalar_one()
        db.session.add(Job(kind='maintenance_mail',company_id=real.company_id,reminder_id=real.id,
            identity='forged-reminder-job',payload={'to':'forged@example.test'}))
        db.session.commit()
    assert run_once(app,'maintenance_mail')['state']=='done'
    assert run_once(app,'maintenance_mail')['state']=='cancelled'
    assert len(app.extensions['captured_mail'])==2  # verification + only the legitimate reminder
    assert api(client,f"/assets/{asset['id']}",method='DELETE').status_code==200
    assert tick(app)['created']==0
    assert info(client,plan)['plan']['blocked_reason']=='archived_asset'


def test_caps_fairness_and_evidence_downgrade_refusal(app,client,owner):
    asset = create_asset(client)
    clock(app)
    plan = make_plan(client,asset,owner['membership']['id'])
    app.config['PM_PENDING_REMINDER_LIMIT'] = 1
    make_plan(client,asset,owner['membership']['id'],title='Second plan')
    result = tick(app)
    assert result['created']==1
    with app.app_context():
        assert db.session.scalar(db.select(db.func.count()).select_from(WorkOrder))==1
        assert 'reminder_capacity' in [p.blocked_reason for p in db.session.execute(db.select(MaintenancePlan)).scalars()]
        db.session.remove()
        with pytest.raises(SystemExit):
            downgrade(directory=str(ROOT/'migrations_pilot'),revision='pilot_0002')
        db.session.rollback()


def test_clock_configuration_and_foreground_heartbeat(app,client,owner):
    config = {key:app.config[key] for key in ('SECRET_KEY','MFA_ENCRYPTION_KEY','APP_BASE_URL','PRIVATE_STORAGE_DIR','SQLALCHEMY_DATABASE_URI')}
    with pytest.raises(RuntimeError,match='TEST_CLOCK'):
        create_app({**config,'LOAD_PILOT_ENV':False,'APP_ENV':'development','TESTING':False,
            'SMTP_HOST':'localhost','SMTP_FROM':'local@example.test','CLAMAV_HOST':'localhost','TEST_CLOCK':lambda:datetime.now(timezone.utc)})
    with pytest.raises(RuntimeError,match='TEST_CLOCK'):
        create_app({**config,'LOAD_PILOT_ENV':False,'APP_ENV':'test','TESTING':True,'TEST_CLOCK':42})
    result = run_foreground(app,max_cycles=1,idle_seconds=.001)
    assert result['cycles']==1
    diagnostics = client.get('/api/v1/maintenance-diagnostics').get_json()
    assert diagnostics['worker']['fresh'] is False  # stopped foreground run is not fake readiness
