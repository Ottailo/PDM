"""Exercise Stage 1 through the real local API, SMTP sink and PDF scanner.

Creates explicit synthetic test organizations in the isolated pilot DB. Never
uses production URLs or original data. Writes a private local evidence report.
"""
from datetime import datetime, timezone
from io import BytesIO
import json
from pathlib import Path
import re
import secrets
import time
from urllib.parse import parse_qs, urlsplit

import pyotp
import requests

ROOT = Path(__file__).resolve().parents[2]
BASE = 'http://127.0.0.1:5051/api/v1'
MAIL = 'http://127.0.0.1:8026/api/v1'
STAMP = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')
EVIDENCE = []


def record(name: str, details: str = '') -> None:
    EVIDENCE.append({'test': name, 'result': 'pass', 'details': details})
    print(f'PASS: {name}' + (f' ({details})' if details else ''))


class Client:
    def __init__(self):
        self.session = requests.Session()

    def request(self, method: str, path: str, status: int = 200, **kwargs):
        headers = dict(kwargs.pop('headers', {}))
        if method != 'GET':
            csrf = self.session.get(BASE + '/csrf', timeout=15)
            assert csrf.status_code == 200, csrf.text
            headers['X-CSRF-Token'] = csrf.json()['csrf_token']
        response = self.session.request(method, BASE + path, headers=headers, timeout=30, **kwargs)
        assert response.status_code == status, f'{method} {path}: {response.status_code}: {response.text[:600]}'
        return response

    def post(self, path, data, status=200, **kwargs):
        return self.request('POST', path, status, json=data, **kwargs).json()


def token_from_mail(email: str, action: str) -> str:
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        messages = requests.get(MAIL + '/messages', timeout=10).json().get('messages', [])
        for message in messages:
            recipients = [recipient.get('Address', '').lower() for recipient in message.get('To', [])]
            if email.lower() not in recipients:
                continue
            detail = requests.get(MAIL + '/message/' + message['ID'], timeout=10).json()
            text = (detail.get('Text') or '') + '\n' + (detail.get('HTML') or '')
            for link in re.findall(r'https?://[^\s<>"\']+', text):
                link = link.replace('&amp;', '&').rstrip(').,')
                parsed = urlsplit(link)
                if action in parsed.path:
                    token = parse_qs(parsed.query).get('token', [])
                    if token:
                        return token[0]
        time.sleep(0.25)
    raise AssertionError(f'No actual captured {action} email for synthetic account')


def signup(client: Client, label: str) -> dict:
    email = f'pilot-{label}-{STAMP}@example.test'
    password = 'Pilot-test-' + secrets.token_urlsafe(18) + '-42!'
    result = client.post('/auth/signup', {'name': f'Test {label}', 'email': email, 'password': password, 'company_name': f'Test factory {label} {STAMP}'}, 201)
    record(f'{label}: signup accepted, pending verification')
    assert 'token' not in result, 'Verification token leaked in signup response'
    client.post('/auth/login', {'email': email, 'password': password}, 403)
    token = token_from_mail(email, 'verify-email')
    client.post('/auth/verify-email', {'token': token})
    record(f'{label}: captured SMTP verification link consumed')
    replay = client.session.post(BASE + '/auth/verify-email', json={'token': token}, headers={'X-CSRF-Token': client.session.get(BASE + '/csrf', timeout=10).json()['csrf_token']}, timeout=15)
    assert replay.status_code in (400, 409, 410), replay.text
    record(f'{label}: verification replay rejected')
    login = client.post('/auth/login', {'email': email, 'password': password})
    assert login.get('mfa_enrollment_required'), 'Owner MFA enrollment not required'
    setup = client.post('/auth/mfa/setup', {'password': password})
    secret = setup['secret']
    confirmed = client.post('/auth/mfa/confirm', {'code': pyotp.TOTP(secret).now()})
    assert confirmed.get('recovery_codes'), 'Missing one-time recovery codes'
    record(f'{label}: owner MFA enrolled')
    return {'email': email, 'password': password, 'totp_secret': secret, 'recovery_codes': confirmed['recovery_codes']}


