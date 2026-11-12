"""Assigned maintenance lifecycle with locked revisions and append-only history."""
import csv
import io
from datetime import datetime, timezone
from flask import Blueprint, g, request, Response
from app import db
from app.models import Asset, Company, User
from app.pilot.models import WorkOrder, WorkEvent, Membership, now
from app.pilot.security import APIError, authorized, data, text, integer, scoped, revision, iso, idempotent, tenant_lock

bp = Blueprint('pilot_maintenance',__name__)
MANAGERS = {'owner','admin','planner'}


def due(body):
    value = body.get('due_at')
    if value is None:
        return None
    try:
        if not isinstance(value,str) or len(value)>40:
            raise ValueError()
        result = datetime.fromisoformat(value.replace('Z','+00:00'))
        if not result.tzinfo:
            raise ValueError()
        return result.astimezone(timezone.utc)
    except ValueError:
        raise APIError('invalid_fields','due_at must be an ISO timestamp with timezone.')


def priority(body):
    value = text(body,'priority',20,True,default='medium')
    if value not in {'low','medium','high','urgent'}:
        raise APIError('invalid_fields','Priority must be low, medium, high or urgent.')
    return value


def eligible_member(company_id, identity, roles=None):
    if identity is None:
        return None
    member = db.session.execute(db.select(Membership).where(Membership.id==identity, Membership.company_id==company_id)).scalar_one_or_none()
    user = db.session.get(User, member.user_id) if member else None
    if not member or not member.active or member.role not in (roles or {'owner','admin','planner','technician'}) or not user or not user.is_enabled or not user.email_verified_at:
        return None
    return member


def assignee(value, company_id=None):
    identity = integer(value,'assignee_id',True)
    cid = company_id if company_id is not None else g.membership.company_id
    if identity:
        member = db.session.execute(db.select(Membership).where(Membership.id==identity, Membership.company_id==cid)).scalar_one_or_none()
        if not member:
            raise APIError('not_found','Record not found.',404)
        if not eligible_member(cid, identity):
            raise APIError('invalid_assignee','Assign work to an active maintenance team member.')
    return identity


def create_work(company, asset, body, assigned, due_at, plan_id=None, occurrence_id=None, actor=None):
    """Caller holds tenant/Company locks. Explicit identity; safe for a scheduler without g."""
    if asset.company_id != company.id or asset.archived_at:
        raise APIError('archived','Cannot request work for an archived machine.',409)
    assignee(assigned, company.id)
    row = WorkOrder(company_id=company.id,asset_id=asset.id,number=f'WO-{company.next_work_order:06d}',
        title=text(body,'title',200,True),description=text(body,'description',10000),priority=priority(body),
        assignee_id=assigned,status='assigned' if assigned else 'open',due_at=due_at,
        checklist=checklist(body.get('checklist',[])),plan_id=plan_id,occurrence_id=occurrence_id)
    company.next_work_order += 1
    db.session.add(row)
    db.session.flush()
    db.session.add(WorkEvent(company_id=company.id,work_order_id=row.id,
        actor_id=actor.id if actor else None,actor_kind='user' if actor else 'system',
        actor_name=actor.name if actor else 'Schedule',action='create' if actor else 'schedule_create',to_status=row.status))
    return row


def checklist(value,completion=False):
    if not isinstance(value,list) or len(value)>100:
        raise APIError('invalid_checklist','Checklist must contain at most 100 steps.')
    result = []
    for item in value:
        keys = {'text','completed'} if completion else {'text'}
        if not isinstance(item,dict) or set(item)!=keys:
            raise APIError('invalid_checklist','Each step must contain text'+(' and completed.' if completion else '.'))
        label = text(item,'text',500,True)
        completed = item.get('completed',False)
        if type(completed) is not bool:
            raise APIError('invalid_checklist','Completed must be true or false.')
        result.append({'text':label,'completed':completed})
    return result


def work_json(row):
    asset = db.session.get(Asset,row.asset_id)
    member = db.session.get(Membership,row.assignee_id) if row.assignee_id else None
    user = db.session.get(User,member.user_id) if member else None
    return {'id':row.id,'number':row.number,'title':row.title,'description':row.description,'asset_id':row.asset_id,'asset_name':asset.name,'priority':row.priority,'status':row.status,'assignee_id':row.assignee_id,'assignee_name':user.name if user else None,'due_at':iso(row.due_at),'revision':row.revision,'created_at':iso(row.created_at),'completed_at':iso(row.completed_at),'notes':row.notes,'completion_notes':row.completion_notes,'checklist':row.checklist,'labor_minutes':row.labor_minutes,'plan_id':row.plan_id,'occurrence_id':row.occurrence_id}


