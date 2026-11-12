"""Verified identities, one-use tokens and encrypted authenticator enrollment."""
import secrets
from datetime import timedelta
from urllib.parse import urlencode
import pyotp
from cryptography.fernet import Fernet
from flask import Blueprint, current_app, g, session, request
from sqlalchemy import update, func
from werkzeug.security import check_password_hash, generate_password_hash
from app import db
from app.models import Company, User
from app.pilot.models import Membership, AuthSession, AuthToken, Job, AccessAudit, now
from app.pilot.security import APIError, authorized, data, text, email, password, submitted_password, digest, integer, new_session, recent_access, tenant_lock, iso, scoped

bp = Blueprint('pilot_auth',__name__)
GENERIC = 'If this address is eligible, a message has been queued. Check your inbox shortly.'


def cipher():
    return Fernet(current_app.config['MFA_ENCRYPTION_KEY'].encode())


def encrypt(value):
    return cipher().encrypt(value.encode()).decode()


def decrypt(value):
    return cipher().decrypt(value.encode()).decode()


def user_json(user):
    return {'id':user.id,'name':user.name,'email':user.email,'email_verified':bool(user.email_verified_at)}


def me_json(user=None,member=None):
    user,member = user or g.user,member or g.membership
    company = db.session.get(Company,member.company_id)
    role = member.role
    enrollment = role in {'owner','admin'} and not user.totp_secret
    return {'user':user_json(user),'company':{'id':company.id,'name':company.name,'timezone':company.timezone},'membership':{'id':member.id,'user_id':user.id,'role':role,'company_id':company.id},'mfa_enrollment_required':enrollment,'capabilities':{'manage_preventive_maintenance':role in {'owner','admin','planner'} and not enrollment,'manage_registry':role in {'owner','admin','planner'} and not enrollment,'manage_team':role in {'owner','admin'} and not enrollment,'manage_work_orders':role in {'owner','admin','planner'} and not enrollment,'request_work_orders':role in {'owner','admin','planner','technician'} and not enrollment,'upload_documents':role in {'owner','admin','planner','technician'} and not enrollment}}


def issue_token(kind,email_address,user_id=None,company_id=None,role=None):
    raw = secrets.token_urlsafe(32)
    row = AuthToken(digest=digest(raw),kind=kind,email=email_address,user_id=user_id,company_id=company_id,role=role,expires_at=now()+timedelta(hours=1 if kind=='reset' else 48))
    db.session.add(row)
    db.session.flush()
    path = {'verify':'/verify-email','reset':'/reset-password','invite':'/invite'}[kind]
    url = current_app.config['APP_BASE_URL'].rstrip('/')+path+'?'+urlencode({'token':raw})
    subjects = {'verify':'Verify your Machivital email','reset':'Reset your Machivital password','invite':'Your Machivital team invitation'}
    message = f'{subjects[kind]}\n\nOpen this link:\n{url}\n\nThis link expires and can be used only once. If you did not request it, ignore this message.'
    db.session.add(Job(kind='mail',company_id=company_id,token_id=row.id,identity=f'auth-token:{row.id}',payload={'to':email_address,'subject':subjects[kind],'body_encrypted':encrypt(message)}))
    return row


def token_row(raw,kind,lock=True):
    if not isinstance(raw,str) or len(raw)>200:
        raise APIError('invalid_token','This link is invalid or expired.')
    query = db.select(AuthToken).where(AuthToken.digest==digest(raw),AuthToken.kind==kind).execution_options(populate_existing=True)
    if lock:
        query = query.with_for_update()
    row = db.session.execute(query).scalar_one_or_none()
    if not row or row.consumed_at or row.expires_at <= now():
        raise APIError('invalid_token','This link is invalid, expired, or already used.')
    return row


def invalidate_tokens(query):
    ids = list(db.session.execute(query.order_by(AuthToken.id).with_for_update()).scalars())
    if ids:
        db.session.execute(update(AuthToken).where(AuthToken.id.in_(ids)).values(consumed_at=now()))
        db.session.execute(update(Job).where(Job.token_id.in_(ids),Job.state.in_(['queued','running','staging'])).values(state='cancelled',payload={},lease_token=None,lease_until=None))


def consume_other_tokens(user_id,kind):
    invalidate_tokens(db.select(AuthToken.id).where(AuthToken.user_id==user_id,AuthToken.kind==kind,AuthToken.consumed_at.is_(None)))


