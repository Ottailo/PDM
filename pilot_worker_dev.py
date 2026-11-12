"""Explicit bounded local worker for development integration verification.

This is not a production scheduler and never starts the application server.
"""
import argparse
from pathlib import Path
import time
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / '.env.pilot', override=False)

from app import create_app
from app.pilot.worker import run_once


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seconds', type=int, default=600)
    args = parser.parse_args()
    if not 1 <= args.seconds <= 1800:
        parser.error('Duration must be 1–1800 seconds')
    app = create_app()
    if app.config['APP_ENV'] != 'development':
        raise SystemExit('This bounded worker is development only')
    deadline = time.monotonic() + args.seconds
    total = 0
    while time.monotonic() < deadline:
        result = run_once(app)
        if result['processed']:
            total += 1
            print(f"Job {result.get('job_id', '?')}: {result.get('state', 'unknown')}", flush=True)
        else:
            time.sleep(0.25)
    print(f'Development worker stopped after {total} claimed jobs', flush=True)


if __name__ == '__main__':
    main()
