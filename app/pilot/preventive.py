"""Authoritative tenant PM API, immutable history, explicit acknowledgment and retry."""
from flask import Blueprint, g, request
from sqlalchemy import func
from app import db
from app.models import Asset, Company, User
from app.pilot.models import (MaintenancePlan, PlanOccurrence, PlanEvent, WorkReminder, Job,
                              WorkerHeartbeat, Membership, ReminderAttempt, now)
from app.pilot.calendar import Calendar, POLICY
from app.pilot.maintenance import assignee, checklist, priority, MANAGERS, eligible_member
from app.pilot.security import APIError, authorized, data, text, integer, scoped, revision, iso, idempotent, tenant_lock
from app.pilot.scheduling import (lock_plan, cursor, plan_event, calendar_for, skipped, cancel_reminders,
                                  reminder_context, reminder_identity)

bp = Blueprint('pilot_preventive',__name__)
SCHEDULE = {'timezone','start_local','interval_unit','interval_count'}
FIELDS = SCHEDULE | {'title','description','priority','assignee_id','checklist','reminder_hours','escalation_member_id'}


def member_name(identity):
    member = db.session.get(Membership,identity) if identity else None
    user = db.session.get(User,member.user_id) if member else None
    return user.name if user else None


def plan_json(row):
    asset = db.session.get(Asset,row.asset_id)
    return {'id':row.id,'asset_id':row.asset_id,'asset_name':asset.name,'title':row.title,
        'description':row.description,'priority':row.priority,'assignee_id':row.assignee_id,
        'assignee_name':member_name(row.assignee_id),'checklist':[{'text':c['text']} for c in row.checklist],
        'timezone':row.timezone,'start_local':row.start_local,'interval_unit':row.interval_unit,
        'interval_count':row.interval_count,'reminder_hours':row.reminder_hours,
        'escalation_member_id':row.escalation_member_id,'enabled':row.enabled,'revision':row.revision,
        'generation':row.generation,'next_due_at':iso(row.next_due_at),'next_due_local':row.next_due_local,
        'blocked_reason':row.blocked_reason,'created_at':iso(row.created_at)}


def occurrence_json(row):
    return {key:getattr(row,key) for key in ('id','plan_id','generation','scheduled_local','work_order_id','missed_count')} | {
        key:iso(getattr(row,key)) for key in ('scheduled_at','missed_from','missed_through','created_at')}


def event_json(row):
    return {'id':row.id,'action':row.action,'actor_name':row.actor_name,'notes':row.notes,'created_at':iso(row.created_at)}


def reminder_json(row):
    return {'id':row.id,'occurrence_id':row.occurrence_id,'work_order_id':row.work_order_id,'stage':row.stage,
        'recipient_name':member_name(row.recipient_id),'state':row.state,'scheduled_at':iso(row.scheduled_at),
        'accepted_at':iso(row.accepted_at),'acknowledged_at':iso(row.acknowledged_at),'attempts':row.attempts,
        'error':row.error,'created_at':iso(row.created_at)}


def calendar_body(body, defaults=None):
    values = {key:body.get(key,getattr(defaults,key,None) if defaults else None) for key in SCHEDULE}
    try:
        return Calendar(values['start_local'],values['timezone'],values['interval_unit'],values['interval_count'])
    except (ValueError,OverflowError,TypeError):
        raise APIError('invalid_fields','Use a valid IANA timezone, local YYYY-MM-DDTHH:mm and day/week/month interval 1–365.') from None


def apply_plan(row, body, creating=False):
    for key,maximum,required in (('title',200,True),('description',10000,False)):
        if creating or key in body:
            setattr(row,key,text(body,key,maximum,required))
    if creating or 'priority' in body:
        row.priority = priority(body)
    if creating or 'assignee_id' in body:
        row.assignee_id = assignee(body.get('assignee_id'),row.company_id)
    if creating or 'checklist' in body:
        row.checklist = [{'text':step['text']} for step in checklist(body.get('checklist',[]))]
    if creating or 'reminder_hours' in body:
        hours = body.get('reminder_hours',24)
        if type(hours) is not int or not 0<=hours<=72:
            raise APIError('invalid_fields','reminder_hours must be 0–72.')
        row.reminder_hours = hours
    if creating or 'escalation_member_id' in body:
        identity = integer(body.get('escalation_member_id'),'escalation_member_id',True)
        if identity:
            scoped(Membership,identity)
            if not eligible_member(row.company_id,identity,MANAGERS):
                raise APIError('invalid_assignee','Escalate only to an active owner, administrator or planner.')
        row.escalation_member_id = identity
    cal = calendar_body(body,row)
    for key in SCHEDULE:
        if key in body:
            setattr(row,key,body[key])
    return cal