def event_json(row):
    return {'id':row.id,'actor_name':row.actor_name,'actor_kind':row.actor_kind,'action':row.action,'from_status':row.from_status,'to_status':row.to_status,'notes':row.notes,'created_at':iso(row.created_at)}


def events(row):
    return db.session.execute(db.select(WorkEvent).where(WorkEvent.company_id==g.membership.company_id,WorkEvent.work_order_id==row.id).order_by(WorkEvent.created_at,WorkEvent.id)).scalars().all()


def append_event(row,action,previous,notes=''):
    db.session.add(WorkEvent(company_id=row.company_id,work_order_id=row.id,actor_id=g.user.id,actor_name=g.user.name,action=action,from_status=previous,to_status=row.status,notes=notes))


@bp.get('/work-orders')
@authorized()
def list_work():
    query = db.select(WorkOrder).where(WorkOrder.company_id==g.membership.company_id)
    if request.args.get('asset_id'):
        try:
            aid = int(request.args['asset_id'])
        except ValueError:
            raise APIError('invalid_filter','Invalid asset_id.')
        scoped(Asset,integer(aid,'asset_id'))
        query = query.where(WorkOrder.asset_id==aid)
    status = request.args.get('status')
    if status:
        if status not in {'open','assigned','in_progress','blocked','awaiting_review','completed','cancelled'}:
            raise APIError('invalid_filter','Invalid status.')
        query = query.where(WorkOrder.status==status)
    mine = request.args.get('assigned_to_me','false')
    if mine not in {'true','false'}:
        raise APIError('invalid_filter','assigned_to_me must be true or false.')
    if mine=='true':
        query = query.where(WorkOrder.assignee_id==g.membership.id)
    return {'work_orders':[work_json(r) for r in db.session.execute(query.order_by(WorkOrder.created_at.desc(),WorkOrder.id.desc()).limit(1000)).scalars()]}


@bp.post('/work-orders')
@authorized('owner','admin','planner','technician',mfa=True)
@idempotent
def add_work():
    body = data({'asset_id','title','description','priority','assignee_id','due_at','checklist'},{'asset_id','title'})
    asset = scoped(Asset,integer(body['asset_id'],'asset_id'))
    if asset.archived_at:
        raise APIError('archived','Cannot request work for an archived machine.',409)
    assigned = assignee(body.get('assignee_id'))
    if assigned and g.membership.role not in MANAGERS:
        raise APIError('forbidden','Only planners can assign work.',403)
    tenant_lock(g.membership.company_id)
    company = db.session.execute(db.select(Company).where(Company.id==g.membership.company_id).with_for_update()).scalar_one()
    row = create_work(company,asset,body,assigned,due(body),actor=g.user)
    return {'work_order':work_json(row)},201


@bp.get('/work-orders/<int:identity>')
@authorized()
def get_work(identity):
    row = scoped(WorkOrder,identity)
    return {'work_order':work_json(row),'events':[event_json(e) for e in events(row)]}


@bp.patch('/work-orders/<int:identity>')
@authorized(*MANAGERS,mfa=True)
@idempotent
def edit_work(identity):
    body = data({'revision','assignee_id','due_at','priority'},{'revision'})
    from app.pilot.scheduling import lock_work
    row = lock_work(identity, g.membership.company_id)
    revision(row,body)
    if row.status in {'completed','cancelled','awaiting_review'}:
        raise APIError('invalid_transition','This work order cannot be reassigned now.',409)
    previous = row.status
    notification_before = (row.assignee_id, row.due_at)
    if 'assignee_id' in body:
        row.assignee_id = assignee(body['assignee_id'])
        if row.status in {'open','assigned'}:
            row.status = 'assigned' if row.assignee_id else 'open'
    if 'due_at' in body:
        row.due_at = due(body)
    if 'priority' in body:
        row.priority = priority(body)
    row.revision += 1
    append_event(row,'update',previous)
    if row.plan_id and notification_before != (row.assignee_id, row.due_at):
        from app.pilot.scheduling import refresh_work_reminders
        row.notification_generation += 1
        refresh_work_reminders(row)
    return {'work_order':work_json(row)}


