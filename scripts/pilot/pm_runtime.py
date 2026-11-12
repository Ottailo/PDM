"""Explicit disposable local PM rehearsal; no original configuration inheritance.

Prepare once, migrate explicitly, then launch API via preview tools only. Fresh
local keys and isolated mail are required; no production hosting or automatic pulls.
"""
import argparse
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import socket
import subprocess
import sys
from urllib.parse import urlsplit, urlunsplit

from cryptography.fernet import Fernet
from dotenv import dotenv_values
import psycopg
from psycopg import sql

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / '.pilot' / 'pm-run.json'
PARSER_IMAGE = 'sha256:94eb11fac2a171ce59582f4f74aa039f496531b5621861786323cabb45fe9316'
MAIL_IMAGE = 'sha256:aef2aacc11f075ec0fb6874275ee4a421e688e11a96ebb296134d1735c7761ce'
CLEAN_KEYS = ('SECRET_KEY', 'DATABASE_URL', 'MFA_ENCRYPTION_KEY', 'PRIVATE_STORAGE_DIR', 'STORAGE_BACKEND', 'S3_BUCKET', 'S3_ENDPOINT_URL', 'S3_REGION', 'AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_SESSION_TOKEN', 'SMTP_HOST', 'SMTP_PORT', 'SMTP_FROM', 'SMTP_USERNAME', 'SMTP_PASSWORD', 'SMTP_STARTTLS', 'APP_BASE_URL', 'APP_ENV', 'PDF_PARSER_MODE', 'PDF_PARSER_IMAGE', 'PDF_DOCKER_EXECUTABLE', 'PDF_RESTRICTED_RUNTIME_APPROVED', 'PILOT_PORT')


def private_path(path):
    path = Path(path).resolve()
    if ROOT / '.pilot' not in path.parents:
        raise ValueError('Runtime files must live in ignored .pilot storage')
    return path


def command(args, **kwargs):
    allowed = {'SYSTEMROOT','WINDIR','PATH','HOME','USERPROFILE','LANG','TEMP','TMP','COMSPEC','PATHEXT','LOCALAPPDATA','APPDATA'}
    safe_env = {key:value for key,value in os.environ.items() if key.upper() in allowed}
    result = subprocess.run(args, capture_output=True, timeout=60, env=safe_env, **kwargs)
    if result.returncode:
        evidence = ROOT/'.pilot'/'pm-command-errors'
        evidence.mkdir(parents=True,exist_ok=True)
        with (evidence/(secrets.token_hex(8)+'.log')).open('xb') as stream:
            stream.write(result.stdout+b'\n'+result.stderr)
        raise RuntimeError('Local runtime command failed; private raw error preserved before retrying')
    return result.stdout.decode().strip()


def validate_manifest(value):
    namespace = value.get('namespace', '')
    if not re.fullmatch(r'machivital_pm_[a-f0-9]{12}', namespace):
        raise ValueError('Invalid disposable namespace')
    for kind, suffix in [('database_url', ''), ('test_database_url', '_test'), ('restore_database_url', '_restore')]:
        parsed = urlsplit(value[kind])
        if parsed.scheme != 'postgresql+psycopg' or parsed.hostname not in {'localhost', '127.0.0.1'} or parsed.port != 55432 or parsed.path != '/' + namespace + suffix or parsed.query or parsed.fragment:
            raise ValueError('Refusing unsafe database target')
    for name in ('secret_key', 'mfa_key'):
        if not isinstance(value.get(name), str) or len(value[name]) < 32:
            raise ValueError('Missing fresh local keys')
    Fernet(value['mfa_key'].encode())
    root = private_path(value['run_dir'])
    if root.name != namespace:
        raise ValueError('Invalid run root')
    for name in ('api_port', 'web_port', 'smtp_port', 'inbox_port'):
        if type(value.get(name)) is not int or not 1024 <= value[name] <= 65535:
            raise ValueError('Invalid loopback port')
    if len({value[name] for name in ('api_port', 'web_port', 'smtp_port', 'inbox_port')}) != 4:
        raise ValueError('Ports must be distinct')
    if value['parser_image'] != PARSER_IMAGE or value['mail_image'] != MAIL_IMAGE:
        raise ValueError('Unapproved local image')
    if value['mail_container'] != namespace + '-mail':
        raise ValueError('Invalid isolated mail container')
    return value


