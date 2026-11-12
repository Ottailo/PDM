"""Read-only consistency assertion against the completed scratch restore proof."""
from pathlib import Path
import importlib.util
import pytest

ROOT=Path(__file__).resolve().parents[2]


def test_completed_snapshot_blob_hashes_match_restored_files():
    spec=importlib.util.spec_from_file_location('restore_snapshot_check',ROOT/'scripts/pilot/pm_restore.py')
    runner=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    value=runner.runtime().load_manifest()
    root=Path(value['run_dir'])
    if not (root/'backups/snapshot/manifest.json').is_file():
        pytest.fail('Explicit local PM restore proof missing; skipped checks are not proof')
    assert runner.blob_inventory(root/'backups/snapshot/documents')==runner.blob_inventory(root/'restored-documents')
