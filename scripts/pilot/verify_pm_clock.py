"""Harness-only controlled-clock PM escalation proof on the isolated app DB.

No clock-control API is exposed. Worker stopped first. Mail goes only to explicit
isolated loopback Mailpit; all records are synthetic test identities.
"""
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import secrets

ROOT=Path(__file__).resolve().parents[2]


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    result=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def write(client,path,body):
    token=client.get('/api/v1/csrf').get_json()['csrf_token']
    result=client.post('/api/v1'+path,json=body,headers={'X-CSRF-Token':token,'Idempotency-Key':secrets.token_hex(16)})
    assert result.status_code in {200,201},(path,result.status_code,result.get_json())
    return result.get_json()


def main():
    runtime=load('pm_clock_runtime','scripts/pilot/pm_runtime.py')
    value=runtime.load_manifest()
    proof=json.loads((Path(value['run_dir'])/'journey-proof.json').read_text())
    creds=proof['credentials']
    clock=[datetime.now(timezone.utc)]
    app=runtime.application(value,testing=True,clock=lambda:clock[0])
    client=app.test_client()
    write(client,'/auth/login',{'email':creds['email'],'password':creds['password'],'totp_code':creds['recovery_codes'][-2]})
    identity=client.get('/api/v1/auth/me').get_json()
    local=(clock[0]+timedelta(minutes=5)).astimezone(__import__('zoneinfo').ZoneInfo('Africa/Lagos')).strftime('%Y-%m-%dT%H:%M')
    plan=write(client,'/maintenance-plans',dict(asset_id=proof['asset_id'],title='Synthetic controlled-clock PM reminder',assignee_id=identity['membership']['id'],escalation_member_id=identity['membership']['id'],timezone='Africa/Lagos',start_local=local,interval_unit='day',interval_count=7,reminder_hours=24,checklist=[]))['plan']
    from app.pilot.worker import run_once
    from app.pilot.scheduling import tick
    tick(app)
    for _ in range(15): run_once(app)
    detail=client.get('/api/v1/maintenance-plans/'+str(plan['id'])).get_json()
    assert len(detail['occurrences'])==1
    assert any(row['stage']=='due' and row['state']=='accepted' for row in detail['reminders'])
    clock[0]+=timedelta(hours=26)
    tick(app)
    for _ in range(15): run_once(app)
    # Session expiration is real: authenticate with a fresh unused recovery code.
    write(client,'/auth/login',{'email':creds['email'],'password':creds['password'],'totp_code':creds['recovery_codes'][-3]})
    detail=client.get('/api/v1/maintenance-plans/'+str(plan['id'])).get_json()
    assert len(detail['occurrences'])==1, 'An unfinished occurrence must not flood duplicate work'
    assert any(row['stage']=='overdue' and row['state']=='accepted' for row in detail['reminders'])
    print('PASS: real isolated SMTP due+overdue stages with harness-only clock; one unfinished work order')
    work=client.get('/api/v1/work-orders/'+str(detail['occurrences'][0]['work_order_id'])).get_json()['work_order']
    write(client,'/work-orders/'+str(work['id'])+'/transition',{'revision':work['revision'],'action':'cancel','notes':'Synthetic clock test finished'})
    detail=client.get('/api/v1/maintenance-plans/'+str(plan['id'])).get_json()
    write(client,'/maintenance-plans/'+str(plan['id'])+'/pause',{'revision':detail['plan']['revision'],'reason':'Stop test clock plan'})
    print('PASS: controlled-clock plan stopped without modifying original pilot or real equipment')


if __name__=='__main__':
    main()