def load_manifest(path=MANIFEST):
    value=json.loads(private_path(path).read_text(encoding='utf-8'))
    if value.get('preparation_state','prepared') != 'prepared':
        raise ValueError('Partial preparation preserved; inspect owned artifacts before continuing')
    return validate_manifest(value)


def environment(value, database='database_url', restored=False):
    validate_manifest(value)
    allowed = {'SYSTEMROOT', 'WINDIR', 'PATH', 'HOME', 'USERPROFILE', 'LANG', 'TEMP', 'TMP', 'COMSPEC', 'PATHEXT', 'LOCALAPPDATA', 'APPDATA', 'PROGRAMFILES', 'PROGRAMFILES(X86)', 'PROGRAMW6432'}
    env = {key: val for key, val in os.environ.items() if key.upper() in allowed}
    executable = shutil.which('docker')
    if not executable:
        raise RuntimeError('Existing Docker executable required; no install attempted')
    root = private_path(value['run_dir'])
    env.update(APP_ENV='development', DATABASE_URL=value[database], SECRET_KEY=value['secret_key'], MFA_ENCRYPTION_KEY=value['mfa_key'], STORAGE_BACKEND='local', PRIVATE_STORAGE_DIR=str(root / ('restored-documents' if restored else 'documents')), SMTP_HOST='127.0.0.1', SMTP_PORT=str(value['smtp_port']), SMTP_FROM='pm-rehearsal@example.test', SMTP_STARTTLS='false', CLAMAV_HOST='127.0.0.1', CLAMAV_PORT='13310', APP_BASE_URL=f"http://localhost:{value['web_port']}", PDF_PARSER_MODE='docker', PDF_PARSER_IMAGE=value['parser_image'], PDF_DOCKER_EXECUTABLE=str(Path(executable).resolve()))
    return env


def application(value, database='database_url', restored=False, testing=False, clock=None):
    # Only explicit values are passed; inherited provider/S3/SMTP overrides removed.
    env = environment(value, database, restored)
    os.environ.clear()
    os.environ.update(env)
    sys.path.insert(0, str(ROOT))
    from app import create_app
    # This helper only permits manifest-owned disposable loopback databases.
    # Repeated five-persona rehearsals must not share the production login budget.
    # The actual application factory keeps its normal AUTH_RATE_LIMIT=30.
    config = {'LOAD_PILOT_ENV': False, 'TESTING': testing, 'APP_ENV': 'development', 'AUTH_RATE_LIMIT': 500}
    if clock is not None:
        if not testing:
            raise ValueError('Clock injection is test-only')
        config['TEST_CLOCK'] = clock
    return create_app(config)


def preflight_ports(value):
    for key in ('api_port', 'web_port', 'smtp_port', 'inbox_port'):
        with socket.socket() as channel:
            try:
                channel.bind(('127.0.0.1', value[key]))
            except OSError as error:
                raise RuntimeError(f'{key} occupied; refuse moving ports or stopping another session') from error