@bp.post('/work-orders/<int:identity>/transition')
@authorized('owner','admin','planner','technician',mfa=True)
@idempotent
def transition(identity):
    body = data({'revision','action','notes','checklist','labor_minutes'},{'revision','action'})
    from app.pilot.scheduling import lock_work
    row = lock_work(identity, g.membership.company_id)
    revision(row,body)
    action = text(body,'action',32,True)
    notes = text(body,'notes',10000)
    manager = g.membership.role in MANAGERS
    if action in {'approve','cancel','reopen'}:
        if not manager:
            raise APIError('forbidden','Only a planner can review or manage this work.',403)
    elif action in {'start','block','resume','submit'}:
        if row.assignee_id != g.membership.id:
            raise APIError('forbidden','Only the assigned person can perform this action.',403)
    else:
        raise APIError('invalid_transition','Unknown work-order action.',409)
    allowed = {'start':({'open','assigned'},'in_progress'),'block':({'in_progress'},'blocked'),'resume':({'blocked'},'in_progress'),'submit':({'in_progress'},'awaiting_review'),'approve':({'awaiting_review'},'completed'),'cancel':({'open','assigned','in_progress','blocked','awaiting_review'},'cancelled'),'reopen':({'completed','cancelled'},'open')}
    sources,target = allowed[action]
    if row.status not in sources:
        raise APIError('invalid_transition','This action is not valid in the current state.',409)
    if action in {'block','submit','cancel','reopen'} and not notes:
        raise APIError('notes_required','Explain this action in the notes.')
    if 'checklist' in body:
        if action not in {'submit','block'}:
            raise APIError('invalid_fields','Checklist changes are only accepted when blocking or submitting.')
        updated = checklist(body['checklist'],True)
        if [c['text'] for c in updated]!=[c['text'] for c in row.checklist]:
            raise APIError('invalid_checklist','Checklist steps cannot be replaced during completion.')
        row.checklist = updated
    if action=='submit' and not all(c['completed'] for c in row.checklist):
        raise APIError('checklist_incomplete','Complete every required checklist step.')
    if 'labor_minutes' in body:
        value = body['labor_minutes']
        if action!='submit' or type(value) is not int or not 0<=value<=525600:
            raise APIError('invalid_fields','Labor minutes must be 0–525600 and supplied on submission.')
        row.labor_minutes = value
    if action=='reopen' and row.plan_id:
        other = db.session.scalar(db.select(WorkOrder.id).where(WorkOrder.company_id==row.company_id,WorkOrder.plan_id==row.plan_id,WorkOrder.id!=row.id,WorkOrder.status.notin_(['completed','cancelled'])).limit(1))
        if other:
            raise APIError('plan_work_conflict','Another unfinished order already exists for this plan.',409)
    previous = row.status
    row.status = target
    row.notes = notes or row.notes
    if action=='submit':
        row.completion_notes = notes
    if action=='approve':
        row.completed_at = now()
    elif action=='reopen':
        row.completed_at = None
        row.completion_notes = ''
        row.assignee_id = None
        row.checklist = [{'text':c['text'],'completed':False} for c in row.checklist]
    row.revision += 1
    append_event(row,action,previous,notes)
    if row.plan_id and action in {'approve','cancel','reopen'}:
        from app.pilot.scheduling import work_closed, refresh_work_reminders
        if action=='reopen':
            row.notification_generation += 1
            refresh_work_reminders(row)
        else:
            work_closed(row)
    return {'work_order':work_json(row)}


def csv_safe(value):
    value = str(value or '')
    if value.lstrip().startswith(('=','+','-','@','\t','\r')):
        value = "'"+value
    return value


@bp.get('/work-orders/<int:identity>/export')
@authorized()
def export(identity):
    row = scoped(WorkOrder,identity)
    out = io.StringIO(newline='')
    writer = csv.writer(out)
    writer.writerow(['Work order','Title','Machine','Priority','Current status'])
    writer.writerow([csv_safe(v) for v in [row.number,row.title,db.session.get(Asset,row.asset_id).name,row.priority,row.status]])
    writer.writerow([])
    writer.writerow(['UTC time','Actor','Action','From','To','Notes'])
    for event in events(row):
        writer.writerow([csv_safe(v) for v in [iso(event.created_at),event.actor_name,event.action,event.from_status,event.to_status,event.notes]])
    return Response(out.getvalue(),mimetype='text/csv',headers={'Content-Disposition':f'attachment; filename="{row.number}.csv"'})
