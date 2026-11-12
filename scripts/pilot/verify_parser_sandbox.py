"""Independent real-Docker containment probes; no DB or application factory.

Run with python -I and --image <trusted immutable ID>. Test command overrides
exist only inside this script, never in the production parser API. Evidence is
configuration/syscall observations on a trusted Docker host, not a kernel audit.
"""
import argparse
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import secrets
import tempfile
import uuid

from flask import Flask
from pypdf import PdfWriter
from pypdf.actions import JavaScript
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject

ROOT = Path(__file__).resolve().parents[2]


def load_runner():
    spec = importlib.util.spec_from_file_location('parser_sandbox_under_test', ROOT / 'app/pilot/sandbox_runner.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture(kind='valid'):
    writer = PdfWriter()
    page = writer.add_blank_page(width=300, height=200)
    font = DictionaryObject({NameObject('/Type'): NameObject('/Font'),
                             NameObject('/Subtype'): NameObject('/Type1'),
                             NameObject('/BaseFont'): NameObject('/Helvetica')})
    page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): writer._add_object(font)})})
    stream = DecodedStreamObject()
    stream.set_data(b'BT /F1 12 Tf 20 100 Td (TESTONLY42) Tj ET')
    page[NameObject('/Contents')] = writer._add_object(stream)
    if kind == 'active':
        writer.add_open_action(JavaScript("app.alert('TESTONLY42')"))
    elif kind == 'encrypted':
        writer.encrypt('test-only-password')
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


# This is fixed verification code, not a callable production command option.
PROBE = r'''
import errno,json,os,socket
from pathlib import Path
payload=json.loads(__import__('sys').stdin.read())
status=dict(line.split(':',1) for line in Path('/proc/self/status').read_text().splitlines() if ':' in line)
root_denied=False
try:
    Path('/root-write-probe').write_text('denied')
except OSError as error:
    root_denied=error.errno==errno.EROFS
network_denied=False
try:
    with socket.socket() as connection:
        connection.settimeout(2)
        connection.connect(('1.1.1.1',443))
except OSError as error:
    network_denied=error.errno in (errno.ENETUNREACH,errno.EACCES,errno.EPERM,errno.EHOSTUNREACH)
print(json.dumps({
 'uid':os.getuid(),'gid':os.getgid(),
 'caps_zero':all(int(status[key].strip(),16)==0 for key in ('CapInh','CapPrm','CapEff','CapBnd','CapAmb')),
 'no_new_privs':status['NoNewPrivs'].strip()=='1',
 'seccomp':status['Seccomp'].strip()=='2',
 'network_connect_denied':network_denied,'root_readonly_denied':root_denied,
 'sentinels_absent':all(not Path(path).exists() for path in payload['paths']),
 'private_env_absent':payload['env_key'] not in os.environ,
 'socket_absent':all(not Path(path).exists() for path in ('/var/run/docker.sock','/run/docker.sock')),
 'pypdf_version':__import__('pypdf').__version__
}))
'''


def test_command(runner, name, image, code):
    args = runner._container_args(name, image, 10485760, 200, 1000000)
    # Replace only the entrypoint and fixed image argument tail in THIS script.
    return [*args[:-4], '--entrypoint', 'python3', image, '-I', '-c', code]


def assert_flags(metadata):
    host = metadata['HostConfig']
    config = metadata['Config']
    checks = {
        'network_none': host['NetworkMode'] == 'none',
        'nonroot': config['User'] == '65532:65532',
        'readonly': host['ReadonlyRootfs'] is True,
        'caps_dropped': host['CapDrop'] == ['ALL'] and not host['CapAdd'],
        'no_new_privileges': 'no-new-privileges=true' in host['SecurityOpt'],
        'pids32': host['PidsLimit'] == 32,
        'memory384m_no_swap': host['Memory'] == 384 * 1024 * 1024 and host['MemorySwap'] == host['Memory'],
        'cpu1': host['NanoCpus'] == 1000000000,
        'private_namespaces': host['IpcMode'] == 'private' and host['PidMode'] == '' and host['CgroupnsMode'] == 'private',
        'private_tmpfs': host['Tmpfs'] == {'/tmp': 'rw,noexec,nosuid,nodev,size=16m,mode=1777'},
        'no_host_mounts': not host['Binds'] and not metadata['Mounts'] and not config.get('Volumes'),
        'no_privileged_devices': not host['Privileged'] and not host['Devices'] and not host.get('DeviceRequests'),
        'logs_disabled': host['LogConfig']['Type'] == 'none',
    }
    assert all(checks.values()), checks
    return checks


