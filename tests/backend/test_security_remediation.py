from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Event
from unittest.mock import patch
import pytest
from sqlalchemy import func, text
from app import db
from app.models import User
from app.pilot.models import Membership, AccessAudit, AuthSession, AuthToken, Job, now
from conftest import api, register, mail_token, create_asset


def reauth(client, owner, index=0):
    return api(client, '/auth/reauth', {'password': owner['password'], 'totp_code': owner['recovery_codes'][index]})


def invite_member(app, client, email='tech@example.test', role='technician'):
    other = app.test_client()
    assert api(client, '/invitations', {'email': email, 'role': role}).status_code == 201
    assert api(other, '/invitations/accept', {'token': mail_token(app, 'invite'), 'name': 'Technician', 'password': 'Technician-safe-password-89!'}).status_code == 200
    assert api(other, '/auth/login', {'email': email, 'password': 'Technician-safe-password-89!'}).status_code == 200
    return other, other.get('/api/v1/auth/me').get_json()


def test_recent_reauthentication_and_last_owner(app, client, owner):
    mid = owner['membership']['id']
    assert api(client, f'/members/{mid}', {'reason': 'Leaving'}, 'DELETE').get_json()['error']['code'] == 'reauthentication_required'
    assert api(client, '/auth/reauth', {'password': 'incorrect', 'totp_code': owner['recovery_codes'][0]}).status_code == 401
    assert reauth(client, owner).status_code == 200
    assert api(client, '/auth/reauth', {'password': owner['password'], 'totp_code': owner['recovery_codes'][0]}).status_code == 401
    result = api(client, f'/members/{mid}', {'reason': 'Leaving'}, 'DELETE')
    assert result.status_code == 409
    assert result.get_json()['error']['code'] == 'last_owner'
    with app.app_context():
        db.session.execute(db.update(AuthSession).values(access_confirmed_at=now()-timedelta(minutes=6)))
        db.session.commit()
    assert api(client, f'/members/{mid}', {'role': 'viewer', 'reason': 'Transfer'}, 'PATCH').get_json()['error']['code'] == 'reauthentication_required'


def test_offboard_preserves_other_tenant_and_history(app, client, owner):
    other = app.test_client()
    second = register(app, other, 'other@example.test', 'Other', 'Other factory', False)
    assert api(client, '/invitations', {'email': 'other@example.test', 'role': 'technician'}).status_code == 201
    assert api(other, '/invitations/accept', {'token': mail_token(app, 'invite')}).status_code == 200
    home_cookie = other.get_cookie('machivital_session').value
    home = app.test_client()
    home.set_cookie('machivital_session', home_cookie)
    # Switching a session is intentionally not cloning it; login gives an independent session.
    assert api(other, '/auth/login', {'email': 'other@example.test', 'password': second['password']}).status_code == 200
    assert api(other, '/companies/switch', {'company_id': owner['company']['id']}).status_code == 200
    mid = other.get('/api/v1/auth/me').get_json()['membership']['id']
    assert reauth(client, owner).status_code == 200
    result = api(client, f'/members/{mid}', {'reason': 'Employment ended'}, 'DELETE')
    assert result.status_code == 200, result.get_json()
    assert other.get('/api/v1/auth/me').status_code == 401
    assert home.get('/api/v1/auth/me').status_code == 200
    assert api(home, '/companies/switch', {'company_id': owner['company']['id']}).status_code == 404
    with app.app_context():
        assert db.session.get(User, second['user']['id']).is_enabled
        assert not db.session.get(Membership, mid).active
        audit = db.session.execute(db.select(AccessAudit)).scalar_one()
        assert audit.action == 'offboard' and audit.reason == 'Employment ended'
        with pytest.raises(Exception, match='append-only'):
            db.session.execute(db.update(AccessAudit).values(reason='erase'))
        db.session.rollback()


def test_invitation_cancel_and_admin_hierarchy(app, client, owner):
    assert api(client, '/invitations', {'email': 'cancel@example.test', 'role': 'viewer'}).status_code == 201
    token = mail_token(app, 'invite')
    invitation = client.get('/api/v1/invitations').get_json()['invitations'][0]
    assert reauth(client, owner).status_code == 200
    assert api(client, f"/invitations/{invitation['id']}", {'reason': 'Wrong address'}, 'DELETE').status_code == 200
    assert api(app.test_client(), '/invitations/accept', {'token': token, 'name': 'No', 'password': 'Technician-safe-password-89!'}).status_code == 400
    admin, identity = invite_member(app, client, 'admin@example.test', 'admin')
    import pyotp
    setup = api(admin, '/auth/mfa/setup', {'password': 'Technician-safe-password-89!'}).get_json()
    confirmed = api(admin, '/auth/mfa/confirm', {'code': pyotp.TOTP(setup['secret']).now()}).get_json()
    assert api(admin, '/auth/reauth', {'password': 'Technician-safe-password-89!', 'totp_code': confirmed['recovery_codes'][0]}).status_code == 200
    assert api(admin, '/invitations', {'email': 'privileged@example.test', 'role': 'admin'}).status_code == 403
    assert api(admin, f"/members/{owner['membership']['id']}", {'role': 'viewer', 'reason': 'Denied'}, 'PATCH').status_code == 403
    assert api(admin, f"/members/{identity['membership']['id']}", {'reason': 'Denied'}, 'DELETE').status_code == 403