def main():
    owner = Client()
    credentials = signup(owner, 'owner')
    csrf_denied = requests.post(BASE + '/auth/login', json={'email': credentials['email'], 'password': credentials['password']}, timeout=10)
    assert csrf_denied.status_code == 403, csrf_denied.text
    record('CSRF rejects unauthenticated mutation without token')
    location = owner.post('/locations', {'name': 'Test maintenance bay', 'type': 'Site'}, 201)['location']
    asset = owner.post('/assets', {'code': 'TEST-PUMP-01', 'name': 'Synthetic pilot test pump', 'manufacturer': 'Test only', 'model': 'Fixture', 'serial_number': STAMP, 'criticality': 'high', 'location_id': location['id'], 'description': 'Synthetic software test asset; no physical equipment connected'}, 201)['asset']
    assert asset['telemetry_status'] == 'not_connected'
    record('General machine persists without template or sensors')
    reload = owner.request('GET', f"/assets/{asset['id']}").json()['asset']
    assert reload['name'] == asset['name'] and reload['serial_number'] == STAMP
    record('Machine metadata reload matches saved values')

    other = Client()
    signup(other, 'foreign')
    other_asset = other.post('/assets', {'code': 'TEST-PUMP-01', 'name': 'Other private test pump'}, 201)['asset']
    assert other_asset['id'] != asset['id']
    for path in [f"/assets/{asset['id']}"]:
        response = other.session.get(BASE + path, timeout=10)
        assert response.status_code in (403, 404), response.text
    record('Duplicate machine code isolated and foreign detail denied')
    foreign_location = other.post('/assets', {'code': 'FOREIGN-REF', 'name': 'Invalid location reference', 'location_id': location['id']}, 404)
    assert foreign_location.get('error')
    record('Foreign location relation rejected')

    email = f'pilot-technician-{STAMP}@example.test'
    owner.post('/invitations', {'email': email, 'role': 'technician'}, 201)
    invite = token_from_mail(email, 'invite')
    technician = Client()
    password = 'Technician-test-' + secrets.token_urlsafe(18) + '-42!'
    technician.post('/invitations/accept', {'token': invite, 'name': 'Synthetic technician', 'password': password})
    technician.post('/auth/login', {'email': email, 'password': password})
    members = owner.request('GET', '/members').json()['members']
    member = next(item for item in members if item['email'] == email)
    record('Real captured invitation creates tenant technician membership')

    key = secrets.token_hex(16)
    payload = {'asset_id': asset['id'], 'title': 'Synthetic maintenance journey', 'description': 'Software verification, not engineering instruction', 'priority': 'high', 'assignee_id': member['id'], 'checklist': [{'text': 'Record test completion evidence'}]}
    order = owner.post('/work-orders', payload, 201, headers={'Idempotency-Key': key})['work_order']
    replay = owner.post('/work-orders', payload, 201, headers={'Idempotency-Key': key})['work_order']
    assert replay['id'] == order['id']
    record('Maintenance retry creates exactly one persisted order')
    changed = dict(payload, title='Changed identity payload')
    owner.post('/work-orders', changed, 409, headers={'Idempotency-Key': key})
    record('Idempotency identity cannot be reused for different request')
    foreign = other.session.get(BASE + f"/work-orders/{order['id']}", timeout=10)
    assert foreign.status_code in (403, 404), foreign.text
    record('Foreign work-order read denied')

    def transition(actor, action, notes='', checklist=None, expected=200):
        nonlocal order
        data = {'revision': order['revision'], 'action': action, 'notes': notes}
        if checklist is not None:
            data['checklist'] = checklist
        result = actor.post(f"/work-orders/{order['id']}/transition", data, expected, headers={'Idempotency-Key': secrets.token_hex(16)})
        if expected == 200:
            order = result['work_order']
        return result

    transition(technician, 'start')
    transition(technician, 'block', 'Synthetic missing-information condition')
    transition(technician, 'resume')
    transition(technician, 'submit', 'Synthetic software evidence', [{'text': 'Record test completion evidence', 'completed': True}])
    assert order['status'] == 'awaiting_review'
    transition(technician, 'approve', 'Unauthorized self approval', expected=403)
    record('Technician submits real persisted evidence but cannot approve')
    transition(owner, 'approve', 'Reviewed synthetic test completion')
    assert order['status'] == 'completed'
    detail = owner.request('GET', f"/work-orders/{order['id']}").json()
    assert len(detail['events']) >= 6
    export = owner.request('GET', f"/work-orders/{order['id']}/export")
    assert 'Synthetic' in export.text
    record('Reviewed completion and append-only history/export persist')

    fixture = ROOT / '.pilot' / 'fixtures' / 'manual-test-only.pdf'
    with fixture.open('rb') as stream:
        document = owner.request('POST', '/documents', 202, files={'file': ('manual-test-only.pdf', stream, 'application/pdf')}, data={'asset_id': asset['id'], 'title': 'Synthetic document fixture'}) .json()['document']
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        document = owner.request('GET', f"/documents/{document['id']}").json()['document']
        if document['status'] in ('ready', 'failed', 'blocked'):
            break
        time.sleep(0.3)
    assert document['status'] == 'ready', document
    page = owner.request('GET', f"/documents/{document['id']}/pages/1").json()
    assert 'TEST-ONLY-42' in page['text']
    downloaded = owner.request('GET', f"/documents/{document['id']}/download")
    assert downloaded.content.startswith(b'%PDF-')
    denied = other.session.get(BASE + f"/documents/{document['id']}/download", timeout=10)
    assert denied.status_code in (403, 404)
    record('Actual quarantined PDF scans/parses, page marker reads and private download denied cross-tenant')

    for path in ['/api/latest-states', '/api/history', '/api/request-maintenance', '/api/ingest', '/auth/setup-admin']:
        response = requests.get('http://127.0.0.1:5051' + path, timeout=10)
        assert response.status_code in (404, 405, 410), f'Legacy path accessible: {path} {response.status_code}'
    record('Legacy simulator/admin/ingest routes not exposed in customer app')
    owner.post('/auth/logout', {})
    owner.request('GET', '/auth/me', 401)
    record('Logout revokes server session')

    report = {'created_at': datetime.now(timezone.utc).isoformat(), 'scope': 'Synthetic isolated local integration only; no field equipment', 'tests': EVIDENCE, 'browser_account': credentials, 'asset_id': asset['id'], 'work_order_id': order['id'], 'document_id': document['id']}
    output = ROOT / '.pilot' / 'api-proof.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(f'PASS: {len(EVIDENCE)} real local API assertions; private report in .pilot/api-proof.json')
    print('No physical machine, prediction accuracy, production deployment or customer use verified')


if __name__ == '__main__':
    main()
