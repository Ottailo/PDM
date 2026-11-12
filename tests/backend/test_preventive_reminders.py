"""PM worker adversarial leases, authority, retries and lane fairness (serial DB runner)."""
from datetime import timedelta
from threading import Event
from concurrent.futures import ThreadPoolExecutor
from app import db
from app.pilot.models import Job, WorkReminder, WorkOrder, PlanOccurrence, MaintenancePlan, ReminderAttempt
from app.pilot.worker import run_once
from app.pilot.scheduling import tick
from conftest import api, create_asset, register
from test_preventive_maintenance import clock, make_plan, info
from test_security_remediation import invite_member, reauth
from test_documents import upload


def test_transient_retry_backoff_and_four_attempt_limit(app,client,owner):
    asset = create_asset(client)
    box = clock(app)
    plan = make_plan(client,asset,owner['membership']['id'])
    tick(app)
    def unavailable(message):
        raise ConnectionError('private smtp credentials must never leak')
    app.config['TEST_MAIL_ADAPTER'] = unavailable
    for attempt in range(4):
        result = run_once(app,'maintenance_mail')
        assert result['state']==('failed' if attempt==3 else 'queued')
        reminder = info(client,plan)['reminders'][0]
        assert reminder['attempts']==attempt+1
        assert 'private' not in reminder['error']
        if attempt<3:
            assert run_once(app,'maintenance_mail')['processed']==0
            box[0] += timedelta(minutes=6)
    assert run_once(app,'maintenance_mail')['processed']==0
    with app.app_context():
        assert len(db.session.execute(db.select(ReminderAttempt)).scalars().all())==4


def test_offboard_before_delivery_and_cancelled_retry_denied(app,client,owner):
    actor,identity = invite_member(app,client,role='technician')
    asset = create_asset(client)
    # Team access confirmation is real-time and performed before the test-only time shift.
    assert reauth(client,owner).status_code==200
    plan = make_plan(client,asset,identity['membership']['id'])
    from datetime import datetime, timezone
    clock(app,datetime.now(timezone.utc).isoformat())
    tick(app)
    app.config.pop('TEST_CLOCK')
    assert api(client,f"/members/{identity['membership']['id']}",{'reason':'Technician departed'},'DELETE').status_code==200
    assert info(client,plan)['reminders'][0]['state']=='cancelled'
    assert run_once(app,'maintenance_mail')['processed']==0
    rid = info(client,plan)['reminders'][0]['id']
    assert api(client,f'/maintenance-reminders/{rid}/retry',{'reason':'Cannot resurrect'},key='pm-offboard-retry').status_code==409


def test_lease_loss_during_external_send_is_fenced_and_truthfully_recorded(app,client,owner):
    asset = create_asset(client)
    clock(app)
    plan = make_plan(client,asset,owner['membership']['id'])
    tick(app)
    rid = info(client,plan)['reminders'][0]['id']
    def lose_lease(message):
        with app.app_context():
            job = db.session.execute(db.select(Job).where(Job.reminder_id==rid)).scalar_one()
            job.lease_token = 'another-worker'
            db.session.commit()
    app.config['TEST_MAIL_ADAPTER'] = lose_lease
    assert run_once(app,'maintenance_mail')['state']=='lease_lost'
    assert info(client,plan)['reminders'][0]['state']=='running'
    assert info(client,plan)['reminders'][0]['accepted_at'] is None
    with app.app_context():
        job = db.session.execute(db.select(Job).where(Job.reminder_id==rid)).scalar_one()
        assert job.lease_token=='another-worker'
        attempt = db.session.execute(db.select(ReminderAttempt)).scalar_one()
        assert attempt.outcome=='lease_lost'


def test_pause_in_flight_has_no_locks_over_smtp_and_cannot_claim_acceptance(app,client,owner):
    asset = create_asset(client)
    clock(app)
    plan = make_plan(client,asset,owner['membership']['id'])
    tick(app)
    entered,release = Event(),Event()
    def blocked(message):
        entered.set()
        assert release.wait(10)
    app.config['TEST_MAIL_ADAPTER'] = blocked
    with ThreadPoolExecutor(max_workers=1) as pool:
        send = pool.submit(run_once,app,'maintenance_mail')
        assert entered.wait(10)
        try:
            assert api(client,f"/maintenance-plans/{plan['id']}/pause",{'revision':1,'reason':'Safety halt'},key='pm-inflight-pause').status_code==200
        finally:
            release.set()
        assert send.result(timeout=10)['state']=='lease_lost'
    assert info(client,plan)['reminders'][0]['state']=='cancelled'
    assert info(client,plan)['reminders'][0]['accepted_at'] is None


def test_reminder_tenant_fairness_and_auth_document_rotation(app,client,owner):
    first = create_asset(client)
    # Prepare identities while using real TOTP time, then drive only PM through the isolated clock.
    other = app.test_client()
    second_owner = register(app,other,'secondpm@example.test','Second','Plant B')
    second = create_asset(other)
    clock(app)
    a = make_plan(client,first,owner['membership']['id'])
    b = make_plan(client,first,owner['membership']['id'],title='Second A')
    c = make_plan(other,second,second_owner['membership']['id'])
    tick(app)
    assert run_once(app,'maintenance_mail')['state']=='done'
    assert run_once(app,'maintenance_mail')['state']=='done'
    assert info(client,a)['reminders'][0]['state']=='accepted'
    assert info(other,c)['reminders'][0]['state']=='accepted'
    assert info(client,b)['reminders'][0]['state']=='queued'
    app.config['TEST_SCANNER'] = lambda content:True
    app.config['TEST_PARSER'] = lambda content:['Safe manual']
    assert upload(client,first).status_code==202
    assert api(client,'/auth/forgot-password',{'email':'owner@example.test'}).status_code==202
    results = [run_once(app) for _ in range(3)]
    with app.app_context():
        kinds = {db.session.get(Job,result['job_id']).kind for result in results if result.get('job_id')}
    assert kinds=={'mail','document','maintenance_mail'}


def test_foreign_pm_composite_links_fail_database_boundary(app,client,owner):
    import pytest
    from sqlalchemy.exc import IntegrityError
    first = create_asset(client)
    other = app.test_client()
    foreign_owner = register(app,other,'foreignpm@example.test','Foreign','Other')
    foreign = create_asset(other)
    clock(app)
    a = make_plan(client,first,owner['membership']['id'])
    b = make_plan(other,foreign,foreign_owner['membership']['id'])
    tick(app)
    aid = info(client,a)['occurrences'][0]['id']
    bid = info(other,b)['occurrences'][0]['work_order_id']
    with app.app_context():
        db.session.add(WorkReminder(company_id=owner['company']['id'],occurrence_id=aid,work_order_id=bid,
            stage='due',recipient_id=owner['membership']['id'],notification_generation=9,
            scheduled_at=app.config['TEST_CLOCK']()))
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()
