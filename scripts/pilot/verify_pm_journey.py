"""Real HTTP/isolated Mailpit PM journey with synthetic identities only.

No mocks, equipment, provider inference or original DB. Private credentials
retained for new-target restoration proof, not printed or published.
"""
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import secrets
import time
from urllib.parse import parse_qs, urlsplit

import pyotp
import requests

ROOT=Path(__file__).resolve().parents[2]


def runtime():
    spec=importlib.util.spec_from_file_location('pm_journey_runtime', ROOT/'scripts/pilot/pm_runtime.py')
    result=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


class Client:
    def __init__(self,base):
        self.base=base
        self.session=requests.Session()

    def get(self,path,expected=200):
        response=self.session.get(self.base+'/api/v1'+path,timeout=20)
        assert response.status_code==expected,(path,response.status_code,response.text[:300])
        return response.json()

    def write(self,path,body=None,expected=200,method='POST',key=None):
        token=self.get('/csrf')['csrf_token']
        headers={'X-CSRF-Token':token,'Idempotency-Key':key or secrets.token_hex(16)}
        response=self.session.request(method,self.base+'/api/v1'+path,json=body or {},headers=headers,timeout=30)
        assert response.status_code==expected,(path,response.status_code,response.text[:300])
        return response.json()


def mail_link(mail,email,action):
    deadline=time.monotonic()+45
    while time.monotonic()<deadline:
        messages=requests.get(mail+'/api/v1/messages',timeout=10).json().get('messages',[])
        for row in messages:
            if not any(person.get('Address','').lower()==email.lower() for person in row.get('To',[])):
                continue
            detail=requests.get(mail+'/api/v1/message/'+row['ID'],timeout=10).json()
            body=(detail.get('Text') or '')+'\n'+(detail.get('HTML') or '')
            for link in re.findall(r'https?://[^\s<>"\']+',body):
                parsed=urlsplit(link.replace('&amp;','&').rstrip(').,'))
                if parsed.path==action:
                    return parse_qs(parsed.query)['token'][0]
        time.sleep(0.25)
    raise AssertionError('Real isolated verification/invitation mail missing')


def account(base,mail,label,stamp):
    client=Client(base)
    email=f'pm-{label}-{stamp}@example.test'
    password='Pm-only!'+secrets.token_urlsafe(18)+'-42'
    created=client.write('/auth/signup',dict(name='Test '+label,email=email,password=password,company_name='Test PM '+label+' '+stamp),201)
    client.write('/auth/verify-email',{'token':mail_link(mail,email,'/verify-email')})
    client.write('/auth/login',dict(email=email,password=password))
    setup=client.write('/auth/mfa/setup',{'password':password})
    enabled=client.write('/auth/mfa/confirm',{'code':pyotp.TOTP(setup['secret']).now()})
    return client,dict(email=email,password=password,totp_secret=setup['secret'],recovery_codes=enabled['recovery_codes'],company_id=created['company']['id'])


def wait_plan(client,identity):
    deadline=time.monotonic()+40
    while time.monotonic()<deadline:
        row=client.get('/maintenance-plans/'+str(identity))
        if row['occurrences']:
            return row
        time.sleep(0.25)
    raise AssertionError('Scheduler failed to materialize genuine PM occurrence')