def check_mfa(user,code):
    if not isinstance(code,str) or len(code) not in {6,16}:
        return False
    if len(code)==6 and code.isdigit():
        totp = pyotp.TOTP(decrypt(user.totp_secret))
        counter = int(now().timestamp()) // 30
        for candidate in (counter-1,counter,counter+1):
            if candidate > user.totp_last_counter and secrets.compare_digest(totp.at(candidate*30),code):
                user.totp_last_counter = candidate
                return True
    hashes = list(user.recovery_hashes or [])
    for index,value in enumerate(hashes):
        if check_password_hash(value,code):
            hashes.pop(index)
            user.recovery_hashes = hashes
            return True
    return False


@bp.get('/csrf')
def csrf():
    session.setdefault('csrf',secrets.token_urlsafe(32))
    return {'csrf_token':session['csrf']}


@bp.post('/auth/signup')
def signup():
    body = data({'name','email','password','company_name'},{'name','email','password','company_name'})
    address = email(body)
    pw = password(body)
    name = text(body,'name',100,True)
    company_name = text(body,'company_name',100,True)
    if db.session.execute(db.select(User.id).where(User.email==address)).first():
        raise APIError('account_exists','An account with this email already exists.',409)
    company = Company(name=company_name,industry='Manufacturing',contact_email=address)
    user = User(username=secrets.token_hex(16),name=name,email=address)
    user.set_password(pw)
    db.session.add_all([company,user])
    db.session.flush()
    db.session.add(Membership(company_id=company.id,user_id=user.id,role='owner'))
    issue_token('verify',address,user.id)
    result = {'user':user_json(user),'company':{'id':company.id,'name':company.name},'message':'Account created. Verification email queued; verify before signing in.'}
    db.session.commit()
    return result,201


@bp.post('/auth/verify-email')
def verify():
    body = data({'token'},{'token'})
    preview = token_row(body['token'],'verify',lock=False)
    user = db.session.execute(db.select(User).where(User.id==preview.user_id).with_for_update()).scalar_one()
    row = token_row(body['token'],'verify')
    user.email_verified_at = now()
    row.consumed_at = now()
    consume_other_tokens(user.id,'verify')
    db.session.commit()
    return {'message':'Email verified. You can now sign in.'}


@bp.post('/auth/resend-verification')
@bp.post('/auth/forgot-password')
def send_token():
    body = data({'email'},{'email'})
    address = email(body)
    user = db.session.execute(db.select(User).where(User.email==address).with_for_update()).scalar_one_or_none()
    kind = 'reset' if request.path.endswith('forgot-password') else 'verify'
    if user and user.is_enabled and ((kind=='reset' and user.email_verified_at) or (kind=='verify' and not user.email_verified_at)):
        consume_other_tokens(user.id,kind)
        issue_token(kind,address,user.id)
    db.session.commit()
    return {'message':GENERIC},202


@bp.post('/auth/reset-password')
def reset():
    body = data({'token','password'},{'token','password'})
    pw = password(body)
    preview = token_row(body['token'],'reset',lock=False)
    user = db.session.execute(db.select(User).where(User.id==preview.user_id).with_for_update()).scalar_one()
    row = token_row(body['token'],'reset')
    user.set_password(pw)
    row.consumed_at = now()
    consume_other_tokens(user.id,'reset')
    db.session.execute(update(AuthSession).where(AuthSession.user_id==user.id,AuthSession.revoked_at.is_(None)).values(revoked_at=now()))
    db.session.commit()
    session.pop('sid',None)
    return {'message':'Password updated. Sign in with your new password.'}


@bp.post('/auth/login')
def login():
    body = data({'email','password','totp_code'},{'email','password'})
    address = email(body)
    pw = submitted_password(body)
    user = db.session.execute(db.select(User).where(User.email==address).with_for_update()).scalar_one_or_none()
    # A real hash operation on unknown addresses reduces timing enumeration.
    if not user:
        check_password_hash(current_app.config['DUMMY_PASSWORD_HASH'],pw)
        raise APIError('invalid_credentials','Email or password is incorrect.',401)
    if not user.check_password(pw) or not user.is_enabled:
        raise APIError('invalid_credentials','Email or password is incorrect.',401)
    if not user.email_verified_at:
        raise APIError('email_unverified','Verify your email before signing in.',403)
    if user.totp_secret and not check_mfa(user,body.get('totp_code')):
        raise APIError('mfa_required','Enter your authenticator code or an unused recovery code.',401)
    members = db.session.execute(db.select(Membership).join(Company,Company.id==Membership.company_id).where(Membership.user_id==user.id,Membership.active.is_(True),Company.is_active.is_(True)).order_by(Membership.id)).scalars().all()
    if not members:
        raise APIError('forbidden','No active organization membership.',403)
    new_session(user,members[0])
    user.last_login = now()
    result = me_json(user,members[0])
    db.session.commit()
    return result