def test_parallel_last_owner_changes(app, client, owner):
    other = app.test_client()
    second = register(app, other, 'second@example.test', 'Second', 'Second factory')
    assert api(client, '/invitations', {'email': 'second@example.test', 'role': 'planner'}).status_code == 201
    assert api(other, '/invitations/accept', {'token': mail_token(app, 'invite')}).status_code == 200
    assert api(other, '/companies/switch', {'company_id': owner['company']['id']}).status_code == 200
    mid = other.get('/api/v1/auth/me').get_json()['membership']['id']
    assert reauth(client, owner).status_code == 200
    assert api(client, f'/members/{mid}', {'role': 'owner', 'reason': 'Replacement'}, 'PATCH').status_code == 200
    assert api(other, '/auth/login', {'email':'second@example.test','password':second['password'],'totp_code':second['recovery_codes'][0]}).status_code == 200
    assert api(other, '/companies/switch', {'company_id':owner['company']['id']}).status_code == 200
    assert reauth(other, second, 1).status_code == 200
    actors = [(client.get_cookie('machivital_session').value, owner['membership']['id']), (other.get_cookie('machivital_session').value, mid)]
    def demote(actor):
        independent = app.test_client()
        independent.set_cookie('machivital_session', actor[0])
        return api(independent, f'/members/{actor[1]}', {'role': 'viewer', 'reason': 'Leaving'}, 'PATCH').status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(demote, actors)) == [200, 409]
    with app.app_context():
        assert db.session.scalar(db.select(func.count()).select_from(Membership).where(Membership.company_id == owner['company']['id'], Membership.active.is_(True), Membership.role == 'owner')) == 1


def test_consume_then_resend_guard_contention_no_deadlock(app,client):
    from app.pilot import auth, security
    assert api(client,'/auth/signup',{'name':'Owner','email':'owner@example.test','password':'Correct-horse-battery-73!','company_name':'Factory'}).status_code==201
    token = mail_token(app,'verify')
    entered,attempted,release = Event(),Event(),Event()
    original_token,original_guard = auth.token_row,security.transaction_guard
    def blocked_token(raw,kind,lock=True):
        row = original_token(raw,kind,lock)
        if lock and kind=='verify':
            entered.set()
            assert release.wait(10)
        return row
    def observed_guard(exclusive=False):
        from flask import request
        if request.path.endswith('resend-verification'):
            attempted.set()
        return original_guard(exclusive)
    with patch.object(auth,'token_row',side_effect=blocked_token),patch.object(security,'transaction_guard',side_effect=observed_guard),ThreadPoolExecutor(max_workers=2) as pool:
        consumed = pool.submit(api,app.test_client(),'/auth/verify-email',{'token':token})
        assert entered.wait(10)
        resent = pool.submit(api,app.test_client(),'/auth/resend-verification',{'email':'owner@example.test'})
        try:
            assert attempted.wait(10)
            assert not resent.done()
        finally:
            release.set()
        assert consumed.result(timeout=10).status_code==200
        assert resent.result(timeout=10).status_code==202
    with app.app_context():
        assert db.session.scalar(db.select(func.count()).select_from(AuthToken).where(AuthToken.kind=='verify',AuthToken.consumed_at.is_(None)))==0


def test_cancel_then_accept_serializes_under_guard(app,client,owner):
    from app.pilot import auth,security
    assert api(client,'/invitations',{'email':'new@example.test','role':'viewer'}).status_code==201
    token = mail_token(app,'invite')
    invitation = client.get('/api/v1/invitations').get_json()['invitations'][0]
    assert reauth(client,owner).status_code==200
    entered,attempted,release = Event(),Event(),Event()
    original_invalidate,original_guard = auth.invalidate_tokens,security.transaction_guard
    def blocked(query):
        entered.set()
        assert release.wait(10)
        return original_invalidate(query)
    def observed(exclusive=False):
        from flask import request
        if request.path.endswith('/accept'):
            attempted.set()
        return original_guard(exclusive)
    with patch.object(auth,'invalidate_tokens',side_effect=blocked),patch.object(security,'transaction_guard',side_effect=observed),ThreadPoolExecutor(max_workers=2) as pool:
        cancelled = pool.submit(api,client,f"/invitations/{invitation['id']}",{'reason':'Cancelled'},'DELETE')
        assert entered.wait(10)
        accepted = pool.submit(api,app.test_client(),'/invitations/accept',{'token':token,'name':'New','password':'Technician-safe-password-89!'})
        try:
            assert attempted.wait(10)
            assert not accepted.done()
        finally:
            release.set()
        assert cancelled.result(timeout=10).status_code==200
        assert accepted.result(timeout=10).status_code==400


def test_offboard_waiting_protected_replay_refreshes_authority(app,client,owner):
    from app.pilot import security
    actor,identity = invite_member(app,client,role='planner')
    asset = create_asset(client)
    body = {'asset_id':asset['id'],'title':'Historic job'}
    assert api(actor,'/work-orders',body,key='historic-replay-001').status_code==201
    cookie = actor.get_cookie('machivital_session').value
    queued_actor = app.test_client()
    queued_actor.set_cookie('machivital_session',cookie)
    assert reauth(client,owner).status_code==200
    attempted = Event()
    original = security.transaction_guard
    def observed(exclusive=False):
        from flask import request
        if request.path=='/api/v1/work-orders':
            attempted.set()
        return original(exclusive)
    with app.app_context():
        security.transaction_guard(exclusive=True)
        target = db.session.get(Membership,identity['membership']['id'])
        with patch.object(security,'transaction_guard',side_effect=observed),ThreadPoolExecutor(max_workers=1) as pool:
            response = pool.submit(api,queued_actor,'/work-orders',body,'POST','historic-replay-001')
            try:
                assert attempted.wait(10)
                assert not response.done()
                target.active=False
                db.session.execute(db.update(AuthSession).where(AuthSession.membership_id==target.id).values(revoked_at=now()))
                db.session.commit()
            finally:
                db.session.rollback()
            assert response.result(timeout=10).status_code==401
