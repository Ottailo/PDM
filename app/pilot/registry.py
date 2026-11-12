"""Tenant-scoped location hierarchy and sensor-optional equipment registry."""
from flask import Blueprint, g, request
from sqlalchemy import func
from app import db
from app.models import Asset, Location
from app.pilot.models import WorkOrder, Document, now
from app.pilot.security import APIError, authorized, data, text, integer, scoped, revision

bp = Blueprint('pilot_registry',__name__)
MANAGERS = ('owner','admin','planner')
ASSET_FIELDS = {'code','name','manufacturer','model','serial_number','criticality','location_id','description'}


def location_json(row):
    return {'id':row.id,'name':row.name,'type':row.type,'parent_id':row.parent_id}


def asset_json(row):
    location = db.session.get(Location,row.location_id) if row.location_id else None
    return {'id':row.id,'code':row.code,'name':row.name,'manufacturer':row.manufacturer,'model':row.model,'serial_number':row.serial_number,'criticality':row.criticality,'location_id':row.location_id,'location_name':location.name if location else None,'status':'archived' if row.archived_at else 'active','description':row.description or '', 'revision':row.revision,'telemetry_status':'not_connected'}


def apply_asset(row,body,creating=False):
    for key,maximum in [('code',64),('name',100),('manufacturer',100),('model',100),('serial_number',100),('description',10000)]:
        if key in body:
            setattr(row,key,text(body,key,maximum,key in {'code','name'}))
    if 'criticality' in body:
        value = text(body,'criticality',20,True)
        if value not in {'low','medium','high','critical'}:
            raise APIError('invalid_fields','Criticality must be low, medium, high or critical.')
        row.criticality = value
    if 'location_id' in body:
        lid = integer(body['location_id'],'location_id',True)
        if lid:
            scoped(Location,lid)
        row.location_id = lid
    if creating:
        row.criticality = row.criticality or 'medium'
    duplicate = db.session.execute(db.select(Asset.id).where(Asset.company_id==g.membership.company_id,Asset.code==row.code,Asset.id!=row.id if row.id else True)).first()
    if duplicate:
        raise APIError('duplicate_code','This machine code is already in use.',409)


@bp.get('/locations')
@authorized()
def locations():
    rows = db.session.execute(db.select(Location).where(Location.company_id==g.membership.company_id).order_by(Location.id)).scalars().all()
    return {'locations':[location_json(r) for r in rows]}


@bp.post('/locations')
@authorized(*MANAGERS,mfa=True)
def add_location():
    body = data({'name','type','parent_id'},{'name','type'})
    kind = text(body,'type',50,True)
    pid = integer(body.get('parent_id'),'parent_id',True)
    if kind not in {'Site','Area','Line'}:
        raise APIError('invalid_fields','Location type must be Site, Area or Line.')
    parent = scoped(Location,pid) if pid else None
    if (kind=='Site' and parent) or (kind=='Area' and (not parent or parent.type!='Site')) or (kind=='Line' and (not parent or parent.type!='Area')):
        raise APIError('invalid_hierarchy','Use Site → Area → Line for the location hierarchy.')
    row = Location(company_id=g.membership.company_id,name=text(body,'name',100,True),type=kind,parent_id=pid)
    db.session.add(row)
    db.session.flush()
    row.path = (parent.path+'/' if parent else '')+str(row.id)
    result = {'location':location_json(row)}
    db.session.commit()
    return result,201


@bp.get('/assets')
@authorized()
def assets():
    query = db.select(Asset).where(Asset.company_id==g.membership.company_id)
    archived = request.args.get('include_archived','false')
    if archived not in {'true','false'}:
        raise APIError('invalid_filter','include_archived must be true or false.')
    if archived=='false':
        query = query.where(Asset.archived_at.is_(None))
    q = request.args.get('q','').strip()
    if len(q)>100:
        raise APIError('invalid_filter','Search is too long.')
    if q:
        escaped = q.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')
        query = query.where(db.or_(Asset.name.ilike('%'+escaped+'%',escape='\\'),Asset.code.ilike('%'+escaped+'%',escape='\\')))
    if request.args.get('location_id'):
        try:
            lid = int(request.args['location_id'])
        except ValueError:
            raise APIError('invalid_filter','Invalid location_id.')
        scoped(Location,integer(lid,'location_id'))
        query = query.where(Asset.location_id==lid)
    rows = db.session.execute(query.order_by(Asset.id).limit(1000)).scalars().all()
    return {'assets':[asset_json(r) for r in rows]}


@bp.post('/assets')
@authorized(*MANAGERS,mfa=True)
def add_asset():
    body = data(ASSET_FIELDS,{'code','name'})
    row = Asset(company_id=g.membership.company_id,status='Active')
    apply_asset(row,body,True)
    db.session.add(row)
    db.session.flush()
    result = {'asset':asset_json(row)}
    db.session.commit()
    return result,201


@bp.get('/assets/<int:identity>')
@authorized()
def get_asset(identity):
    return {'asset':asset_json(scoped(Asset,identity))}


@bp.patch('/assets/<int:identity>')
@authorized(*MANAGERS,mfa=True)
def edit_asset(identity):
    body = data(ASSET_FIELDS|{'revision'},{'revision'})
    row = scoped(Asset,identity,True)
    revision(row,body)
    if row.archived_at:
        raise APIError('archived','Archived machines cannot be edited.',409)
    apply_asset(row,body)
    row.revision += 1
    result = {'asset':asset_json(row)}
    db.session.commit()
    return result


@bp.delete('/assets/<int:identity>')
@authorized(*MANAGERS,mfa=True)
def archive_asset(identity):
    data(set())
    from app.pilot.security import tenant_lock
    tenant_lock(g.membership.company_id)
    row = scoped(Asset,identity,True)
    if not row.archived_at:
        row.archived_at = now()
        row.revision += 1
        from app.pilot.models import MaintenancePlan
        from app.pilot.scheduling import cancel_reminders
        for plan in db.session.execute(db.select(MaintenancePlan).where(MaintenancePlan.company_id==row.company_id,MaintenancePlan.asset_id==row.id)).scalars():
            cancel_reminders(row.company_id,plan_id=plan.id)
            plan.blocked_reason = 'archived_asset'
    result = {'asset':asset_json(row)}
    db.session.commit()
    return result


@bp.get('/summary')
@authorized()
def summary():
    tenant = g.membership.company_id
    def count(model,*conditions):
        return db.session.scalar(db.select(func.count()).select_from(model).where(model.company_id==tenant,*conditions))
    open_states = ['open','assigned','in_progress','blocked','awaiting_review']
    return {'asset_count':count(Asset,Asset.archived_at.is_(None)),'open_work_order_count':count(WorkOrder,WorkOrder.status.in_(open_states)),'awaiting_review_count':count(WorkOrder,WorkOrder.status=='awaiting_review'),'completed_work_order_count':count(WorkOrder,WorkOrder.status=='completed'),'overdue_work_order_count':count(WorkOrder,WorkOrder.status.in_(open_states),WorkOrder.due_at<now()),'document_count':count(Document,Document.deleted_at.is_(None))}
