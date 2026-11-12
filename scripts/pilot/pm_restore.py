"""Snapshot/restore the isolated PM app plus private blobs; originals refused.

Stop the owned worker before backup. Matching test keys remain in run manifest,
never included in dump/blobs. Restores only once into its new empty scratch DB.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
from urllib.parse import urlsplit

import psycopg

ROOT = Path(__file__).resolve().parents[2]


def runtime():
    spec = importlib.util.spec_from_file_location('pm_restore_runtime', ROOT/'scripts/pilot/pm_runtime.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(args, content=None):
    allowed = {'SYSTEMROOT','WINDIR','PATH','HOME','USERPROFILE','LANG','TEMP','TMP','COMSPEC','PATHEXT','LOCALAPPDATA','APPDATA'}
    safe_env = {key:value for key,value in os.environ.items() if key.upper() in allowed}
    result = subprocess.run(['docker','exec','-i','machivital-pilot-db',*args],input=content,capture_output=True,timeout=120,env=safe_env)
    if result.returncode:
        import secrets
        evidence=ROOT/'.pilot'/'pm-command-errors'
        evidence.mkdir(parents=True,exist_ok=True)
        (evidence/(secrets.token_hex(8)+'.log')).write_bytes(result.stderr)
        raise RuntimeError('Isolated backup/restore failed; private raw error preserved, source/original DBs unchanged')
    return result.stdout


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def blob_inventory(directory):
    import re
    result={}
    for path in directory.iterdir():
        if path.is_symlink() or not path.is_file() or not re.fullmatch(r'[a-f0-9]{32}\.pdf',path.name):
            raise RuntimeError('Unexpected private blob path; refuse unowned backup content')
        result[path.name]=sha(path)
    return result


def backup(value):
    root = Path(value['run_dir'])
    output = root/'backups'/'snapshot'
    output.mkdir(exist_ok=False)
    source = urlsplit(value['database_url']).path.lstrip('/')
    connection_url = value['database_url'].replace('postgresql+psycopg://','postgresql://')
    with psycopg.connect(connection_url) as connection:
        connection.execute('BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        snapshot = connection.execute('SELECT pg_export_snapshot()').fetchone()[0]
        before = blob_inventory(root/'documents')
        dump = run(['pg_dump','-U','machivital','-d',source,'--format=custom','--no-owner','--no-acl','--snapshot='+snapshot])
        shutil.copytree(root/'documents',output/'documents')
        if before != blob_inventory(output/'documents') or before != blob_inventory(root/'documents'):
            raise RuntimeError('Blob source changed during backup; evidence retained, do not restore')
    (output/'database.dump').write_bytes(dump)
    proof = {'source_database':source,'blob_hashes':before,'dump_sha256':sha(output/'database.dump'),'keys_included':False}
    (output/'manifest.json').write_text(json.dumps(proof,indent=2),encoding='utf-8')
    print('PASS: isolated snapshot and',len(before),'private blobs backed up; test keys kept separately')


def restore(value):
    root = Path(value['run_dir'])
    output = root/'backups'/'snapshot'
    proof = json.loads((output/'manifest.json').read_text(encoding='utf-8'))
    if proof['source_database'] != value['namespace'] or proof['keys_included'] is not False or proof['dump_sha256'] != sha(output/'database.dump') or proof['blob_hashes'] != blob_inventory(output/'documents'):
        raise RuntimeError('Backup integrity/provenance failure')
    target = urlsplit(value['restore_database_url']).path.lstrip('/')
    if target != value['namespace']+'_restore':
        raise RuntimeError('Refusing nonisolated restore')
    with psycopg.connect(value['restore_database_url'].replace('postgresql+psycopg://','postgresql://')) as connection:
        if connection.execute("SELECT EXISTS(SELECT 1 FROM pg_tables WHERE schemaname='public')").fetchone()[0]:
            raise RuntimeError('Restore target not empty; never overwrite existing data')
    directory = root/'restored-documents'
    if any(directory.iterdir()):
        raise RuntimeError('Restore blob target not empty')
    run(['pg_restore','-U','machivital','-d',target,'--exit-on-error','--no-owner','--no-acl'],(output/'database.dump').read_bytes())
    for source in (output/'documents').iterdir():
        if source.is_file():
            shutil.copy2(source,directory/source.name)
    if blob_inventory(directory) != proof['blob_hashes']:
        raise RuntimeError('Restored blob checksum mismatch')
    print('PASS: restored isolated DB and',len(proof['blob_hashes']),'blobs to new targets; app/MFA verification still required')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=['backup','restore'])
    args=parser.parse_args()
    value=runtime().load_manifest()
    (backup if args.mode=='backup' else restore)(value)


if __name__=='__main__':
    main()