@bp.get('/maintenance-plans')
@authorized()
def list_plans():
    query = db.select(MaintenancePlan).where(MaintenancePlan.company_id==g.membership.company_id)
    if request.args.get('asset_id'):
        try:
            aid = int(request.args['asset_id'])
        except ValueError:
            raise APIError('invalid_filter','Invalid asset_id.')
        scoped(Asset,integer(aid,'asset_id'))
        query = query.where(MaintenancePlan.asset_id==aid)
    return {'plans':[plan_json(row) for row in db.session.execute(query.order_by(MaintenancePlan.id.desc()).limit(1000)).scalars()]}


@bp.post('/maintenance-plans/preview')
@authorized()
def preview():
    body = data(SCHEDULE,SCHEDULE)
    cal = calendar_body(body)
    try:
        dates = cal.preview(now())
    except (ValueError,OverflowError):
        raise APIError('invalid_fields','The schedule exceeds the supported calendar range.') from None
    return {'dates':dates,'policy':POLICY}


@bp.post('/maintenance-plans')
@authorized(*MANAGERS,mfa=True)
@idempotent
def create_plan():
    body = data(FIELDS|{'asset_id'},SCHEDULE|{'asset_id','title','checklist'})
    cid = g.membership.company_id
    tenant_lock(cid)
    company = db.session.execute(db.select(Company).where(Company.id==cid).with_for_update()).scalar_one()
    asset = scoped(Asset,integer(body['asset_id'],'asset_id'))
    if asset.archived_at:
        raise APIError('archived','Cannot schedule an archived machine.',409)
    count = db.session.scalar(db.select(func.count()).select_from(MaintenancePlan).where(MaintenancePlan.company_id==cid))
    from flask import current_app
    if count>=current_app.config['PM_PLAN_LIMIT']:
        raise APIError('plan_capacity','This factory has reached its maintenance-plan limit.',409)
    row = MaintenancePlan(company_id=company.id,asset_id=asset.id)
    apply_plan(row,body,True)
    row.next_index = 0
    cursor(row,0)
    row.blocked_reason = 'needs_assignment' if not row.assignee_id else None
    db.session.add(row)
    db.session.flush()
    plan_event(row,'create','Fixed local calendar schedule created.',g.user)
    return {'plan':plan_json(row)},201


@bp.get('/maintenance-plans/<int:identity>')
@authorized()
def detail(identity):
    row = scoped(MaintenancePlan,identity)
    occurrences = db.session.execute(db.select(PlanOccurrence).where(PlanOccurrence.company_id==row.company_id,PlanOccurrence.plan_id==row.id).order_by(PlanOccurrence.id.desc()).limit(100)).scalars()
    events = db.session.execute(db.select(PlanEvent).where(PlanEvent.company_id==row.company_id,PlanEvent.plan_id==row.id).order_by(PlanEvent.id.desc()).limit(100)).scalars()
    reminders = db.session.execute(db.select(WorkReminder).join(PlanOccurrence,PlanOccurrence.id==WorkReminder.occurrence_id).where(WorkReminder.company_id==row.company_id,PlanOccurrence.plan_id==row.id).order_by(WorkReminder.id.desc()).limit(100)).scalars()
    return {'plan':plan_json(row),'occurrences':[occurrence_json(o) for o in occurrences],
        'events':[event_json(e) for e in events],'reminders':[reminder_json(r) for r in reminders]}


@bp.patch('/maintenance-plans/<int:identity>')
@authorized(*MANAGERS,mfa=True)
@idempotent
def edit(identity):
    body = data(FIELDS|{'revision'},{'revision'})
    row = lock_plan(identity,g.membership.company_id)
    revision(row,body)
    old_schedule = tuple(getattr(row,key) for key in sorted(SCHEDULE))
    apply_plan(row,body)
    if old_schedule!=tuple(getattr(row,key) for key in sorted(SCHEDULE)):
        row.generation += 1
        row.effective_at = now()
        cal = calendar_for(row)
        try:
            next_index = cal.future_index(row.effective_at)
        except (ValueError,OverflowError):
            raise APIError('invalid_fields','No future slot exists in the supported calendar range.') from None
        cursor(row,next_index)
        plan_event(row,'generation',f'Generation {row.generation} effective {iso(row.effective_at)}; existing work snapshots unchanged.',g.user)
    row.revision += 1
    plan_event(row,'edit','Future work template updated; existing work and reminder snapshots retained.',g.user)
    return {'plan':plan_json(row)}


