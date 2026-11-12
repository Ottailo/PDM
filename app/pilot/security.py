"""Validation, authoritative authorization and transactional replay protection."""
import hashlib
import hmac
import json
import re
import secrets
from datetime import timedelta
from functools import wraps
from flask import current_app, g, request, session
from sqlalchemy import text as sql_text
from sqlalchemy.dialects.postgresql import insert
from app import db
from app.models import User, Company
from app.pilot.models import AuthSession, Membership, RateBucket, Idempotency, now


class APIError(Exception):
    def __init__(self, code, message, status=400, fields=None):
        self.code, self.message, self.status, self.fields = code, message, status, fields


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def iso(value):
    return value.isoformat().replace('+00:00', 'Z') if value else None


def data(allowed, required=()):
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise APIError('invalid_body', 'A JSON object is required.')
    unknown = set(body) - set(allowed)
    missing = set(required) - set(body)
    if unknown or missing:
        raise APIError('invalid_fields', 'Unknown or missing fields.', fields={**{k:'Unknown field' for k in unknown}, **{k:'Required' for k in missing}})
    return body


def text(body, key, maximum=200, required=False, default=''):
    value = body.get(key, default)
    if not isinstance(value, str) or len(value) > maximum or (required and not value.strip()) or '\x00' in value:
        raise APIError('invalid_fields', f'Invalid {key}.', fields={key:f'Must be text, at most {maximum} characters.'})
    return value.strip()


def integer(value, key='id', nullable=False):
    if value is None and nullable:
        return None
    if type(value) is not int or value <= 0:
        raise APIError('invalid_fields', f'{key} must be a positive integer.')
    return value


def email(body):
    value = text(body, 'email', 120, True).lower()
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', value):
        raise APIError('invalid_fields', 'Enter a valid email address.')
    return value


def password(body):
    value = body.get('password')
    if not isinstance(value, str) or not 12 <= len(value) <= 128 or len(set(value)) < 5 or value.lower() in {'password1234','password123456','123456789012','abcdefghijkl'}:
        raise APIError('weak_password', 'Use a unique password of 12–128 characters.')
    return value


def submitted_password(body):
    """Validate credential shape without changing its exact contents."""
    value = body.get('password')
    if not isinstance(value, str) or not value or len(value) > 128 or '\x00' in value:
        raise APIError('invalid_fields', 'Enter your password.')
    return value


def rate_limit():
    if request.method not in {'POST','PATCH','DELETE','PUT'} or not request.path.startswith('/api/v1/'):
        return
    if request.path.startswith('/api/v1/auth/') or request.path.startswith('/api/v1/invitations') or request.path=='/api/v1/companies/switch':
        window = int(now().timestamp()) // 600
        # IP comes from the actual peer, never arbitrary forwarded headers.
        key = digest(f'{request.remote_addr}:{request.path}:{window}')
        db.session.execute(insert(RateBucket).values(key=key,count=1,expires_at=now()+timedelta(minutes=20)).on_conflict_do_update(index_elements=['key'],set_={'count':RateBucket.count+1}))
        row = db.session.get(RateBucket,key)
        count = row.count
        db.session.commit()  # Failed authentication attempts also count.
        if count > current_app.config['AUTH_RATE_LIMIT']:
            raise APIError('rate_limited','Too many attempts. Try again later.',429)
    elif request.path=='/api/v1/documents' and request.method=='POST':
        load_identity()  # Discovery only; authoritative refresh follows the counter commit.
        if not g.user:
            return
        seconds = current_app.config['DOCUMENT_UPLOAD_WINDOW_SECONDS']
        window = int(now().timestamp()) // seconds
        counts = []
        for scope in (f'tenant:{g.membership.company_id}',f'actor:{g.membership.company_id}:{g.user.id}'):
            key = digest(f'upload:{scope}:{window}')
            counts.append(db.session.execute(insert(RateBucket).values(key=key,count=1,expires_at=now()+timedelta(seconds=seconds*2)).on_conflict_do_update(index_elements=['key'],set_={'count':RateBucket.count+1}).returning(RateBucket.count)).scalar_one())
        db.session.commit()
        if max(counts)>current_app.config['DOCUMENT_UPLOAD_RATE_LIMIT']:
            raise APIError('document_upload_rate_limited','Too many upload attempts for this factory. Try again later.',429)


def csrf_check():
    if request.method in {'POST','PUT','PATCH','DELETE'}:
        supplied = request.headers.get('X-CSRF-Token','')
        expected = session.get('csrf','')
        if not expected or not hmac.compare_digest(supplied,expected):
            raise APIError('csrf_failed','Refresh the page and try again.',403)
        origin = request.headers.get('Origin')
        if origin and origin not in current_app.config['ALLOWED_ORIGINS']:
            raise APIError('origin_denied','Request origin is not allowed.',403)


# One deliberate pilot-wide readers/writer gate. Order: gate -> tenant/scheduler
# -> User -> Company -> AuthToken -> Membership -> AuthSession -> Idempotency
# -> Job -> domain rows. No shared-to-exclusive upgrades or external I/O under it.
AUTH_GUARD = 73119401002