@bp.post('/auth/reauth')
@authorized()
def reauthenticate():
    body = data({'password','totp_code'},{'password','totp_code'})
    user = db.session.execute(db.select(User).where(User.id==g.user.id).with_for_update()).scalar_one()
    if not user.check_password(submitted_password(body)):
        raise APIError('invalid_credentials','Password is incorrect.',401)
    if not user.totp_secret:
        raise APIError('mfa_enrollment_required','Enroll an authenticator before confirming access changes.',403)
    if not check_mfa(user,body['totp_code']):
        raise APIError('mfa_required','Enter your authenticator code or an unused recovery code.',401)
    g.auth_session.access_confirmed_at = now()
    db.session.commit()
    return {'message':'Access confirmed for five minutes.'}


@bp.get('/auth/me')
@authorized()
def me():
    return me_json()


@bp.post('/auth/logout')
@authorized()
def logout():
    data(set())
    g.auth_session.revoked_at = now()
    db.session.commit()
    csrf_value = session.get('csrf')
    session.clear()
    session['csrf'] = csrf_value or secrets.token_urlsafe(32)
    return {'message':'Signed out.'}


@bp.get('/auth/mfa')
@authorized()
def mfa_status():
    return {'enabled':bool(g.user.totp_secret),'enrollment_required':g.membership.role in {'owner','admin'} and not g.user.totp_secret,'recovery_codes_remaining':len(g.user.recovery_hashes or [])}


@bp.post('/auth/mfa/setup')
@authorized()
def mfa_setup():
    body = data({'password'},{'password'})
    user = db.session.execute(db.select(User).where(User.id==g.user.id).with_for_update()).scalar_one()
    if not user.check_password(submitted_password(body)):
        raise APIError('invalid_credentials','Password is incorrect.',401)
    if user.totp_secret:
        raise APIError('mfa_already_enabled','Authenticator is already enrolled.',409)
    secret = pyotp.random_base32()
    user.totp_pending_secret = encrypt(secret)
    user.totp_pending_until = now()+timedelta(minutes=10)
    db.session.commit()
    return {'secret':secret,'otpauth_url':pyotp.TOTP(secret).provisioning_uri(name=user.email,issuer_name='Machivital')}


@bp.post('/auth/mfa/confirm')
@authorized()
def mfa_confirm():
    body = data({'code'},{'code'})
    user = db.session.execute(db.select(User).where(User.id==g.user.id).with_for_update()).scalar_one()
    if user.totp_secret or not user.totp_pending_secret or not user.totp_pending_until or user.totp_pending_until <= now():
        raise APIError('enrollment_expired','Start authenticator enrollment again.',409)
    secret = decrypt(user.totp_pending_secret)
    code = text(body,'code',6,True)
    totp = pyotp.TOTP(secret)
    counter = int(now().timestamp())//30
    matched = next((c for c in (counter-1,counter,counter+1) if secrets.compare_digest(totp.at(c*30),code)),None)
    if matched is None:
        raise APIError('invalid_mfa','Authenticator code is incorrect.',400)
    codes = [secrets.token_hex(8) for _ in range(10)]
    user.totp_secret = user.totp_pending_secret
    user.totp_pending_secret = None
    user.totp_pending_until = None
    user.totp_last_counter = matched
    user.recovery_hashes = [generate_password_hash(c) for c in codes]
    # Pre-enrollment sessions must never inherit commercial access without proving MFA.
    db.session.execute(update(AuthSession).where(AuthSession.user_id==user.id,AuthSession.id!=g.auth_session.id,AuthSession.revoked_at.is_(None)).values(revoked_at=now()))
    db.session.commit()
    return {'recovery_codes':codes}


@bp.get('/companies')
@authorized()
def companies():
    rows = db.session.execute(db.select(Company,Membership).join(Membership,Membership.company_id==Company.id).where(Membership.user_id==g.user.id,Membership.active.is_(True),Company.is_active.is_(True)).order_by(Company.id)).all()
    return {'companies':[{'id':c.id,'name':c.name,'role':m.role} for c,m in rows]}