def prepare(path=MANIFEST):
    path = private_path(path)
    if path.exists():
        raise ValueError('Existing run manifest preserved; choose a new manifest explicitly')
    if sys.version_info[:2] != (3, 13):
        raise RuntimeError('This local rehearsal requires existing tested CPython3.13')
    node = shutil.which('node')
    if not node:
        raise RuntimeError('Existing Node runtime required')
    version = command([node, '--version'])
    if not version.startswith('v26.'):
        raise RuntimeError('This local rehearsal is tested with existing Node26; do not install automatically')
    command(['docker', 'image', 'inspect', PARSER_IMAGE])
    command(['docker', 'image', 'inspect', MAIL_IMAGE])
    configured = dotenv_values(ROOT / '.env.pilot').get('DATABASE_URL')
    parsed = urlsplit(configured or '')
    if parsed.scheme != 'postgresql+psycopg' or parsed.hostname not in {'localhost', '127.0.0.1'} or parsed.port != 55432:
        raise ValueError('Existing loopback PostgreSQL config required')
    namespace = 'machivital_pm_' + secrets.token_hex(6)
    run_dir = ROOT / '.pilot' / namespace
    value = dict(namespace=namespace, run_dir=str(run_dir), api_port=5053, web_port=5174, smtp_port=11027, inbox_port=8027, secret_key=secrets.token_hex(32), mfa_key=Fernet.generate_key().decode(), parser_image=PARSER_IMAGE, mail_image=MAIL_IMAGE, mail_container=namespace+'-mail')
    for key, suffix in [('database_url',''), ('test_database_url','_test'), ('restore_database_url','_restore')]:
        value[key] = urlunsplit(parsed._replace(path='/' + namespace + suffix, query='', fragment=''))
    validate_manifest(value)
    preflight_ports(value)
    with socket.create_connection(('127.0.0.1',13310), timeout=10) as scanner:
        scanner.sendall(b'zPING\0')
        if not scanner.recv(128).startswith(b'PONG'):
            raise RuntimeError('Existing local scanner unavailable')
    run_dir.mkdir(parents=True, exist_ok=False)
    # Preserve the ownership manifest before provisioning; a partial failure must
    # not leave unidentifiable databases/containers or trigger destructive cleanup.
    with path.open('x', encoding='utf-8') as stream:
        json.dump({**value, 'preparation_state':'provisioning'}, stream, indent=2)
    for directory in ('documents','restored-documents','logs','backups','mail'):
        (run_dir/directory).mkdir()
    admin_url = urlunsplit(parsed._replace(scheme='postgresql', path='/postgres', query='', fragment=''))
    with psycopg.connect(admin_url, autocommit=True) as connection:
        for suffix in ('','_test','_restore'):
            connection.execute(sql.SQL('CREATE DATABASE {} TEMPLATE template0').format(sql.Identifier(namespace+suffix)))
    command(['docker', 'run', '--detach', '--pull', 'never', '--name', value['mail_container'], '--restart', 'no', '--network', 'bridge', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges=true', '--memory', '128m', '-p', f"127.0.0.1:{value['smtp_port']}:1025", '-p', f"127.0.0.1:{value['inbox_port']}:8025", '-e', 'MP_DATABASE=/data/mail.db', '-v', str(run_dir/'mail')+':/data', MAIL_IMAGE])
    # The only replaced file is this run's freshly created provisioning record.
    with path.open('w', encoding='utf-8') as stream:
        json.dump({**value, 'preparation_state':'prepared'}, stream, indent=2)
    print('PASS: isolated databases, temporary keys, blob roots and Mailpit prepared; original databases/config/mailbox unchanged')
    print('Run namespace:', namespace)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['prepare','info','migrate','check','api','worker','test-env','stop-mail'])
    parser.add_argument('--manifest', type=Path, default=MANIFEST)
    parser.add_argument('--seconds', type=int, default=900)
    args = parser.parse_args()
    if args.mode == 'prepare':
        prepare(args.manifest)
        return
    value = load_manifest(args.manifest)
    if args.mode == 'info':
        print(json.dumps({key:value[key] for key in ('namespace','api_port','web_port','smtp_port','inbox_port')},indent=2))
        return
    if args.mode == 'test-env':
        raise SystemExit('Do not print credential-bearing test environment; use run_pm_checks.py')
    if args.mode == 'stop-mail':
        command(['docker','stop',value['mail_container']])
        print('Isolated mail stopped; persistent evidence retained')
        return
    app = application(value)
    if args.mode in {'migrate','check'}:
        from flask_migrate import upgrade, check
        with app.app_context():
            (upgrade if args.mode == 'migrate' else check)(directory=str(ROOT/'migrations_pilot'))
        print('PASS:',args.mode,'isolated',value['namespace'])
    elif args.mode == 'api':
        app.run(host='127.0.0.1',port=value['api_port'],debug=False,use_reloader=False)
    else:
        if not 1 <= args.seconds <= 1800:
            raise ValueError('Duration must be1–1800 seconds')
        from app.pilot.worker import run_service
        run_service(app, seconds=args.seconds)


if __name__ == '__main__':
    main()