def transaction_guard(exclusive=False):
    connection_session = db.session()
    transaction = connection_session.get_transaction()
    held = connection_session.info.get('pilot_guard')
    if held and held[0] is transaction and transaction is not None:
        if exclusive and not held[1]:
            raise RuntimeError('Identity guard cannot be upgraded')
        return
    function = 'pg_advisory_xact_lock' if exclusive else 'pg_advisory_xact_lock_shared'
    db.session.execute(sql_text(f'SELECT {function}(:key)'), {'key': AUTH_GUARD})
    connection_session.info['pilot_guard'] = (connection_session.get_transaction(), exclusive)


def request_guard():
    if request.method in {'POST','PATCH','DELETE','PUT'}:
        exclusive = (request.path.startswith(('/api/v1/auth/', '/api/v1/invitations', '/api/v1/members/'))
                     or request.path == '/api/v1/companies/switch')
        transaction_guard(exclusive)
    # Discard authority read before waiting for the gate, including replay paths.
    db.session.expire_all()
    load_identity()


def recent_access():
    confirmed = g.auth_session.access_confirmed_at if g.auth_session else None
    if not confirmed or confirmed <= now()-timedelta(minutes=5):
        raise APIError('reauthentication_required','Confirm your password and authenticator to change team access.',403)


def tenant_lock(company_id):
    # A separate namespace from the identity guard; always acquired before row locks.
    db.session.execute(sql_text('SELECT pg_advisory_xact_lock(731194, :tenant)'), {'tenant': company_id})


def load_identity():
    g.user = g.membership = g.auth_session = None
    sid = session.get('sid')
    if not sid:
        return
    auth = db.session.get(AuthSession,digest(sid))
    if not auth or auth.revoked_at or auth.expires_at <= now():
        session.pop('sid',None)
        return
    member = db.session.get(Membership,auth.membership_id)
    user = db.session.get(User,auth.user_id)
    company = db.session.get(Company,member.company_id) if member else None
    if not member or not member.active or not user or not user.is_enabled or not user.email_verified_at or not company or not company.is_active or member.user_id != user.id:
        session.pop('sid',None)
        return
    g.user,g.membership,g.auth_session = user,member,auth


def authorized(*roles, mfa=False):
    def decorate(function):
        @wraps(function)
        def wrapped(*args,**kwargs):
            if request.method in {'POST','PATCH','DELETE','PUT'}:
                request_guard()
            if not g.user:
                raise APIError('unauthorized','Sign in to continue.',401)
            if roles and g.membership.role not in roles:
                raise APIError('forbidden','Your role cannot perform this action.',403)
            if mfa and g.membership.role in {'owner','admin'} and not g.user.totp_secret:
                raise APIError('mfa_enrollment_required','Enroll an authenticator before making changes.',403)
            return function(*args,**kwargs)
        return wrapped
    return decorate


def scoped(model, identity, lock=False):
    query = db.select(model).where(model.id==identity,model.company_id==g.membership.company_id)
    if lock:
        query = query.with_for_update()
    row = db.session.execute(query).scalar_one_or_none()
    if not row:
        raise APIError('not_found','Record not found.',404)
    return row


def revision(row, body):
    if type(body.get('revision')) is not int or body['revision'] != row.revision:
        raise APIError('revision_conflict','This record changed. Refresh before saving.',409)


def idempotent(function):
    @wraps(function)
    def wrapped(*args,**kwargs):
        key = request.headers.get('Idempotency-Key','')
        if not 8 <= len(key) <= 128 or not re.fullmatch(r'[A-Za-z0-9._:-]+',key):
            raise APIError('idempotency_required','Provide an Idempotency-Key of 8–128 safe characters.')
        # Domain mutation/replay order: authority guard -> tenant -> Company -> replay -> plan/Job/domain.
        # Taking the tenant fence before replay also prevents opposite-order PM worker/API deadlocks.
        tenant_lock(g.membership.company_id)
        db.session.execute(db.select(Company).where(Company.id==g.membership.company_id).with_for_update()).scalar_one()
        fingerprint = digest(request.method+request.path+json.dumps(request.get_json(silent=True),sort_keys=True,separators=(',',':')))
        values = dict(company_id=g.membership.company_id,user_id=g.user.id,key=key,digest=fingerprint)
        db.session.execute(insert(Idempotency).values(**values).on_conflict_do_nothing(index_elements=['company_id','user_id','key']))
        row = db.session.execute(db.select(Idempotency).filter_by(company_id=g.membership.company_id,user_id=g.user.id,key=key).with_for_update()).scalar_one()
        if row.digest != fingerprint:
            raise APIError('idempotency_conflict','This key was used for a different request.',409)
        if row.response is not None:
            return row.response,row.status_code
        result = function(*args,**kwargs)
        body,status = result if isinstance(result,tuple) else (result,200)
        row.response,row.status_code = body,status
        db.session.commit()
        return body,status
    return wrapped


def new_session(user, member):
    session.clear()
    sid = secrets.token_urlsafe(32)
    db.session.add(AuthSession(id=digest(sid),user_id=user.id,membership_id=member.id,expires_at=now()+timedelta(hours=12)))
    session['sid'] = sid
    session['csrf'] = secrets.token_urlsafe(32)
    session.permanent = True