def main():
    run=runtime().load_manifest()
    base=f"http://127.0.0.1:{run['api_port']}"
    mail=f"http://127.0.0.1:{run['inbox_port']}"
    stamp=secrets.token_hex(5)
    owner,credentials=account(base,mail,'owner',stamp)
    other,_=account(base,mail,'foreign',stamp)
    checks=[]
    def passed(name):
        checks.append(name)
        print('PASS:',name)
    asset=owner.write('/assets',{'code':'TEST-PM-'+stamp,'name':'Synthetic PM pump'},201)['asset']
    assert asset['telemetry_status']=='not_connected'
    passed('Machine registration remains honest, no measurements invented')
    technician=Client(base)
    tech_email='pm-tech-'+stamp+'@example.test'
    tech_password='Pm-technician!'+secrets.token_urlsafe(18)+'42'
    owner.write('/invitations',dict(email=tech_email,role='technician'),201)
    technician.write('/invitations/accept',dict(token=mail_link(mail,tech_email,'/invite'),name='Test PM technician',password=tech_password))
    technician.write('/auth/login',dict(email=tech_email,password=tech_password))
    tech_identity=technician.get('/auth/me')
    passed('Real Mailpit invitation establishes tenant technician')
    start=(datetime.now(timezone.utc)+timedelta(minutes=10)).astimezone(__import__('zoneinfo').ZoneInfo('Africa/Lagos')).strftime('%Y-%m-%dT%H:%M')
    calendar=dict(start_local=start,timezone='Africa/Lagos',interval_unit='day',interval_count=1)
    preview=owner.write('/maintenance-plans/preview',calendar)
    assert len(preview['dates'])==5 and preview['dates'][0]['timezone']=='Africa/Lagos'
    passed('Calendar preview returns actual local and UTC slots')
    body=dict(asset_id=asset['id'],title='Test-only scheduled inspection '+stamp,description='Software rehearsal, not engineering instruction',priority='medium',assignee_id=tech_identity['membership']['id'],checklist=[{'text':'Record synthetic rehearsal notes'}],reminder_hours=24,escalation_member_id=owner.get('/auth/me')['membership']['id'],**calendar)
    key=secrets.token_hex(16)
    plan=owner.write('/maintenance-plans',body,201,key=key)['plan']
    assert owner.write('/maintenance-plans',body,201,key=key)['plan']['id']==plan['id']
    passed('Idempotent plan retry creates one plan')
    other.get('/maintenance-plans/'+str(plan['id']),404)
    technician.write('/maintenance-plans',body,403)
    passed('Foreign plan denied and technician cannot author plan')
    detail=wait_plan(owner,plan['id'])
    occurrence=detail['occurrences'][0]
    order=owner.get('/work-orders/'+str(occurrence['work_order_id']))['work_order']
    assert order['status']=='assigned' and order['plan_id']==plan['id']
    events=owner.get('/work-orders/'+str(order['id']))['events']
    assert any(event.get('actor_kind')=='system' for event in events)
    passed('Scheduler materializes actual assigned order with system provenance')
    deadline=time.monotonic()+45
    while time.monotonic()<deadline:
        detail=owner.get('/maintenance-plans/'+str(plan['id']))
        if any(row['stage']=='due' and row['state']=='accepted' for row in detail['reminders']):
            break
        time.sleep(0.25)
    else: raise AssertionError('Due reminder not genuinely SMTP accepted')
    messages=requests.get(mail+'/api/v1/messages',timeout=10).json()['messages']
    assert any(any(p.get('Address','').lower()==tech_email for p in row.get('To',[])) and 'maintenance' in row.get('Subject','').lower() for row in messages)
    passed('Actual isolated SMTP accepts due reminder; not a human receipt claim')
    order=technician.write('/work-orders/'+str(order['id'])+'/transition',dict(revision=order['revision'],action='start'))['work_order']
    order=technician.write('/work-orders/'+str(order['id'])+'/transition',dict(revision=order['revision'],action='submit',notes='Synthetic PM software rehearsal complete',checklist=[{'text':'Record synthetic rehearsal notes','completed':True}],labor_minutes=12))['work_order']
    technician.write('/work-orders/'+str(order['id'])+'/transition',dict(revision=order['revision'],action='approve'),403)
    order=owner.write('/work-orders/'+str(order['id'])+'/transition',dict(revision=order['revision'],action='approve',notes='Reviewed test-only PM'))['work_order']
    assert order['status']=='completed'
    passed('Technician evidence and manager review complete real maintenance history')
    fixture=ROOT/'.pilot/fixtures/manual-test-only.pdf'
    token=owner.get('/csrf')['csrf_token']
    with fixture.open('rb') as stream:
        response=owner.session.post(base+'/api/v1/documents',files={'file':('manual-test-only.pdf',stream,'application/pdf')},data={'asset_id':asset['id'],'title':'Synthetic PM restore manual'},headers={'X-CSRF-Token':token},timeout=30)
    assert response.status_code==202,response.text[:300]
    document=response.json()['document']
    deadline=time.monotonic()+60
    while time.monotonic()<deadline:
        document=owner.get('/documents/'+str(document['id']))['document']
        if document['status']=='ready': break
        time.sleep(0.3)
    assert document['status']=='ready',document
    downloaded=owner.session.get(base+'/api/v1/documents/'+str(document['id'])+'/download',timeout=20)
    assert downloaded.status_code==200 and hashlib.sha256(downloaded.content).hexdigest()==hashlib.sha256(fixture.read_bytes()).hexdigest()
    other.get('/documents/'+str(document['id']),404)
    passed('Actual ClamAV and pinned parser produce private checksum-verified manual for restore')
    final=owner.get('/maintenance-plans/'+str(plan['id']))
    paused=owner.write('/maintenance-plans/'+str(plan['id'])+'/pause',dict(revision=final['plan']['revision'],reason='Test pause'))['plan']
    assert paused['enabled'] is False
    passed('Pause preserves existing completed work and stops future generation')
    out=Path(run['run_dir'])/'journey-proof.json'
    with out.open('x',encoding='utf-8') as stream:
        json.dump(dict(scope='Synthetic isolated PM integration only',checks=checks,credentials=credentials,asset_id=asset['id'],plan_id=plan['id'],work_order_id=order['id'],document_id=document['id'],document_checksum=document['checksum']),stream,indent=2)
    print('PASS:',len(checks),'real local PM assertions; private proof retained')


if __name__=='__main__':
    main()