@bp.post('/maintenance-plans/<int:identity>/pause')
@bp.post('/maintenance-plans/<int:identity>/resume')
@authorized(*MANAGERS,mfa=True)
@idempotent
def enabled(identity):
    body = data({'revision','reason'},{'revision','reason'})
    row = lock_plan(identity,g.membership.company_id)
    revision(row,body)
    reason = text(body,'reason',1000,True)
    resume = request.path.endswith('/resume')
    if resume==row.enabled:
        raise APIError('invalid_transition','The plan is already in that state.',409)
    if resume:
        last = calendar_for(row).latest_index(now())
        skipped(row,row.next_index,last,'paused_period')
        cursor(row,max(row.next_index,last+1))
        row.paused_at = None
        row.blocked_reason = None
    else:
        cancel_reminders(row.company_id,plan_id=row.id)
        row.paused_at = now()
        row.blocked_reason = 'paused'
    row.enabled = resume
    row.revision += 1
    plan_event(row,'resume' if resume else 'pause',reason,g.user)
    return {'plan':plan_json(row)}


def lock_reminder(identity):
    cid = g.membership.company_id
    preview = scoped(WorkReminder,identity)
    occurrence = db.session.get(PlanOccurrence,preview.occurrence_id)
    plan = lock_plan(occurrence.plan_id,cid)
    job = db.session.execute(db.select(Job).where(Job.company_id==cid,Job.reminder_id==identity).with_for_update()).scalar_one_or_none()
    row = db.session.execute(db.select(WorkReminder).where(WorkReminder.id==identity,WorkReminder.company_id==cid).with_for_update().execution_options(populate_existing=True)).scalar_one()
    return row,job,plan


@bp.post('/maintenance-reminders/<int:identity>/retry')
@authorized(*MANAGERS,mfa=True)
@idempotent
def retry(identity):
    from flask import current_app
    from app.pilot.scheduling import pending_count
    body = data({'reason'},{'reason'})
    reason = text(body,'reason',1000,True)
    row,job,plan = lock_reminder(identity)
    if row.state!='failed' or not job or job.state!='failed':
        raise APIError('invalid_transition','Only a failed reminder can be retried.',409)
    if pending_count(row.company_id)>=current_app.config['PM_PENDING_REMINDER_LIMIT']:
        raise APIError('reminder_capacity','This factory has reached its pending-reminder limit.',409)
    row.state = 'queued'
    if not reminder_context(job):
        raise APIError('reminder_obsolete','This reminder no longer has a valid recipient or unfinished work.',409)
    job.state,job.attempts,job.error,job.available_at = 'queued',0,None,now()
    job.lease_token = job.lease_until = None
    row.error = None
    plan_event(plan,'reminder_retry',f'Reminder {row.id}: {reason}',g.user)
    db.session.add(ReminderAttempt(company_id=row.company_id,reminder_id=row.id,lease_token='manual-retry',outcome='manual_retry'))
    return {'reminder':reminder_json(row)}


@bp.post('/maintenance-reminders/<int:identity>/ack')
@authorized(mfa=True)
@idempotent
def acknowledge(identity):
    data(set())
    row,job,plan = lock_reminder(identity)
    if row.recipient_id!=g.membership.id and g.membership.role not in MANAGERS:
        raise APIError('forbidden','Only the recipient or a planner can acknowledge this reminder.',403)
    if not row.acknowledged_at:
        row.acknowledged_at = now()
        plan_event(plan,'reminder_ack',f'Reminder {row.id} acknowledged; no work approval or receipt implied.',g.user)
    return {'reminder':reminder_json(row)}


@bp.get('/maintenance-diagnostics')
@authorized(*MANAGERS,mfa=True)
def diagnostics():
    cid = g.membership.company_id
    heartbeat = db.session.execute(db.select(WorkerHeartbeat).where(WorkerHeartbeat.stopped_at.is_(None)).order_by(WorkerHeartbeat.last_seen_at.desc()).limit(1)).scalar_one_or_none()
    counts = dict(db.session.execute(db.select(WorkReminder.state,func.count()).where(WorkReminder.company_id==cid).group_by(WorkReminder.state)).all())
    oldest = db.session.scalar(db.select(func.min(WorkReminder.scheduled_at)).where(WorkReminder.company_id==cid,WorkReminder.state.in_(['queued','running','retrying'])))
    due = db.session.scalar(db.select(func.min(MaintenancePlan.next_due_at)).where(MaintenancePlan.company_id==cid,MaintenancePlan.enabled.is_(True)))
    return {'worker':{'last_seen_at':iso(heartbeat.last_seen_at) if heartbeat else None,
        'fresh':bool(heartbeat and (now()-heartbeat.last_seen_at).total_seconds()<=60)},
        'scheduler_last_tick_at':iso(heartbeat.last_tick_at) if heartbeat else None,
        'next_due_at':iso(due),'reminder_counts':counts,'oldest_pending_at':iso(oldest)}