@bp.post('/companies/switch')
@authorized()
def switch():
    body = data({'company_id'},{'company_id'})
    cid = integer(body['company_id'],'company_id')
    member = db.session.execute(db.select(Membership).join(Company,Company.id==Membership.company_id).where(Membership.company_id==cid,Membership.user_id==g.user.id,Membership.active.is_(True),Company.is_active.is_(True))).scalar_one_or_none()
    if not member:
        raise APIError('not_found','Organization not found.',404)
    g.auth_session.membership_id = member.id
    g.auth_session.access_confirmed_at = None
    result = me_json(g.user,member)
    db.session.commit()
    return result


@bp.get('/members')
@authorized()
def members():
    rows = db.session.execute(db.select(Membership,User).join(User,User.id==Membership.user_id).where(Membership.company_id==g.membership.company_id,Membership.active.is_(True)).order_by(Membership.id)).all()
    return {'members':[{'id':m.id,'user_id':u.id,'name':u.name,'email':u.email,'role':m.role,'active':m.active,'revision':m.revision} for m,u in rows]}


@bp.post('/invitations')
@authorized('owner','admin',mfa=True)
def invite():
    body = data({'email','role'},{'email','role'})
    address = email(body)
    role = text(body,'role',20,True)
    if role not in {'admin','planner','technician','stores','viewer'} or (g.membership.role=='admin' and role=='admin'):
        raise APIError('forbidden','You cannot invite this role.',403)
    # Serialize invitations per company; an outstanding replacement invalidates old links.
    tenant_lock(g.membership.company_id)
    db.session.execute(db.select(Company).where(Company.id==g.membership.company_id).with_for_update()).scalar_one()
    existing = db.session.execute(db.select(Membership).join(User,User.id==Membership.user_id).where(Membership.company_id==g.membership.company_id,User.email==address,Membership.active.is_(True))).scalar_one_or_none()
    if existing:
        raise APIError('already_member','This person is already a team member.',409)
    invalidate_tokens(db.select(AuthToken.id).where(AuthToken.company_id==g.membership.company_id,AuthToken.email==address,AuthToken.kind=='invite',AuthToken.consumed_at.is_(None)))
    issue_token('invite',address,company_id=g.membership.company_id,role=role)
    db.session.commit()
    return {'message':'Invitation queued.'},201


@bp.get('/invitations')
@authorized('owner','admin',mfa=True)
def list_invitations():
    rows = db.session.execute(db.select(AuthToken).where(AuthToken.company_id==g.membership.company_id,AuthToken.kind=='invite',AuthToken.consumed_at.is_(None),AuthToken.expires_at>now()).order_by(AuthToken.id)).scalars()
    return {'invitations':[{'id':r.id,'email':r.email,'role':r.role,'expires_at':iso(r.expires_at)} for r in rows]}


def team_target(identity):
    tenant_lock(g.membership.company_id)
    target = scoped(Membership,integer(identity))
    if not target.active:
        raise APIError('not_found','Active team member not found.',404)
    if g.membership.role=='admin' and target.role in {'owner','admin'}:
        raise APIError('forbidden','Only an owner can manage privileged members.',403)
    return target


def access_audit(action, reason, target=None, invitation=None, role=None, active=None):
    db.session.add(AccessAudit(company_id=g.membership.company_id,actor_id=g.user.id,
        target_id=target.user_id if target else None,membership_id=target.id if target else None,
        invitation_id=invitation.id if invitation else None,action=action,
        old_role=target.role if target else invitation.role,new_role=role,
        old_active=target.active if target else True,new_active=active,reason=reason))


def revoke_member_sessions(target):
    db.session.execute(update(AuthSession).where(AuthSession.membership_id==target.id,AuthSession.revoked_at.is_(None)).values(revoked_at=now(),access_confirmed_at=None))


@bp.patch('/members/<int:identity>')
@authorized('owner','admin',mfa=True)
def change_member(identity):
    body = data({'role','reason'},{'role','reason'})
    recent_access()
    role = text(body,'role',20,True)
    reason = text(body,'reason',1000,True)
    if role not in {'owner','admin','planner','technician','stores','viewer'} or (g.membership.role=='admin' and role in {'owner','admin'}):
        raise APIError('forbidden','Your role cannot grant privileged access.',403)
    target = team_target(identity)
    if target.role=='owner' and role!='owner':
        ensure_replacement_owner(target)
    old_role = target.role
    access_audit('role_change',reason,target,role=role,active=True)
    target.role = role
    target.revision += 1
    if old_role != role:
        revoke_member_sessions(target)
        if role not in {'owner','admin','planner','technician'} or (old_role in {'owner','admin','planner'} and role not in {'owner','admin','planner'}):
            from app.pilot.scheduling import cancel_reminders
            cancel_reminders(target.company_id,recipient_id=target.id,stage='overdue' if role in {'owner','admin','planner','technician'} else None)
    result = {'member':{'id':target.id,'user_id':target.user_id,'role':target.role,'active':target.active,'revision':target.revision},'message':'Member role updated. Existing organization sessions revoked.'}
    db.session.commit()
    return result


