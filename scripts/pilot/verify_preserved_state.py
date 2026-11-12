"""Read-only original pilot/blob/source fingerprint, stored privately per run.

Never imports the application or writes to a database. Baseline refuses overwrite.
"""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit

import psycopg
from psycopg import sql
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[2]


def file_hash(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def snapshot():
    config = dotenv_values(ROOT / '.env.pilot')
    parsed = urlsplit(config['DATABASE_URL'])
    if parsed.hostname not in {'localhost', '127.0.0.1'} or parsed.port != 55432 or parsed.path != '/machivital_pilot':
        raise SystemExit('Refusing unexpected original database target')
    database = {}
    with psycopg.connect(config['DATABASE_URL'].replace('postgresql+psycopg://', 'postgresql://')) as connection:
        connection.execute('BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        tables = connection.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename").fetchall()
        for (table,) in tables:
            # Stable sorted JSON row representation; hashes never expose private rows.
            rows = connection.execute(sql.SQL('SELECT row_to_json(t)::text FROM {} t ORDER BY row_to_json(t)::text').format(sql.Identifier(table)))
            digest = hashlib.sha256()
            count = 0
            for (row,) in rows:
                encoded = row.encode('utf-8')
                digest.update(len(encoded).to_bytes(8, 'big'))
                digest.update(encoded)
                count += 1
            database[table] = {'rows': count, 'sha256': digest.hexdigest()}
    protected = [ROOT / '.env.pilot', ROOT / 'migrations_pilot/versions/pilot_0001.py']
    # Discover frozen migration name without assuming a filename.
    protected += list((ROOT / 'migrations_pilot/versions').glob('*0001*'))
    protected += list((ROOT / 'instance').glob('*.db'))
    storage = Path(config['PRIVATE_STORAGE_DIR'])
    if not storage.is_absolute():
        storage = ROOT / storage
    protected += [path for path in storage.rglob('*') if path.is_file()]
    files = {str(path.relative_to(ROOT)): file_hash(path) for path in set(protected) if path.is_file()}
    return {'original_database': database, 'protected_files': files}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', required=True, type=Path)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    destination = args.baseline.resolve()
    if ROOT / '.pilot' not in destination.parents:
        parser.error('Fingerprint evidence must live in ignored .pilot storage')
    current = snapshot()
    if args.check:
        saved = json.loads(destination.read_text(encoding='utf-8'))
        if saved != current:
            raise SystemExit('Preserved original pilot/database/blob/config changed; stop and inspect')
        print(f"PASS: {len(current['original_database'])} original tables and {len(current['protected_files'])} protected files unchanged")
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open('x', encoding='utf-8') as stream:
            json.dump(current, stream, indent=2)
        print(f"PASS: read-only baseline of {len(current['original_database'])} original tables and {len(current['protected_files'])} protected files recorded")


if __name__ == '__main__':
    main()
