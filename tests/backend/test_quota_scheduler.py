from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Event
from unittest.mock import patch
import pytest
from app import db
from app.pilot.models import Document, Job, now
from app.pilot.worker import run_once
from app.pilot.quota import reconcile_staging
from app.pilot.storage import storage
from conftest import api, register, create_asset
from test_documents import upload, pdf
from test_security_remediation import reauth


def test_retained_and_pending_quota_and_attempt_rate(app, client, owner):
    asset = create_asset(client)
    app.config['DOCUMENT_QUOTA_FILES'] = 1
    first = upload(client, asset)
    assert first.status_code == 202
    denied = upload(client, asset)
    assert denied.status_code == 429
    assert denied.get_json()['error']['code'] == 'document_quota_exceeded'
    assert denied.get_json()['error']['fields']['remaining']['files'] == 0
    assert api(client, f"/documents/{first.get_json()['document']['id']}", method='DELETE').status_code == 200
    assert upload(client, asset).status_code == 429  # Soft-delete is not physical erasure.
    app.config['DOCUMENT_QUOTA_FILES'] = 100
    app.config['DOCUMENT_PENDING_LIMIT'] = 1
    assert upload(client, asset).status_code == 202
    assert upload(client, asset).get_json()['error']['fields']['remaining']['pending'] == 0
    app.config['DOCUMENT_UPLOAD_RATE_LIMIT'] = 1
    assert upload(client, asset).get_json()['error']['code'] == 'document_upload_rate_limited'


def test_concurrent_boundary_upload_charged_before_storage(app, client, owner):
    asset = create_asset(client)
    app.config['DOCUMENT_QUOTA_BYTES'] = len(pdf())
    cookie = client.get_cookie('machivital_session').value
    entered, release = Event(), Event()
    original = app.extensions['pilot_storage'].put
    def blocked(key, content):
        entered.set()
        assert release.wait(10)
        original(key, content)
    def submit():
        actor = app.test_client()
        actor.set_cookie('machivital_session', cookie)
        return upload(actor, asset)
    with patch.object(app.extensions['pilot_storage'], 'put', side_effect=blocked):
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(submit)
            assert entered.wait(10)
            try:
                denied = pool.submit(submit).result(timeout=10)
                assert denied.status_code == 429, denied.get_json()
                with app.app_context():
                    row = db.session.execute(db.select(Document)).scalar_one()
                    assert row.status == 'staging'
                    assert db.session.execute(db.select(Job).where(Job.kind=='document')).scalar_one().state == 'staging'
                assert run_once(app, 'document')['processed'] == 0
            finally:
                release.set()
            assert first.result(timeout=10).status_code == 202


def test_failed_storage_and_abandoned_reservation_cleanup(app, client, owner):
    asset = create_asset(client)
    with patch.object(app.extensions['pilot_storage'], 'put', side_effect=OSError('disk full')):
        assert upload(client, asset).status_code == 500
    with app.app_context():
        row = db.session.execute(db.select(Document)).scalar_one()
        assert row.storage_released_at and row.status == 'failed'
    # Simulate a persisted crash after writing only part of its known owned blob.
    with app.app_context():
        row = Document(company_id=owner['company']['id'], asset_id=asset['id'], title='Abandoned', filename='manual.pdf', blob_key='f'*32+'.pdf', size=100, checksum='0'*64, status='staging', staging_token='a'*48, staging_until=now()-timedelta(seconds=1))
        db.session.add(row)
        db.session.flush()
        identity = row.id
        db.session.add(Job(company_id=row.company_id, kind='document', identity=f'document:{row.id}:1', payload={'document_id':row.id,'revision':1}, state='staging'))
        storage().put(row.blob_key, b'%PDF-partial')
        storage().put('e'*32+'.pdf', b'unrelated retained sentinel')
        db.session.commit()
    assert reconcile_staging(app) == {'reconciled':1}
    with app.app_context():
        row = db.session.get(Document, identity)
        assert row.storage_released_at and row.staging_token is None
        assert storage().get('e'*32+'.pdf',100) == b'unrelated retained sentinel'
        with pytest.raises(FileNotFoundError):
            storage().get(row.blob_key,100)


