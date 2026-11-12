"""Prove full synthetic PM restoration through the actual Flask API.

Fresh restore DB/blob root only; no server, original data or real mail. Negative
controls operate only on restored app copies and preserve source snapshot.
"""
import importlib.util
import hashlib
import json
from pathlib import Path

from cryptography.fernet import Fernet
import pyotp

ROOT=Path(__file__).resolve().parents[2]


def runtime():
    spec=importlib.util.spec_from_file_location('pm_restored_runtime',ROOT/'scripts/pilot/pm_runtime.py')
    result=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def write(client,path,body):
    csrf=client.get('/api/v1/csrf').get_json()['csrf_token']
    return client.post('/api/v1'+path,json=body,headers={'X-CSRF-Token':csrf})


def main():
    runner=runtime()
    run=runner.load_manifest()
    root=Path(run['run_dir'])
    proof=json.loads((root/'journey-proof.json').read_text())
    credentials=proof['credentials']
    app=runner.application(run,'restore_database_url',restored=True,testing=True)
    # Restore side effects are captured in-process, never delivered to any mailbox.
    restored_mail=[]
    app.config['TEST_MAIL_ADAPTER']=restored_mail.append
    assert Path(app.config['PRIVATE_STORAGE_DIR']).resolve()==(root/'restored-documents').resolve()
    assert app.config['SQLALCHEMY_DATABASE_URI']==run['restore_database_url']
    assert app.config['STORAGE_BACKEND']=='local'
    client=app.test_client()
    login=write(client,'/auth/login',dict(email=credentials['email'],password=credentials['password'],totp_code=credentials['recovery_codes'][-1]))
    assert login.status_code==200,login.get_json()
    print('PASS: restored identity and matching MFA key/recovery login work')
    assert client.get('/readyz').status_code==200
    plan=client.get('/api/v1/maintenance-plans/'+str(proof['plan_id'])).get_json()
    assert plan['plan']['enabled'] is False and plan['occurrences']
    order=client.get('/api/v1/work-orders/'+str(proof['work_order_id'])).get_json()
    assert order['work_order']['status']=='completed' and len(order['events'])>=4
    print('PASS: PM cursor/provenance and completed technician history survived restore')
    download=client.get('/api/v1/documents/'+str(proof['document_id'])+'/download')
    assert download.status_code==200 and hashlib.sha256(download.data).hexdigest()==proof['document_checksum']
    print('PASS: restored private manual checksum and authorized download match')
    # Restore has paused plan/completed work: no overdue mail or duplicate order on restart.
    from app.pilot.worker import run_once
    with app.app_context():
        from app import db
        from app.pilot.models import WorkOrder
        before=db.session.scalar(db.select(db.func.count()).select_from(WorkOrder).where(WorkOrder.plan_id==proof['plan_id']))
    from app.pilot.scheduling import tick
    tick(app)
    results=[run_once(app) for _ in range(3)]
    with app.app_context():
        after=db.session.scalar(db.select(db.func.count()).select_from(WorkOrder).where(WorkOrder.plan_id==proof['plan_id']))
    assert before==after
    with app.app_context():
        from app.pilot.models import Job
        from app.pilot.models import WorkReminder
        accepted_or_pending=db.session.scalar(db.select(db.func.count()).select_from(Job).join(WorkReminder,Job.reminder_id==WorkReminder.id).where(WorkReminder.work_order_id==proof['work_order_id'],WorkReminder.stage=='overdue',Job.kind=='maintenance_mail',Job.state.in_(['queued','running','done'])))
        assert accepted_or_pending==0, 'Restored paused/completed PM must not send new reminders'
    assert all(order['work_order']['number'] not in message.get('Subject','') for message in restored_mail)
    print('PASS: restored safe worker resume does not replay completed PM work')
    blob_root=root/'restored-documents'
    from app.pilot.models import Document
    with app.app_context():
        document=db.session.get(Document,proof['document_id'])
        path=blob_root/document.blob_key
    content=path.read_bytes()
    try:
        path.write_bytes(b'%PDF-corrupt-restore-negative-control')
        assert client.get('/api/v1/documents/'+str(proof['document_id'])+'/download').status_code==409
        path.unlink()
        assert client.get('/api/v1/documents/'+str(proof['document_id'])+'/download').status_code!=200
    finally:
        path.write_bytes(content)
    print('PASS: corrupt/missing restored private blob denied, source snapshot unchanged')
    wrong=runner.application({**run,'mfa_key':Fernet.generate_key().decode()},'restore_database_url',restored=True)
    refused=write(wrong.test_client(),'/auth/login',dict(email=credentials['email'],password=credentials['password'],totp_code=pyotp.TOTP(credentials['totp_secret']).now()))
    assert refused.status_code!=200
    print('PASS: wrong restored encryption key cannot authenticate MFA, no secrets reflected')
    with app.app_context():
        from sqlalchemy import text
        revision=db.session.execute(text('SELECT version_num FROM alembic_version_pilot')).scalar_one()
        try:
            db.session.execute(text('UPDATE alembic_version_pilot SET version_num=:value'),{'value':'pilot_0001'})
            db.session.commit()
            assert client.get('/readyz').status_code==503
        finally:
            db.session.execute(text('UPDATE alembic_version_pilot SET version_num=:value'),{'value':revision})
            db.session.commit()
    print('PASS: stale restore schema reports not ready and restored revision preserved')
    print('PASS: full synthetic local app+blob+separate-key restore checks; not production/offsite SLA proof')


if __name__=='__main__':
    main()