def ensure_replacement_owner(target):
    owners = db.session.scalar(db.select(func.count()).select_from(Membership).where(Membership.company_id==target.company_id,Membership.active.is_(True),Membership.role=='owner',Membership.id!=target.id))
    if not owners:
        raise APIError('last_owner','Promote another active member to owner before removing or demoting the last owner.',409)


@bp.delete('/members/<int:identity>')
@authorized('owner','admin',mfa=True)
def offboard_member(identity):
    body = data({'reason'},{'reason'})
    recent_access()
    reason = text(body,'reason',1000,True)
    target = team_target(identity)
    if target.role=='owner':
        ensure_replacement_owner(target)
    address = db.session.get(User,target.user_id).email
    invalidate_tokens(db.select(AuthToken.id).where(AuthToken.company_id==target.company_id,AuthToken.email==address,AuthToken.kind=='invite',AuthToken.consumed_at.is_(None)))
    access_audit('offboard',reason,target,role=target.role,active=False)
    target.active = False
    target.revision += 1
    revoke_member_sessions(target)
    from app.pilot.scheduling import cancel_reminders
    cancel_reminders(target.company_id,recipient_id=target.id)
    db.session.commit()
    return {'message':'Member access removed. Previously downloaded files cannot be recalled.'}


@bp.delete('/invitations/<int:identity>')
@authorized('owner','admin',mfa=True)
def cancel_invitation(identity):
    body = data({'reason'},{'reason'})
    recent_access()
    tenant_lock(g.membership.company_id)
    row = scoped(AuthToken,integer(identity))
    if row.kind!='invite' or row.consumed_at or row.expires_at<=now():
        raise APIError('not_found','Pending invitation not found.',404)
    if g.membership.role=='admin' and row.role in {'owner','admin'}:
        raise APIError('forbidden','Only an owner can cancel privileged invitations.',403)
    access_audit('invitation_cancel',text(body,'reason',1000,True),invitation=row,active=False)
    invalidate_tokens(db.select(AuthToken.id).where(AuthToken.id==row.id))
    db.session.commit()
    return {'message':'Invitation cancelled.'}


@bp.get('/invitations/preview')
def preview():
    row = token_row(request.args.get('token'),'invite',lock=False)
    company = db.session.get(Company,row.company_id)
    if not company or not company.is_active:
        raise APIError('invalid_token','Invitation is no longer available.')
    return {'company':{'id':company.id,'name':company.name},'email':row.email,'role':row.role}


@bp.post('/invitations/accept')
def accept():
    body = data({'token','name','password'},{'token'})
    preview = token_row(body['token'],'invite',lock=False)
    tenant_lock(preview.company_id)
    user = db.session.execute(db.select(User).where(User.email==preview.email).with_for_update()).scalar_one_or_none()
    company = db.session.execute(db.select(Company).where(Company.id==preview.company_id).with_for_update()).scalar_one()
    row = token_row(body['token'],'invite')
    if not company.is_active or row.role not in {'admin','planner','technician','stores','viewer'}:
        raise APIError('invalid_token','Invitation is no longer available.')
    if user:
        if not g.user or g.user.id!=user.id:
            raise APIError('authentication_required','Sign in to your existing account before accepting.',401)
        # Existing passwords are never changed by invitation acceptance.
    else:
        user = User(username=secrets.token_hex(16),email=row.email,name=text(body,'name',100,True),email_verified_at=now())
        user.set_password(password(body))
        db.session.add(user)
        db.session.flush()
    member = db.session.execute(db.select(Membership).where(Membership.company_id==company.id,Membership.user_id==user.id).with_for_update()).scalar_one_or_none()
    if member and member.active:
        raise APIError('already_member','You are already a team member.',409)
    if member:
        member.active,member.role = True,row.role
        member.revision += 1
    else:
        db.session.add(Membership(company_id=company.id,user_id=user.id,role=row.role))
    row.consumed_at = now()
    db.session.commit()
    return {'message':'Invitation accepted. Sign in or switch organizations to continue.'}
