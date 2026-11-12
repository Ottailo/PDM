"""Restore refuses forged/corrupt/shared evidence before any DB/tool mutation."""
import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[2]


def module():
    spec = importlib.util.spec_from_file_location('restore_under_test', ROOT/'scripts/pilot/pm_restore.py')
    result=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def setup(tmp_path):
    root=tmp_path/'isolated'
    output=root/'backups/snapshot'
    (output/'documents').mkdir(parents=True)
    (root/'restored-documents').mkdir()
    (output/'database.dump').write_bytes(b'synthetic-only-backup')
    (output/'documents'/'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.pdf').write_bytes(b'%PDF-test')
    runner=module()
    proof={'source_database':'machivital_pm_aaaaaaaaaaaa','blob_hashes':runner.blob_inventory(output/'documents'),'dump_sha256':runner.sha(output/'database.dump'),'keys_included':False}
    (output/'manifest.json').write_text(json.dumps(proof))
    config={'run_dir':str(root),'namespace':proof['source_database'],'restore_database_url':'postgresql+psycopg://x:x@localhost:55432/'+proof['source_database']+'_restore'}
    return runner,config,output,proof


def test_private_blob_inventory_rejects_unknown_name(tmp_path):
    runner=module()
    (tmp_path/'unowned.txt').write_text('do not import',encoding='utf-8')
    with pytest.raises(RuntimeError,match='Unexpected private blob'):
        runner.blob_inventory(tmp_path)


@pytest.mark.parametrize('kind',['dump','blob','source','keys','target'])
def test_corrupt_or_unowned_restore_refused_before_io(tmp_path,kind):
    runner,config,output,proof=setup(tmp_path)
    if kind=='dump': (output/'database.dump').write_bytes(b'corrupt')
    elif kind=='blob': (output/'documents'/'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.pdf').write_bytes(b'corrupt')
    elif kind=='source': proof['source_database']='machivital_pilot'
    elif kind=='keys': proof['keys_included']=True
    else: config['restore_database_url']='postgresql+psycopg://x:x@localhost:55432/machivital_pilot'
    (output/'manifest.json').write_text(json.dumps(proof))
    with patch.object(runner.psycopg,'connect',side_effect=AssertionError('DB must not open')),patch.object(runner,'run',side_effect=AssertionError('Tool must not run')):
        with pytest.raises(RuntimeError): runner.restore(config)