def verify(image):
    runner = load_runner()
    executable = runner._docker_executable({})
    identity = runner._resolve_image(executable, image, 'test')
    app = Flask('sandbox-verifier')
    app.config.update(APP_ENV='test', TESTING=True, PDF_PARSER_MODE='docker', PDF_PARSER_IMAGE=identity,
                      PDF_MAX_BYTES=10485760, PDF_MAX_PAGES=200, PDF_MAX_TEXT=1000000, PDF_PARSE_TIMEOUT=25)
    evidence = {'image_id': identity, 'runtime': runner._json_control(executable, ['info', '--format', '{{json .SecurityOptions}}'])}
    with tempfile.TemporaryDirectory(prefix='machivital-host-sentinel-') as directory:
        host = Path(directory) / 'host-sentinel'
        private = Path(directory) / 'private-storage' / 'document-sentinel'
        private.parent.mkdir()
        host.write_text(secrets.token_hex(16))
        private.write_text(secrets.token_hex(16))
        env_key = 'MACHIVITAL_PRIVATE_PROBE_' + secrets.token_hex(8).upper()
        os.environ[env_key] = secrets.token_hex(16)
        name = 'machivital-pdf-probe-' + uuid.uuid4().hex
        try:
            runner._control(executable, test_command(runner, name, identity, PROBE))
            metadata = runner._json_control(executable, ['container', 'inspect', name])[0]
            evidence['docker_inspect_flags'] = assert_flags(metadata)
            assert not any(item.startswith(env_key + '=') for item in metadata['Config']['Env'])
            payload = json.dumps({'paths': [str(host), str(private), '/private-storage/' + private.name], 'env_key': env_key}).encode()
            code, output, _ = runner._bounded_process([executable, 'start', '--attach', '--interactive', name], payload, timeout=15)
            assert code == 0, code
            result = json.loads(output)
            assert result['uid'] == result['gid'] == 65532, result
            assert result['pypdf_version'] == '7.0.1', result
            assert all(result[key] is True for key in ('caps_zero', 'no_new_privs', 'seccomp', 'network_connect_denied', 'root_readonly_denied', 'sentinels_absent', 'private_env_absent', 'socket_absent')), result
            evidence['syscall_probes'] = result
            assert host.exists() and private.exists()
        finally:
            del os.environ[env_key]
            runner._remove_container(executable, name)
    with app.app_context():
        valid = fixture()
        pages = runner.parse_pdf(valid)
        assert len(pages) == 1 and 'TESTONLY42' in pages[0], pages
        evidence['valid_fixture'] = {'sha256': hashlib.sha256(valid).hexdigest(), 'page_count': len(pages), 'text': pages[0]}
        rejections = {}
        for kind, content in [('active', fixture('active')), ('encrypted', fixture('encrypted')), ('malformed', b'%PDF-1.7\ninvalid')]:
            try:
                runner.parse_pdf(content)
            except runner.ParserRejected as error:
                rejections[kind] = str(error)
            else:
                raise AssertionError(f'{kind} PDF was not rejected')
        evidence['rejections'] = rejections
        # Fixed test-only override executes a sleeping workload through the REAL
        # parse_pdf timeout/finally path, proving workload removal, not CLI kill.
        original = runner._container_args
        timed_names = []

        def sleeper(name, image, *_limits):
            timed_names.append(name)
            return test_command_original(name, image)

        def test_command_original(name, image):
            args = original(name, image, 10485760, 200, 1000000)
            return [*args[:-4], '--entrypoint', 'python3', image, '-I', '-c', 'import time; time.sleep(60)']

        runner._container_args = sleeper
        app.config['PDF_PARSE_TIMEOUT'] = 0.5
        try:
            try:
                runner.parse_pdf(valid)
            except runner.ParserRejected as error:
                assert 'deadline' in str(error), str(error)
            else:
                raise AssertionError('Sleeping container was not timed out')
        finally:
            runner._container_args = original
            app.config['PDF_PARSE_TIMEOUT'] = 25
        assert len(timed_names) == 1
        remaining = runner._control(executable, ['container', 'ls', '--all', '--filter', 'name=^/' + timed_names[0] + '$', '--format', '{{.Names}}'])
        assert not remaining.strip()
        evidence['timeout_cleanup'] = {'container': timed_names[0], 'absent_after_timeout': True}
        app.config['APP_ENV'] = 'production'
        if 'name=rootless' not in evidence['runtime']:
            try:
                runner.parse_pdf(valid)
            except runner.ParserUnavailable as error:
                assert 'rootless' in str(error)
                evidence['production_rootful_failclosed'] = str(error)
            else:
                raise AssertionError('Production accepted a rootful daemon')
    evidence['boundary'] = 'Trusted configured image/host only; no kernel, runtime escape, or daemon authorization certification.'
    return evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', required=True, help='Locally available trusted immutable image ID or repository digest')
    args = parser.parse_args()
    print(json.dumps(verify(args.image), indent=2))


if __name__ == '__main__':
    main()
