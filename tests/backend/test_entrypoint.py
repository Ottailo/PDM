"""Optional deployment adapter never returns traces or starts the simulator."""
import importlib.util
from pathlib import Path
from unittest.mock import patch


def test_optional_adapter_hides_startup_error():
    path = Path(__file__).resolve().parents[2] / 'api' / 'index.py'
    spec = importlib.util.spec_from_file_location('pilot_entrypoint_fixture', path)
    module = importlib.util.module_from_spec(spec)
    with patch('app.create_app', side_effect=RuntimeError('private-secret-must-not-leak')):
        spec.loader.exec_module(module)
    responses = []
    body = b''.join(module.app({'QUERY_STRING': '', 'PATH_INFO': '/'}, lambda status, headers: responses.append((status, headers))))
    assert responses[0][0] == '503 Service Unavailable'
    assert b'private-secret' not in body and b'Traceback' not in body
