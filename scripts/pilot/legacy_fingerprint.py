"""Record/check legacy database identity without opening the application.

Output lives in ignored .pilot storage. This is evidence protection, not a migration.
"""
from pathlib import Path
import argparse
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / '.pilot' / 'legacy-fingerprint.json'


def fingerprint() -> dict:
    result = {}
    for file in sorted((ROOT / 'instance').glob('*.db')):
        digest = hashlib.sha256()
        with file.open('rb') as stream:
            while chunk := stream.read(1024 * 1024):
                digest.update(chunk)
        result[file.name] = {'size': file.stat().st_size, 'sha256': digest.hexdigest()}
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    current = fingerprint()
    if args.check:
        saved = json.loads(STATE.read_text(encoding='utf-8'))
        assert current == saved, 'Legacy database changed; stop and inspect before continuing'
        print(f'PASS: {len(current)} legacy database files unchanged')
    else:
        if STATE.exists():
            raise SystemExit('Existing fingerprint preserved; use --check')
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(json.dumps(current, indent=2), encoding='utf-8')
        print(f'Recorded read-only fingerprint of {len(current)} legacy database files; no data printed')


if __name__ == '__main__':
    main()
