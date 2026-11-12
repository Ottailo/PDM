"""Verify a local pilot database backup restores into an isolated scratch DB.

Does not restore over a working database or access original SQLite files.
"""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import subprocess

import psycopg
from psycopg import sql
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[2]
CONTAINER = 'machivital-pilot-db'


def execute(*arguments: str, input_data: bytes | None = None) -> bytes:
    result = subprocess.run(['docker', 'exec', '-i', CONTAINER, *arguments], input=input_data, capture_output=True, check=True)
    return result.stdout


def inventory(database: str) -> list[str]:
    sql = "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
    tables = execute('psql', '-U', 'machivital', '-d', database, '-At', '-c', sql).decode().splitlines()
    result = []
    for table in tables:
        # Database-derived names, independently identifier quoted.
        escaped = table.replace('"', '""')
        count = execute('psql', '-U', 'machivital', '-d', database, '-At', '-c', f'SELECT count(*) FROM "{escaped}"').decode().strip()
        result.append(f'{table}:{count}')
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--database', choices=['machivital_pilot', 'machivital_test'], default='machivital_pilot')
    args = parser.parse_args()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')
    target = f'machivital_restore_check_{stamp}'
    configured = dotenv_values(ROOT / '.env.pilot')['DATABASE_URL']
    uri = configured.replace('postgresql+psycopg://', 'postgresql://')
    # Keep an exported snapshot alive while pg_dump and row counts read it.
    # Concurrent application writes must not make a valid backup look corrupt.
    with psycopg.connect(uri, dbname=args.database) as connection:
        connection.execute('BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        snapshot = connection.execute('SELECT pg_export_snapshot()').fetchone()[0]
        tables = connection.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename").fetchall()
        before = [f'{table}:{connection.execute(sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(table))).fetchone()[0]}' for (table,) in tables]
        if not before:
            raise SystemExit('No migrated tables; empty database backup is not release proof')
        dump = execute('pg_dump', '-U', 'machivital', '-d', args.database, '--format=custom', '--no-owner', '--no-acl', '--snapshot=' + snapshot)
    backup = ROOT / '.pilot' / 'backups' / f'{args.database}-{stamp}.dump'
    backup.parent.mkdir(parents=True, exist_ok=True)
    backup.write_bytes(dump)
    execute('createdb', '-U', 'machivital', target)
    execute('pg_restore', '-U', 'machivital', '-d', target, '--exit-on-error', '--no-owner', '--no-acl', input_data=dump)
    after = inventory(target)
    assert before == after, 'Restored tables/counts differ from captured source; inspect scratch DB'
    print(f'PASS: {len(before)} migrated tables and row counts match a scratch restore')
    print(f'Private backup saved under .pilot/backups; scratch database {target} retained for inspection')
    print('No original data replaced. This verifies local restore, not production backup operations.')


if __name__ == '__main__':
    main()
