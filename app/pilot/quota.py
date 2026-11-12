"""Charged upload reservations and bounded, ownership-verified crash cleanup."""
from contextlib import contextmanager
from datetime import timedelta
from sqlalchemy import func, text
from flask import current_app, g
from app import db
from app.pilot.models import Document, Job, now
from app.pilot.security import APIError, transaction_guard, tenant_lock
from app.pilot.storage import storage


def capacity(company_id):
    retained = db.session.execute(db.select(func.coalesce(func.sum(Document.size),0),func.count(Document.id)).where(Document.company_id==company_id,Document.storage_released_at.is_(None))).one()
    pending = db.session.scalar(db.select(func.count()).select_from(Job).where(Job.company_id==company_id,Job.kind=='document',Job.state.in_(['staging','queued','running'])))
    return {'bytes':max(0,current_app.config['DOCUMENT_QUOTA_BYTES']-retained[0]),
            'files':max(0,current_app.config['DOCUMENT_QUOTA_FILES']-retained[1]),
            'pending':max(0,current_app.config['DOCUMENT_PENDING_LIMIT']-pending)}


def admit(size):
    tenant_lock(g.membership.company_id)
    remaining = capacity(g.membership.company_id)
    if size>remaining['bytes'] or remaining['files']<1 or remaining['pending']<1:
        raise APIError('document_quota_exceeded','This factory has reached its retained manual or pending-processing limit.',429,{'remaining':remaining})
    return remaining


@contextmanager
def blob_lock(identity,wait=True):
    """Session-level reservation I/O fence, independent of short authority guards.

    A live uploader retains this fence over storage and finalization. A crashed process
    releases it at connection close, allowing bounded cleanup. No directory scanning.
    """
    with db.engine.connect().execution_options(isolation_level='AUTOCOMMIT') as connection:
        function = 'pg_advisory_lock' if wait else 'pg_try_advisory_lock'
        result = connection.execute(text(f'SELECT {function}(731195, :id)'),{'id':identity}).scalar()
        acquired = True if wait else result
        try:
            yield acquired
        finally:
            if acquired:
                connection.execute(text('SELECT pg_advisory_unlock(731195, :id)'),{'id':identity})


def release_staging(identity,token,error):
    """Caller owns blob fence. Capacity is released only after confirmed deletion."""
    transaction_guard()
    row = db.session.get(Document,identity)
    if not row or row.status!='staging' or row.staging_token!=token:
        db.session.rollback()
        return False
    key,cid = row.blob_key,row.company_id
    db.session.commit()
    storage().delete(key)
    transaction_guard()
    tenant_lock(cid)
    job = db.session.execute(db.select(Job).where(Job.identity==f'document:{identity}:1').with_for_update()).scalar_one_or_none()
    row = db.session.execute(db.select(Document).where(Document.id==identity).with_for_update().execution_options(populate_existing=True)).scalar_one()
    if row.status!='staging' or row.staging_token!=token:
        db.session.rollback()
        return False
    row.status,row.error,row.storage_released_at = 'failed',error[:300],now()
    row.staging_token,row.staging_until = None,None
    if job:
        job.state,job.payload,job.lease_token,job.lease_until = 'cancelled',{},None,None
    db.session.commit()
    return True


def reconcile_staging(app):
    """Reconcile only expired persisted reservations, never arbitrary private files."""
    cleaned = 0
    with app.app_context():
        candidates = db.session.execute(db.select(Document.id,Document.staging_token).where(Document.status=='staging',Document.staging_until<=now()).order_by(Document.id).limit(app.config['DOCUMENT_RECONCILE_LIMIT'])).all()
        db.session.rollback()
        for identity,token in candidates:
            with blob_lock(identity,wait=False) as acquired:
                if not acquired:
                    continue
                try:
                    if release_staging(identity,token,'Abandoned upload reservation cleaned up.'):
                        cleaned += 1
                except Exception:
                    db.session.rollback()  # Keep failed cleanup charged for the next bounded pass.
        return {'reconciled':cleaned}
