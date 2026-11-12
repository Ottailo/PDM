"""Quarantined PDF submission and authorized extracted-text reading."""
import hashlib
import io
import secrets
from datetime import timedelta
from flask import Blueprint, current_app, g, request, send_file
from werkzeug.utils import secure_filename
from sqlalchemy import update
from app import db
from app.models import Asset
from app.pilot.models import Document, Job, now
from app.pilot.security import APIError, authorized, data, scoped, integer, iso, request_guard, tenant_lock
from app.pilot.quota import admit, capacity, blob_lock, release_staging
from app.pilot.storage import storage

bp = Blueprint('pilot_documents',__name__)


def document_json(row):
    asset = db.session.get(Asset,row.asset_id)
    return {'id':row.id,'title':row.title,'filename':row.filename,'asset_id':row.asset_id,'asset_name':asset.name,'status':row.status,'page_count':row.page_count,'error':row.error,'created_at':iso(row.created_at),'checksum':row.checksum,'revision':row.revision}


def visible(identity,lock=False):
    row = scoped(Document,identity,lock)
    if row.deleted_at:
        raise APIError('not_found','Document not found.',404)
    return row


@bp.post('/documents')
@authorized('owner','admin','planner','technician',mfa=True)
def upload():
    if set(request.form)-{'asset_id','title'} or set(request.files)!={'file'} or len(request.files.getlist('file'))!=1 or any(len(request.form.getlist(k))!=1 for k in request.form):
        raise APIError('invalid_fields','Provide file, asset_id and optional title only.')
    try:
        aid = int(request.form.get('asset_id',''))
    except ValueError:
        raise APIError('invalid_fields','asset_id is required.')
    asset = scoped(Asset,integer(aid,'asset_id'))
    if asset.archived_at:
        raise APIError('archived','Cannot attach manuals to an archived machine.',409)
    file = request.files['file']
    filename = secure_filename(file.filename or '')[:200]
    if not filename.lower().endswith('.pdf') or file.mimetype not in {'application/pdf','application/octet-stream'}:
        raise APIError('invalid_file','Upload a PDF document only.')
    content = file.stream.read(current_app.config['PDF_MAX_BYTES']+1)
    if not content or len(content)>current_app.config['PDF_MAX_BYTES']:
        raise APIError('file_too_large','PDF is empty or exceeds the upload limit.',413)
    if not content.startswith(b'%PDF-'):
        raise APIError('invalid_file','File does not have a valid PDF signature.')
    title = request.form.get('title',filename).strip()
    if not title or len(title)>200 or '\x00' in title:
        raise APIError('invalid_fields','Title must be 1–200 characters.')
    admit(len(content))
    key,token = secrets.token_hex(16)+'.pdf',secrets.token_hex(24)
    cid = g.membership.company_id
    row = Document(company_id=cid,asset_id=asset.id,title=title,filename=filename,blob_key=key,size=len(content),checksum=hashlib.sha256(content).hexdigest(),status='staging',staging_token=token,staging_until=now()+timedelta(seconds=current_app.config['DOCUMENT_STAGING_SECONDS']))
    db.session.add(row)
    db.session.flush()
    identity = row.id
    db.session.add(Job(kind='document',company_id=cid,identity=f'document:{identity}:1',payload={'document_id':identity,'revision':1},state='staging'))
    # Hold a reservation-specific I/O fence before publishing the charged staging row.
    with blob_lock(identity):
        db.session.commit()  # Authority guard ends before storage I/O.
        try:
            storage().put(key,content)
            request_guard()  # Fresh session/member/role after storage and gate wait.
            if not g.user:
                raise APIError('unauthorized','Sign in to continue.',401)
            if g.membership.company_id!=cid or g.membership.role not in {'owner','admin','planner','technician'}:
                raise APIError('forbidden','Upload access changed before admission completed.',403)
            if g.membership.role in {'owner','admin'} and not g.user.totp_secret:
                raise APIError('mfa_enrollment_required','Enroll an authenticator before making changes.',403)
            tenant_lock(cid)
            asset = scoped(Asset,aid)
            if asset.archived_at:
                raise APIError('archived','Cannot attach manuals to an archived machine.',409)
            job = db.session.execute(db.select(Job).where(Job.identity==f'document:{identity}:1').with_for_update()).scalar_one()
            row = scoped(Document,identity,True)
            if row.status!='staging' or row.staging_token!=token or job.state!='staging':
                raise APIError('upload_reservation_lost','Upload reservation is no longer available.',409)
            row.status,row.staging_token,row.staging_until = 'quarantined',None,None
            job.state = 'queued'
            result = {'document':document_json(row),'quota_remaining':capacity(cid)}
            db.session.commit()
        except Exception:
            db.session.rollback()
            try:
                release_staging(identity,token,'Upload did not complete; private storage cleaned up.')
            except Exception:
                db.session.rollback()  # Keep charged; bounded reconciler retries verified cleanup.
            raise
    return result,202


@bp.get('/documents')
@authorized()
def list_documents():
    query = db.select(Document).where(Document.company_id==g.membership.company_id,Document.deleted_at.is_(None))
    if request.args.get('asset_id'):
        try:
            aid = int(request.args['asset_id'])
        except ValueError:
            raise APIError('invalid_filter','Invalid asset_id.')
        scoped(Asset,integer(aid,'asset_id'))
        query = query.where(Document.asset_id==aid)
    return {'documents':[document_json(d) for d in db.session.execute(query.order_by(Document.id.desc()).limit(1000)).scalars()]}


@bp.get('/documents/<int:identity>')
@authorized()
def get_document(identity):
    return {'document':document_json(visible(identity))}


@bp.get('/documents/<int:identity>/download')
@authorized()
def download(identity):
    row = visible(identity)
    if row.status!='ready':
        raise APIError('document_not_ready','This document has not passed security processing.',409)
    content = storage().get(row.blob_key,current_app.config['PDF_MAX_BYTES'])
    if hashlib.sha256(content).hexdigest()!=row.checksum:
        raise APIError('document_integrity_failed','The stored document failed its integrity check.',409)
    return send_file(io.BytesIO(content),mimetype='application/pdf',as_attachment=True,download_name=row.filename,max_age=0)


@bp.get('/documents/<int:identity>/pages/<int:page>')
@authorized()
def page_text(identity,page):
    row = visible(identity)
    if row.status!='ready':
        raise APIError('document_not_ready','This document has not passed security processing.',409)
    if page<1 or page>(row.page_count or 0):
        raise APIError('not_found','Page not found.',404)
    return {'page_number':page,'text':row.pages[page-1]}


@bp.delete('/documents/<int:identity>')
@authorized('owner','admin','planner',mfa=True)
def delete_document(identity):
    data(set())
    tenant_lock(g.membership.company_id)
    candidate = visible(identity)  # Authorize before taking job locks.
    if candidate.status=='staging':
        raise APIError('upload_in_progress','Wait for this upload to finish before deleting it.',409)
    db.session.execute(db.select(Job).where(Job.identity.like(f'document:{identity}:%')).order_by(Job.id).with_for_update()).scalars().all()
    row = visible(identity,True)  # Same lock order as worker finalization: job then document.
    row.deleted_at = now()
    row.status = 'deleted'
    row.pages = None
    row.revision += 1
    db.session.execute(update(Job).where(Job.identity.like(f'document:{row.id}:%')).values(state='cancelled',lease_token=None,lease_until=None,payload={}))
    # Original private blob retained until an explicit retention purge. All access is revoked now.
    result = {'document':document_json(row)}
    db.session.commit()
    return result
