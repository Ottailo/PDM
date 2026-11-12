"""Disposable PostgreSQL fixtures. Never fall back to the legacy or pilot database."""
import os
import re
import secrets
from pathlib import Path
from urllib.parse import urlsplit, parse_qs
import pytest
from cryptography.fernet import Fernet
from sqlalchemy import inspect, text
from flask_migrate import upgrade
from app import create_app, db
from app.pilot.worker import run_once

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope='session')
def database_url():
    url = os.environ.get('PDM_TEST_DATABASE_URL')
    if not url:
        pytest.fail('Supply PDM_TEST_DATABASE_URL for an explicitly disposable PostgreSQL database; skipped tests are not proof')
    name = urlsplit(url).path.lstrip('/')
    if not url.startswith('postgresql+psycopg://') or not re.fullmatch(r'[A-Za-z0-9_]+_test',name):
        pytest.fail('Refusing test database without PostgreSQL URL and _test database name')
    # Fixture cleanup truncates this disposable database. Never let two suites
    # race each other while testing requests with their own concurrent threads.
    import psycopg
    with psycopg.connect(url.replace('postgresql+psycopg://', 'postgresql://'), autocommit=True) as lock:
        acquired = lock.execute('SELECT pg_try_advisory_lock(73119401001)').fetchone()[0]
        if not acquired:
            pytest.fail('Another backend suite owns this disposable database; run suites serially')
        try:
            yield url
        finally:
            lock.execute('SELECT pg_advisory_unlock(73119401001)')


@pytest.fixture
def app(database_url,tmp_path):
    mail = []
    application = create_app({'TESTING':True,'LOAD_PILOT_ENV':False,'APP_ENV':'test','PDF_PARSER_MODE':'development','SQLALCHEMY_DATABASE_URI':database_url,'SECRET_KEY':secrets.token_hex(32),'MFA_ENCRYPTION_KEY':Fernet.generate_key().decode(),'PRIVATE_STORAGE_DIR':str(tmp_path/'blobs'),'APP_BASE_URL':'http://localhost','SESSION_COOKIE_SECURE':False,'AUTH_RATE_LIMIT':500,'TEST_MAIL_ADAPTER':mail.append,'SMTP_STARTTLS':False,'TRUSTED_HOSTS':['localhost']})
    application.extensions['captured_mail'] = mail
    with application.app_context():
        upgrade(directory=str(ROOT/'migrations_pilot'))
        tables = [t for t in inspect(db.engine).get_table_names() if t!='alembic_version_pilot']
        if tables:
            quoted = ', '.join('"'+t.replace('"','""')+'"' for t in tables)
            db.session.execute(text('TRUNCATE TABLE '+quoted+' RESTART IDENTITY CASCADE'))
            db.session.commit()
    yield application
    with application.app_context():
        db.session.remove()
        db.engine.dispose()


@pytest.fixture
def client(app):
    return app.test_client()


def api(client,path,body=None,method='POST',key=None):
    csrf = client.get('/api/v1/csrf').get_json()['csrf_token']
    headers = {'X-CSRF-Token':csrf}
    if key:
        headers['Idempotency-Key'] = key
    return client.open('/api/v1'+path,method=method,json=body if body is not None else {},headers=headers)


def mail_token(app,kind):
    while run_once(app,'mail')['processed']:
        pass
    path = {'verify':'verify-email','reset':'reset-password','invite':'invite'}[kind]
    messages = app.extensions['captured_mail']
    for message in reversed(messages):
        match = re.search(r'https?://[^\s]+/'+path+r'\?token=([^\s]+)',message.get_content())
        if match:
            return match.group(1)
    raise AssertionError('No matching captured mail')


def register(app,client,email='owner@example.test',name='Owner',company='Factory',enroll=True):
    import pyotp
    pw = 'Correct-horse-battery-73!'
    response = api(client,'/auth/signup',{'name':name,'email':email,'password':pw,'company_name':company})
    assert response.status_code==201,response.get_json()
    assert api(client,'/auth/verify-email',{'token':mail_token(app,'verify')}).status_code==200
    login = api(client,'/auth/login',{'email':email,'password':pw})
    assert login.status_code==200,login.get_json()
    result = login.get_json()
    if enroll:
        setup = api(client,'/auth/mfa/setup',{'password':pw})
        assert setup.status_code==200,setup.get_json()
        response = api(client,'/auth/mfa/confirm',{'code':pyotp.TOTP(setup.get_json()['secret']).now()})
        assert response.status_code==200,response.get_json()
        result['recovery_codes'] = response.get_json()['recovery_codes']
    result['password'] = pw
    return result


def create_asset(client,code='PUMP-01',name='Cooling pump'):
    response = api(client,'/assets',{'code':code,'name':name,'manufacturer':'OEM','model':'M1','serial_number':'SN1','criticality':'high'})
    assert response.status_code==201,response.get_json()
    return response.get_json()['asset']


@pytest.fixture
def owner(app,client):
    return register(app,client)
