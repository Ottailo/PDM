"""No database fixtures. Run pytest --noconftest on this module only.

Real Docker integration is opt-in via PDM_PARSER_SANDBOX_IMAGE. Its independent
verifier also checks containment flags and syscall denials on the actual host.
"""
import importlib.util
import json
import os
from pathlib import Path
import sys
import time

from flask import Flask
import pytest

ROOT = Path(__file__).resolve().parents[2]
IMAGE = 'sha256:' + '1' * 64


def load_runner():
    spec = importlib.util.spec_from_file_location('sandbox_runner_unit', ROOT / 'app/pilot/sandbox_runner.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def runner():
    return load_runner()


@pytest.fixture
def sandbox_app():
    app = Flask('sandbox-unit')
    app.config.update(APP_ENV='test', TESTING=True, PDF_MAX_BYTES=10485760, PDF_MAX_PAGES=200,
                      PDF_MAX_TEXT=1000000, PDF_PARSE_TIMEOUT=25, PDF_PARSER_IMAGE=IMAGE)
    return app


def image_metadata():
    return [{'Id': IMAGE, 'Os': 'linux', 'RepoDigests': [], 'Config': {
        'Entrypoint': ['python3', '-I', '/parser/parser.py'], 'Cmd': [],
        'User': '65532:65532', 'WorkingDir': '/parser', 'Volumes': None}}]


def fake_runtime(runner, monkeypatch, security=None, metadata=None):
    def control(_executable, args, **_kwargs):
        if args[0] == 'info':
            return {'OSType': 'linux', 'SecurityOptions': security if security is not None else ['name=seccomp,profile=builtin', 'name=rootless']}
        return metadata if metadata is not None else image_metadata()
    monkeypatch.setattr(runner, '_json_control', control)


def test_fixed_container_command_has_no_user_command_options(runner):
    args = runner._container_args('fixed-name', IMAGE, 10485760, 200, 1000000)
    assert args[:3] == ['create', '--name', 'fixed-name']
    assert args[-4:] == [IMAGE, '10485760', '200', '1000000']
    expected = {'--pull': 'never', '--network': 'none', '--user': '65532:65532',
                '--cap-drop': 'ALL', '--security-opt': 'no-new-privileges=true',
                '--pids-limit': '32', '--memory': '384m', '--memory-swap': '384m', '--cpus': '1',
                '--ipc': 'private', '--cgroupns': 'private',
                '--tmpfs': '/tmp:rw,noexec,nosuid,nodev,size=16m,mode=1777', '--log-driver': 'none'}
    for flag, value in expected.items():
        assert args[args.index(flag) + 1] == value
    assert '--read-only' in args
    assert '--pid' not in args  # Docker defaults to a private PID namespace.
    assert not {'--volume', '-v', '--mount', '--env', '-e', '--privileged', '--device', '--entrypoint', '--pid=host'} & set(args)


@pytest.mark.parametrize('image', ['latest', 'parser:tag', 'sha256:abc', 'sha256:' + 'A' * 64, '--privileged', None])
def test_mutable_or_invalid_image_is_rejected_before_cli(runner, monkeypatch, image):
    monkeypatch.setattr(runner, '_json_control', lambda *_args, **_kwargs: pytest.fail('CLI must not run'))
    with pytest.raises(runner.ParserUnavailable, match='immutable'):
        runner._resolve_image('docker', image, 'test')


def test_production_rootful_fails_closed(runner, monkeypatch):
    fake_runtime(runner, monkeypatch, security=['name=seccomp,profile=builtin'])
    with pytest.raises(runner.ParserUnavailable, match='rootless'):
        runner._resolve_image('docker', IMAGE, 'production')
    assert runner._resolve_image('docker', IMAGE, 'development') == IMAGE
    assert runner._resolve_image('docker', IMAGE, 'test') == IMAGE


def test_production_rootless_passes_metadata_gate(runner, monkeypatch):
    fake_runtime(runner, monkeypatch)
    assert runner._resolve_image('docker', IMAGE, 'production') == IMAGE


def test_seccomp_required_even_locally(runner, monkeypatch):
    fake_runtime(runner, monkeypatch, security=['name=rootless'])
    with pytest.raises(runner.ParserUnavailable, match='seccomp'):
        runner._resolve_image('docker', IMAGE, 'test')


@pytest.mark.parametrize('key,value', [('Entrypoint', ['/bin/sh']), ('Cmd', ['evil']), ('User', '0'), ('Volumes', {'/private': {}}), ('WorkingDir', '/tmp')])
def test_image_contract_rejects_overrides(runner, monkeypatch, key, value):
    metadata = image_metadata()
    metadata[0]['Config'][key] = value
    fake_runtime(runner, monkeypatch, metadata=metadata)
    with pytest.raises(runner.ParserUnavailable, match='contract'):
        runner._resolve_image('docker', IMAGE, 'test')


def test_digest_resolves_to_inspected_immutable_identity(runner, monkeypatch):
    digest = 'registry.example/parser@sha256:' + '2' * 64
    metadata = image_metadata()
    metadata[0]['RepoDigests'] = [digest]
    fake_runtime(runner, monkeypatch, metadata=metadata)
    assert runner._resolve_image('docker', digest, 'test') == IMAGE
    with pytest.raises(runner.ParserUnavailable, match='did not match'):
        runner._resolve_image('docker', 'registry.example/parser@sha256:' + '3' * 64, 'test')


def test_environment_has_no_app_secrets_or_docker_flags(runner, monkeypatch):
    monkeypatch.setenv('SECRET_KEY', 'never-export')
    monkeypatch.setenv('MFA_ENCRYPTION_KEY', 'never-export')
    monkeypatch.setenv('DOCKER_HOST', 'tcp://unexpected:2375')
    monkeypatch.setenv('DOCKER_CONFIG', 'unexpected')
    monkeypatch.setenv('PYTHONPATH', 'unexpected')
    environment = runner._environment()
    assert not {'SECRET_KEY', 'MFA_ENCRYPTION_KEY', 'DOCKER_HOST', 'DOCKER_CONFIG', 'PYTHONPATH'} & environment.keys()


def test_default_docker_executable_resolves_to_fixed_binary(runner, monkeypatch, tmp_path):
    executable = tmp_path / 'docker.exe'
    executable.touch()
    monkeypatch.setattr(runner.shutil, 'which', lambda name: str(executable) if name == 'docker' else None)
    assert runner._docker_executable({'PDF_DOCKER_EXECUTABLE': 'docker'}) == str(executable.resolve())
    monkeypatch.setattr(runner.shutil, 'which', lambda _name: None)
    with pytest.raises(runner.ParserUnavailable, match='unavailable'):
        runner._docker_executable({'PDF_DOCKER_EXECUTABLE': 'docker'})


@pytest.mark.parametrize('value', ['docker --privileged', '/missing/docker', '/bin/sh'])
def test_executable_override_is_not_arbitrary_command(runner, value):
    with pytest.raises(runner.ParserUnavailable):
        runner._docker_executable({'PDF_DOCKER_EXECUTABLE': value})


def test_no_silent_docker_fallback(runner, sandbox_app, monkeypatch):
    assert 'PDF_PARSER_MODE' not in sandbox_app.config
    monkeypatch.setattr(runner, '_docker_executable', lambda _config: (_ for _ in ()).throw(runner.ParserUnavailable('Docker missing')))
    monkeypatch.setattr(runner, '_bounded_process', lambda *_args, **_kwargs: pytest.fail('No development fallback'))
    with sandbox_app.app_context(), pytest.raises(runner.ParserUnavailable, match='missing'):
        runner.parse_pdf(b'%PDF-test')


def test_development_mode_never_production_even_testing(runner, sandbox_app, monkeypatch):
    sandbox_app.config.update(PDF_PARSER_MODE='development', APP_ENV='production', TESTING=True)
    monkeypatch.setattr(runner, '_bounded_process', lambda *_args, **_kwargs: pytest.fail('Must not launch'))
    with sandbox_app.app_context(), pytest.raises(runner.ParserUnavailable, match='forbidden'):
        runner.parse_pdf(b'%PDF-test')


@pytest.mark.parametrize('key,value', [('PDF_MAX_BYTES', 10485761), ('PDF_MAX_PAGES', 201), ('PDF_MAX_TEXT', 1000001),
                                      ('PDF_MAX_PAGES', True), ('PDF_PARSE_TIMEOUT', 0), ('PDF_PARSE_TIMEOUT', float('nan')), ('PDF_PARSE_TIMEOUT', 61)])
def test_limit_configs_fail_closed(runner, sandbox_app, key, value):
    sandbox_app.config[key] = value
    with sandbox_app.app_context(), pytest.raises(runner.ParserUnavailable):
        runner.parse_pdf(b'%PDF-test')


@pytest.mark.parametrize('content', [b'', 'not bytes', b'x' * 100])
def test_input_bounds_before_runtime(runner, sandbox_app, monkeypatch, content):
    sandbox_app.config['PDF_MAX_BYTES'] = 10
    monkeypatch.setattr(runner, '_docker_executable', lambda _config: pytest.fail('No runtime call'))
    with sandbox_app.app_context(), pytest.raises(runner.ParserRejected):
        runner.parse_pdf(content)


@pytest.mark.parametrize('result', [[], {'pages': []}, {'pages': [123]}, {'pages': ['x' * 100001]}, {'pages': ['x'], 'extra': 1}, {'pages': ['xx']}])
def test_output_schema_and_caps(runner, result):
    with pytest.raises(runner.ParserRejected):
        runner._validate_output(0, json.dumps(result).encode(), 1, 1)
    assert runner._validate_output(0, b'{"pages":["x"]}', 1, 1) == ['x']


def test_untrusted_error_not_reflected(runner):
    with pytest.raises(runner.ParserRejected) as error:
        runner._validate_output(1, b'{"error":"secret attacker payload"}', 200, 1000000)
    assert str(error.value) == 'PDF could not be parsed safely'


def test_named_container_removed_on_timeout(runner, sandbox_app, monkeypatch):
    calls = []
    monkeypatch.setattr(runner, '_docker_executable', lambda _config: 'docker')
    monkeypatch.setattr(runner, '_resolve_image', lambda *_args: IMAGE)
    monkeypatch.setattr(runner, '_control', lambda _executable, args, **_kwargs: calls.append(args) or b'')
    monkeypatch.setattr(runner, '_bounded_process', lambda *_args, **_kwargs: (_ for _ in ()).throw(runner._Deadline()))
    with sandbox_app.app_context(), pytest.raises(runner.ParserRejected, match='deadline'):
        runner.parse_pdf(b'%PDF-test')
    name = calls[0][2]
    assert ['rm', '--force', name] in calls
    assert any(args[:3] == ['container', 'ls', '--all'] for args in calls)


def test_uncertain_create_failure_removes_named_container(runner, sandbox_app, monkeypatch):
    calls = []
    monkeypatch.setattr(runner, '_docker_executable', lambda _config: 'docker')
    monkeypatch.setattr(runner, '_resolve_image', lambda *_args: IMAGE)

    def control(_executable, args, **_kwargs):
        calls.append(args)
        if args[0] == 'create':
            raise runner.ParserUnavailable('create deadline exceeded')
        if args[:3] == ['container', 'ls', '--all'] and len(calls) == 2:
            return b'machivital-pdf-created-before-cli-timeout'
        return b''

    monkeypatch.setattr(runner, '_control', control)
    with sandbox_app.app_context(), pytest.raises(runner.ParserUnavailable, match='create deadline'):
        runner.parse_pdf(b'%PDF-test')
    assert ['rm', '--force', calls[0][2]] in calls


def test_cleanup_failure_prevents_success(runner, sandbox_app, monkeypatch):
    monkeypatch.setattr(runner, '_docker_executable', lambda _config: 'docker')
    monkeypatch.setattr(runner, '_resolve_image', lambda *_args: IMAGE)
    monkeypatch.setattr(runner, '_control', lambda *_args, **_kwargs: b'')
    monkeypatch.setattr(runner, '_bounded_process', lambda *_args, **_kwargs: (0, b'{"pages":["ok"]}', b''))
    monkeypatch.setattr(runner, '_remove_container', lambda *_args: (_ for _ in ()).throw(runner.ParserUnavailable('cleanup failed')))
    with sandbox_app.app_context(), pytest.raises(runner.ParserUnavailable, match='cleanup'):
        runner.parse_pdf(b'%PDF-test')


@pytest.mark.parametrize('channel', ['stdout', 'stderr'])
def test_real_streaming_output_bound(runner, channel):
    started = time.monotonic()
    command = [sys.executable, '-I', '-c', f"import sys; s=sys.{channel}.buffer; [s.write(b'x'*8192) or s.flush() for _ in range(100000)]"]
    with pytest.raises(runner._OutputLimit):
        runner._bounded_process(command, timeout=5, stdout_limit=1024, stderr_limit=1024)
    assert time.monotonic() - started < 5


def test_real_stdin_block_deadline(runner):
    command = [sys.executable, '-I', '-c', 'import time; time.sleep(10)']
    started = time.monotonic()
    with pytest.raises(runner._Deadline):
        runner._bounded_process(command, b'x' * 1048576, timeout=0.2)
    assert time.monotonic() - started < 3


def test_parser_entry_limits_and_extraction_negative_controls():
    spec = importlib.util.spec_from_file_location('isolated_parser_unit', ROOT / 'sandbox/pdf/parser.py')
    parser = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(parser)
    assert parser.limits(['1024', '1', '100']) == (1024, 1, 100)
    for args in (['--help'], ['1024', '201', '100'], ['0', '1', '1'], ['1', '1', '١'], ['1', '1', '1', 'ignored']):
        with pytest.raises(parser.Rejected):
            parser.limits(args)
    verifier = _load_verifier()
    import io
    assert parser.extract(io.BytesIO(verifier.fixture()), 10485760, 200, 1000000) == ['TESTONLY42']
    for kind in ('active', 'encrypted'):
        with pytest.raises(parser.Rejected):
            parser.extract(io.BytesIO(verifier.fixture(kind)), 10485760, 200, 1000000)
    with pytest.raises(parser.Rejected, match='text'):
        parser.extract(io.BytesIO(verifier.fixture()), 10485760, 200, 1)


def _load_verifier():
    spec = importlib.util.spec_from_file_location('sandbox_probe_test', ROOT / 'scripts/pilot/verify_parser_sandbox.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.skipif(not os.environ.get('PDM_PARSER_SANDBOX_IMAGE'), reason='Opt-in real Docker probe requires trusted immutable image')
def test_opt_in_real_docker():
    evidence = _load_verifier().verify(os.environ['PDM_PARSER_SANDBOX_IMAGE'])
    assert evidence['timeout_cleanup']['absent_after_timeout']
    assert all(evidence['docker_inspect_flags'].values())