def test_idle_worker_reconciles_expired_upload_and_refunds_capacity(app, client, owner):
    from app.pilot.quota import capacity
    asset = create_asset(client)
    with app.app_context():
        row = Document(company_id=owner['company']['id'], asset_id=asset['id'], title='Crashed upload', filename='manual.pdf', blob_key='d'*32+'.pdf', size=100, checksum='0'*64, status='staging', staging_token='b'*48, staging_until=now()-timedelta(seconds=1))
        db.session.add(row)
        db.session.flush()
        identity = row.id
        db.session.add(Job(company_id=row.company_id, kind='document', identity=f'document:{identity}:1', payload={'document_id':identity,'revision':1}, state='staging'))
        storage().put(row.blob_key, b'%PDF-partial')
        db.session.commit()
        assert capacity(row.company_id)['pending'] == app.config['DOCUMENT_PENDING_LIMIT']-1
    assert run_once(app, 'document')['processed'] == 0
    with app.app_context():
        row = db.session.get(Document, identity)
        assert row.storage_released_at and row.status == 'failed'
        assert capacity(row.company_id) == {'bytes':app.config['DOCUMENT_QUOTA_BYTES'], 'files':app.config['DOCUMENT_QUOTA_FILES'], 'pending':app.config['DOCUMENT_PENDING_LIMIT']}
        with pytest.raises(FileNotFoundError):
            storage().get(row.blob_key, 100)


def test_authority_change_during_storage_never_queues(app, client, owner):
    # Demote a planner while their blob I/O is in flight. Tenant session is revoked.
    from test_security_remediation import invite_member
    actor, identity = invite_member(app, client, role='planner')
    asset = create_asset(client)
    entered, release = Event(), Event()
    original = app.extensions['pilot_storage'].put
    def blocked(key, content):
        entered.set()
        assert release.wait(10)
        original(key, content)
    cookie = actor.get_cookie('machivital_session').value
    def submit():
        isolated = app.test_client()
        isolated.set_cookie('machivital_session',cookie)
        return upload(isolated,asset)
    assert reauth(client,owner).status_code == 200
    with patch.object(app.extensions['pilot_storage'],'put',side_effect=blocked), ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(submit)
        assert entered.wait(10)
        try:
            assert api(client,f"/members/{identity['membership']['id']}",{'role':'viewer','reason':'Access narrowed'},'PATCH').status_code == 200
        finally:
            release.set()
        assert pending.result(timeout=10).status_code == 401
    with app.app_context():
        row = db.session.execute(db.select(Job).where(Job.kind=='document')).scalar_one()
        assert row.state=='cancelled'
        assert db.session.execute(db.select(Document)).scalar_one().storage_released_at


def test_tenant_fairness_mail_lane_and_live_lease_cap(app, client, owner):
    app.config['TEST_SCANNER'] = lambda content: True
    app.config['TEST_PARSER'] = lambda content: ['Safe']
    first = create_asset(client)
    a = upload(client,first).get_json()['document']
    b = upload(client,first).get_json()['document']
    other = app.test_client()
    register(app,other,'other@example.test','Other','Second')
    second = create_asset(other)
    c = upload(other,second).get_json()['document']
    assert run_once(app,'document')['state']=='done'
    with app.app_context():
        assert db.session.get(Document,a['id']).status=='ready'
        assert db.session.get(Document,b['id']).status=='quarantined'
    assert run_once(app,'document')['state']=='done'
    with app.app_context():
        assert db.session.get(Document,c['id']).status=='ready'
        job = db.session.execute(db.select(Job).where(Job.identity==f"document:{b['id']}:1")).scalar_one()
        job.state,job.lease_token,job.lease_until = 'running','still-live',now()+timedelta(minutes=1)
        db.session.commit()
    assert run_once(app,'document')['processed']==0
    assert api(client,'/auth/forgot-password',{'email':'owner@example.test'}).status_code==202
    assert run_once(app,'mail')['state']=='done'
    with app.app_context():
        job = db.session.execute(db.select(Job).where(Job.identity==f"document:{b['id']}:1")).scalar_one()
        job.lease_until = now()-timedelta(seconds=1)
        db.session.commit()
    assert run_once(app,'document')['state']=='done'


def test_default_worker_alternates_ready_kinds_and_stale_fence(app, client, owner):
    asset = create_asset(client)
    upload(client,asset)
    assert api(client,'/auth/forgot-password',{'email':'owner@example.test'}).status_code==202
    app.config['TEST_SCANNER'] = lambda content: True
    app.config['TEST_PARSER'] = lambda content: ['Safe']
    results = [run_once(app),run_once(app)]
    with app.app_context():
        kinds = {db.session.get(Job,r['job_id']).kind for r in results}
        assert kinds == {'mail','document'}
    another = upload(client,asset).get_json()['document']
    def lose_lease(content):
        with app.app_context():
            row = db.session.execute(db.select(Job).where(Job.identity==f"document:{another['id']}:1")).scalar_one()
            row.lease_token = 'new-lease'
            db.session.commit()
        return ['Do not publish']
    app.config['TEST_PARSER'] = lose_lease
    assert run_once(app,'document')['state']=='lease_lost'
    with app.app_context():
        row = db.session.execute(db.select(Job).where(Job.identity==f"document:{another['id']}:1")).scalar_one()
        assert row.state=='running' and row.lease_token=='new-lease'
        assert db.session.get(Document,another['id']).pages is None
