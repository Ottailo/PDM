from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
import pytest
from sqlalchemy import inspect,text
from flask_migrate import downgrade,upgrade
from app import create_app,db
from app.pilot.models import Job,now
from app.pilot.worker import run_once
from conftest import api,mail_token,ROOT


def test_factory_fails_closed(app):
    config = {k:app.config[k] for k in ['SECRET_KEY','MFA_ENCRYPTION_KEY','APP_BASE_URL','PRIVATE_STORAGE_DIR','SQLALCHEMY_DATABASE_URI']}
    config.update(TESTING=True,APP_ENV='test')
    with pytest.raises(RuntimeError,match='PostgreSQL'):
        create_app({**config,'SQLALCHEMY_DATABASE_URI':'sqlite:///instance/maintenance.db'})
    with pytest.raises(RuntimeError,match='SECRET_KEY'):
        create_app({**config,'SECRET_KEY':''})
    with pytest.raises(RuntimeError,match='HTTPS'):
        create_app({**config,'APP_ENV':'production','SESSION_COOKIE_SECURE':False})
    with pytest.raises(RuntimeError,match='Test boundary'):
        create_app({**config,'TESTING':False,'APP_ENV':'development','TEST_SCANNER':lambda c:True})


def test_worker_mail_retry_abandoned_lease_and_concurrent_claim(app,client):
    assert api(client,'/auth/signup',{'name':'Owner','email':'owner@example.test','password':'Correct-horse-battery-73!','company_name':'Plant'}).status_code==201
    def failure(message):
        raise ConnectionError('SMTP unavailable')
    app.config['TEST_MAIL_ADAPTER']=failure
    assert run_once(app)['state']=='queued'
    with app.app_context():
        job = db.session.execute(db.select(Job)).scalar_one()
        assert job.attempts==1 and job.error=='SMTP unavailable'
        job.state='running'
        job.lease_until=now()-timedelta(seconds=1)
        db.session.commit()
    app.config['TEST_MAIL_ADAPTER']=app.extensions['captured_mail'].append
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _:run_once(app),range(2)))
    assert sum(r['processed'] for r in results)==1
    assert len(app.extensions['captured_mail'])==1
    with app.app_context():
        job = db.session.execute(db.select(Job)).scalar_one()
        assert job.state=='done' and job.payload=={} and job.lease_token is None


def test_empty_database_migration_roundtrip(app,client):
    with app.app_context():
        db.session.remove()
        downgrade(directory=str(ROOT/'migrations_pilot'),revision='base')
        assert inspect(db.engine).get_table_names()==['alembic_version_pilot']
        upgrade(directory=str(ROOT/'migrations_pilot'))
        assert {'companies','users','assets','memberships','documents','work_orders','pilot_jobs'}<=set(inspect(db.engine).get_table_names())
    assert client.get('/readyz').status_code==200


def test_legacy_all_methods_and_unknown_logout(app,client,owner):
    for method in ['POST','PATCH','DELETE','PUT']:
        assert client.open('/api/ingest',method=method,json={}).status_code==410
        assert client.open('/auth/setup-admin',method=method,json={}).status_code==410
    assert api(client,'/auth/logout',{'user_id':999}).status_code==400
    assert client.get('/api/v1/auth/me').status_code==200


def test_frozen_upgrade_job_provenance_and_downgrade_evidence(app,client,owner):
    from conftest import create_asset
    from test_documents import upload
    from app.pilot.models import Document,AuthToken,AccessAudit
    from test_security_remediation import reauth
    asset = create_asset(client)
    document = upload(client,asset).get_json()['document']
    with app.app_context():
        job = db.session.execute(db.select(Job).where(Job.kind=='document')).scalar_one()
        job.state='done'
        db.session.commit()
        db.session.remove()
        downgrade(directory=str(ROOT/'migrations_pilot'),revision='pilot_0001')
        db.session.remove()
        # Insert a copied frozen-schema outbox fixture with an invalid document link.
        db.session.execute(text("""INSERT INTO pilot_jobs(kind,identity,payload,state,attempts,available_at,created_at)
            VALUES ('document','document:99999:1',json_build_object('document_id',99999,'revision',1),'queued',0,NOW(),NOW())"""))
        db.session.commit()
        upgrade(directory=str(ROOT/'migrations_pilot'))
        db.session.remove()
        original = db.session.execute(db.select(Job).where(Job.identity==f"document:{document['id']}:1")).scalar_one()
        assert original.company_id==owner['company']['id']
        mail = db.session.execute(db.select(Job).where(Job.kind=='mail')).scalar_one()
        assert mail.token_id is not None and mail.company_id is None
        invalid = db.session.execute(db.select(Job).where(Job.identity=='document:99999:1')).scalar_one()
        assert invalid.state=='quarantined' and invalid.payload=={} and invalid.company_id is None
        db.session.remove()
        with pytest.raises(SystemExit) as refusal:
            downgrade(directory=str(ROOT/'migrations_pilot'),revision='pilot_0001')
        assert refusal.value.code==1
        db.session.rollback()
        invalid = db.session.execute(db.select(Job).where(Job.identity=='document:99999:1')).scalar_one()
        invalid.state='cancelled'
        db.session.commit()
    assert reauth(client,owner).status_code==200
    assert api(client,'/invitations',{'email':'cancel@example.test','role':'viewer'}).status_code==201
    invitation = client.get('/api/v1/invitations').get_json()['invitations'][0]
    assert api(client,f"/invitations/{invitation['id']}",{'reason':'Audit evidence'},'DELETE').status_code==200
    with app.app_context():
        assert db.session.execute(db.select(AccessAudit)).scalar_one().reason=='Audit evidence'
        db.session.remove()
        with pytest.raises(SystemExit) as refusal:
            downgrade(directory=str(ROOT/'migrations_pilot'),revision='pilot_0001')
        assert refusal.value.code==1
        db.session.rollback()


def test_upload_and_parser_configuration_validation(app):
    config = {k:app.config[k] for k in ['SECRET_KEY','MFA_ENCRYPTION_KEY','APP_BASE_URL','PRIVATE_STORAGE_DIR','SQLALCHEMY_DATABASE_URI']}
    config.update(TESTING=True,APP_ENV='test',PDF_PARSER_MODE='development')
    for key in ('DOCUMENT_QUOTA_BYTES','DOCUMENT_QUOTA_FILES','DOCUMENT_PENDING_LIMIT','DOCUMENT_UPLOAD_RATE_LIMIT'):
        with pytest.raises(RuntimeError,match=key):
            create_app({**config,key:0})
    with pytest.raises(RuntimeError,match='immutable'):
        create_app({**config,'PDF_PARSER_IMAGE':'python:latest'})
    with pytest.raises(RuntimeError,match='fixed absolute'):
        create_app({**config,'PDF_DOCKER_EXECUTABLE':'docker --privileged'})
    production = {**config,'APP_ENV':'production','APP_BASE_URL':'https://factory.example.test','SESSION_COOKIE_SECURE':True,'SMTP_STARTTLS':True}
    with pytest.raises(RuntimeError,match='forbids'):
        create_app(production)
    with pytest.raises(RuntimeError,match='approved restricted'):
        create_app({**production,'PDF_PARSER_MODE':'docker','PDF_PARSER_IMAGE':'sha256:'+'a'*64})
