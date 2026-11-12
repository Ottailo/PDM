"""Explicit isolated security verification API/worker; never original pilot data.

Server starts only via Browser preview. Existing private env supplies unchanged
local secrets; database/blob overrides are process-local and fixed to this run.
"""
import argparse
import os
from pathlib import Path
import shutil
import sys
import time
from urllib.parse import urlsplit, urlunsplit

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[2]
DATABASE = 'machivital_security_20261112'
IMAGE = 'sha256:94eb11fac2a171ce59582f4f74aa039f496531b5621861786323cabb45fe9316'


def application():
    config = dotenv_values(ROOT / '.env.pilot')
    source = urlsplit(config['DATABASE_URL'])
    if source.hostname not in {'localhost', '127.0.0.1'} or source.port != 55432:
        raise SystemExit('Refusing nonlocal source configuration')
    if config.get('SMTP_HOST') not in {'localhost', '127.0.0.1'} or config.get('SMTP_PORT') != '11026':
        raise SystemExit('Verification mail must use existing loopback Mailpit')
    if config.get('CLAMAV_HOST') not in {'localhost', '127.0.0.1'} or config.get('CLAMAV_PORT') != '13310':
        raise SystemExit('Verification scanner must use existing loopback ClamAV')
    for key, value in config.items():
        if value is not None:
            os.environ[key] = value
    executable = shutil.which('docker')
    if not executable:
        raise SystemExit('Existing Docker executable unavailable')
    os.environ.update(
        APP_ENV='development',
        DATABASE_URL=urlunsplit(source._replace(path='/' + DATABASE)),
        PRIVATE_STORAGE_DIR=str(ROOT / '.pilot' / 'security-20261112' / 'documents'),
        PDF_PARSER_MODE='docker', PDF_PARSER_IMAGE=IMAGE,
        PDF_DOCKER_EXECUTABLE=str(Path(executable).resolve()),
    )
    sys.path.insert(0, str(ROOT))
    from app import create_app
    return create_app()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['api', 'worker', 'migrate', 'check'])
    parser.add_argument('--seconds', type=int, default=600)
    args = parser.parse_args()
    if not 1 <= args.seconds <= 1800:
        parser.error('Worker duration must be 1–1800 seconds')
    app = application()
    if args.mode in {'migrate', 'check'}:
        from flask_migrate import upgrade, check
        with app.app_context():
            (upgrade if args.mode == 'migrate' else check)(directory=str(ROOT / 'migrations_pilot'))
        print(f'PASS: {args.mode} isolated {DATABASE}; original pilot not migrated')
    elif args.mode == 'api':
        app.run(host='127.0.0.1', port=5051, debug=False, use_reloader=False)
    else:
        from app.pilot.worker import run_once
        deadline = time.monotonic() + args.seconds
        while time.monotonic() < deadline:
            result = run_once(app)
            if result['processed']:
                print(f"Verification job: {result.get('state', 'unknown')}", flush=True)
            else:
                time.sleep(0.25)
        print('Bounded verification worker stopped', flush=True)


if __name__ == '__main__':
    main()
