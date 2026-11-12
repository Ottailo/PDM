from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import pytest
from sqlalchemy import func
from app import db
from app.models import User, Company
from app.pilot.models import AuthSession, AuthToken, Job, now
from conftest import api,register,mail_token


def test_no_startup_seed_and_legacy_disabled(app,client):
    with app.app_context():
        assert db.session.scalar(db.select(func.count()).select_from(User))==0
        assert db.session.scalar(db.select(func.count()).select_from(Company))==0
    assert client.get('/healthz').status_code==200
    assert client.get('/readyz').status_code==200
    for path in ['/api/latest-states','/api/history','/api/ingest','/auth/setup-admin','/admin','/mobile','/static/uploads/test.pdf']:
        assert client.get(path).status_code==410
    assert client.get('/api/v1/auth/me').status_code==401
    assert client.post('/api/v1/auth/signup',json={}).status_code==403
    assert client.get('/healthz').headers['Cache-Control'].startswith('private, no-store')


def test_signup_verification_one_use_and_mfa_gate(app,client):
    pw = 'Correct-horse-battery-73!'
    response = api(client,'/auth/signup',{'name':'Owner','email':'owner@example.test','password':pw,'company_name':'Plant','role':'admin'})
    assert response.status_code==400
    assert api(client,'/auth/signup',{'name':'Owner','email':'owner@example.test','password':'password1234','company_name':'Plant'}).status_code==400
    response = api(client,'/auth/signup',{'name':'Owner','email':'owner@example.test','password':pw,'company_name':'Plant'})
    assert response.status_code==201
    assert 'token' not in response.get_json()
    assert client.get('/api/v1/auth/me').status_code==401
    assert api(client,'/auth/login',{'email':'owner@example.test','password':pw}).status_code==403
    token = mail_token(app,'verify')
    assert api(client,'/auth/verify-email',{'token':token}).status_code==200
    assert api(client,'/auth/verify-email',{'token':token}).status_code==400
    response = api(client,'/auth/login',{'email':'owner@example.test','password':pw})
    assert response.status_code==200
    assert response.get_json()['mfa_enrollment_required']
    assert api(client,'/assets',{'code':'P1','name':'Pump'}).status_code==403
    assert api(client,'/auth/mfa/setup',{'password':'incorrect-password'}).status_code==401
    before_enrollment = app.test_client()
    assert api(before_enrollment,'/auth/login',{'email':'owner@example.test','password':pw}).status_code==200
    setup = api(client,'/auth/mfa/setup',{'password':pw}).get_json()
    import pyotp
    assert api(client,'/auth/mfa/confirm',{'code':pyotp.TOTP(setup['secret']).now()}).status_code==200
    assert before_enrollment.get('/api/v1/auth/me').status_code==401
    assert client.get('/api/v1/auth/me').status_code==200


def test_reset_revokes_sessions_and_recovery_code_one_use(app,client,owner):
    assert api(client,'/auth/logout').status_code==200
    assert api(client,'/auth/login',{'email':'owner@example.test','password':owner['password']}).get_json()['error']['code']=='mfa_required'
    assert client.get('/api/v1/auth/me').status_code==401
    recovery = owner['recovery_codes'][0]
    assert api(client,'/auth/login',{'email':'owner@example.test','password':owner['password'],'totp_code':recovery}).status_code==200
    second = app.test_client()
    assert api(second,'/auth/login',{'email':'owner@example.test','password':owner['password'],'totp_code':recovery}).status_code==401
    assert api(client,'/auth/forgot-password',{'email':'owner@example.test'}).status_code==202
    token = mail_token(app,'reset')
    assert api(second,'/auth/reset-password',{'token':token,'password':'Changed-unique-password-85!'}).status_code==200
    assert client.get('/api/v1/auth/me').status_code==401
    assert api(second,'/auth/reset-password',{'token':token,'password':'Another-unique-password-86!'}).status_code==400


def test_generic_email_expiry_and_session_revocation(app,client,owner):
    assert api(client,'/auth/forgot-password',{'email':'unknown@example.test'}).get_json()==api(client,'/auth/forgot-password',{'email':'owner@example.test'}).get_json()
    token = mail_token(app,'reset')
    with app.app_context():
        row = db.session.execute(db.select(AuthToken).where(AuthToken.kind=='reset')).scalar_one()
        row.expires_at = now()-timedelta(seconds=1)
        db.session.commit()
    assert api(client,'/auth/reset-password',{'token':token,'password':'Changed-unique-password-85!'}).status_code==400
    with app.app_context():
        db.session.execute(db.update(AuthSession).values(revoked_at=now()))
        db.session.commit()
    assert client.get('/api/v1/auth/me').status_code==401


def test_invite_existing_identity_no_password_overwrite(app,client,owner):
    other = app.test_client()
    registered = register(app,other,'other@example.test','Other','Other plant',False)
    assert api(client,'/invitations',{'email':'other@example.test','role':'owner'}).status_code==403
    assert api(client,'/invitations',{'email':'other@example.test','role':'technician'}).status_code==201
    token = mail_token(app,'invite')
    preview = other.get('/api/v1/invitations/preview',query_string={'token':token})
    assert preview.status_code==200
    assert preview.get_json()['email']=='other@example.test'
    stranger = app.test_client()
    assert api(stranger,'/invitations/accept',{'token':token,'name':'Hacker','password':'Overwrite-attempt-password-88!'}).status_code==401
    assert api(other,'/invitations/accept',{'token':token,'name':'Ignore','password':'Overwrite-attempt-password-88!'}).status_code==200
    assert api(other,'/invitations/accept',{'token':token}).status_code==400
    with app.app_context():
        user = db.session.execute(db.select(User).where(User.email=='other@example.test')).scalar_one()
        assert user.check_password(registered['password'])
    assert api(other,'/companies/switch',{'company_id':owner['company']['id']}).status_code==200
    assert other.get('/api/v1/auth/me').get_json()['membership']['role']=='technician'
    assert api(other,'/assets',{'code':'P1','name':'Denied'}).status_code==403


def test_parallel_token_consumption(app,client):
    body = {'name':'Owner','email':'owner@example.test','password':'Correct-horse-battery-73!','company_name':'Plant'}
    assert api(client,'/auth/signup',body).status_code==201
    token = mail_token(app,'verify')
    def consume(_):
        return api(app.test_client(),'/auth/verify-email',{'token':token}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(consume,range(2)))==[200,400]


def test_db_rate_limit_and_origin(app,client):
    app.config['AUTH_RATE_LIMIT']=1
    body = {'email':'unknown@example.test'}
    assert api(client,'/auth/forgot-password',body).status_code==202
    assert api(client,'/auth/forgot-password',body).status_code==429
    token = client.get('/api/v1/csrf').get_json()['csrf_token']
    assert client.post('/api/v1/companies/switch',json={'company_id':1},headers={'X-CSRF-Token':token,'Origin':'https://evil.example'}).status_code==403
