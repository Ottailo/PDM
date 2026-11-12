"""Fail-closed, fixed-command PDF containment; no Flask factory/worker imports.

The Docker daemon and configured immutable image are trusted administrative
boundaries. Never give the API/worker an unrestricted rootful Docker socket in
production. A rootless daemon is required outside explicit local environments.
"""
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import uuid

from flask import current_app


class ParserRejected(Exception):
    """Permanent document rejection (worker should leave it quarantined)."""


class ParserUnavailable(Exception):
    """Containment/configuration failure; worker may retry, never fall back."""


class _OutputLimit(Exception):
    pass


class _Deadline(Exception):
    pass


_ROOT = Path(__file__).resolve().parents[2]
_PARSER = _ROOT / 'sandbox' / 'pdf' / 'parser.py'
_IMAGE_ID = re.compile(r'sha256:[0-9a-f]{64}\Z')
_IMAGE_DIGEST = re.compile(r'[a-z0-9][a-z0-9./:_-]*@sha256:[0-9a-f]{64}\Z')
_ENTRYPOINT = ['python3', '-I', '/parser/parser.py']
_ENV_KEYS = {'SYSTEMROOT', 'WINDIR', 'PATH', 'HOME', 'USERPROFILE', 'LANG', 'TEMP', 'TMP'}


def _environment():
    # No application secrets, DOCKER_HOST, DOCKER_* flags, or Python overrides.
    return {key: value for key, value in os.environ.items() if key.upper() in _ENV_KEYS}


def _bounded_process(args, content=b'', *, timeout=10, stdout_limit=65536, stderr_limit=8192, cwd=None):
    """Drain pipes incrementally, terminating before an untrusted output can grow.

    Threads work with Windows anonymous pipes too. Both buffers are hard-bounded;
    a deadline also bounds stdin writes. Containers are separately removed by the
    caller: killing a docker CLI alone is NOT a containment cleanup operation.
    """
    try:
        process = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, shell=False, cwd=cwd or str(_ROOT),
                                   env=_environment())
    except OSError as error:
        raise ParserUnavailable('Parser executable could not be started') from error
    buffers = [bytearray(), bytearray()]
    exceeded = threading.Event()
    pipe_failed = threading.Event()

    def read(pipe, destination, limit):
        try:
            while True:
                chunk = pipe.read(8192)
                if not chunk:
                    return
                room = limit - len(destination)
                destination.extend(chunk[:max(0, room)])
                if len(chunk) > room:
                    exceeded.set()
                    return
        except (OSError, ValueError):
            pipe_failed.set()
        finally:
            pipe.close()

    def write():
        try:
            for offset in range(0, len(content), 65536):
                process.stdin.write(content[offset:offset + 65536])
            process.stdin.flush()
        except (BrokenPipeError, OSError, ValueError):
            # Early parser rejection can legitimately stop reading stdin.
            pass
        finally:
            try:
                process.stdin.close()
            except OSError:
                pass

    threads = [threading.Thread(target=read, args=(process.stdout, buffers[0], stdout_limit), daemon=True),
               threading.Thread(target=read, args=(process.stderr, buffers[1], stderr_limit), daemon=True),
               threading.Thread(target=write, daemon=True)]
    for thread in threads:
        thread.start()
    deadline = time.monotonic() + timeout
    failure = None
    try:
        while process.poll() is None or any(thread.is_alive() for thread in threads):
            if exceeded.is_set():
                failure = _OutputLimit('Parser output exceeds limits')
                break
            if time.monotonic() >= deadline:
                failure = _Deadline('Parser deadline exceeded')
                break
            exceeded.wait(min(0.02, max(0, deadline - time.monotonic())))
        if exceeded.is_set():
            failure = _OutputLimit('Parser output exceeds limits')
        if failure:
            raise failure
        if pipe_failed.is_set():
            raise ParserUnavailable('Parser pipe failed')
        return process.returncode, bytes(buffers[0]), bytes(buffers[1])
    finally:
        if process.poll() is None:
            process.kill()
        process.wait(timeout=5)
        for thread in threads:
            thread.join(timeout=1)


def _control(executable, args, *, limit=65536):
    try:
        code, output, _ = _bounded_process([executable, *args], stdout_limit=limit)
    except (_Deadline, _OutputLimit) as error:
        raise ParserUnavailable('Docker control operation exceeded limits') from error
    if code:
        raise ParserUnavailable('Docker control operation failed')
    return output


def _docker_executable(config):
    configured = config.get('PDF_DOCKER_EXECUTABLE')
    path = Path(configured) if isinstance(configured, str) and configured and configured != 'docker' else None
    if path is not None:
        if not path.is_absolute() or path.name.lower() not in {'docker', 'docker.exe'} or not path.is_file():
            raise ParserUnavailable('PDF_DOCKER_EXECUTABLE must be a fixed absolute Docker executable')
    else:
        resolved = shutil.which('docker')
        if not resolved:
            raise ParserUnavailable('Docker parser runtime is unavailable')
        path = Path(resolved)
    return str(path.resolve())


def _json_control(executable, args, *, limit=65536):
    try:
        return json.loads(_control(executable, args, limit=limit))
    except (ValueError, UnicodeError) as error:
        raise ParserUnavailable('Docker returned invalid metadata') from error


def _resolve_image(executable, image, environment):
    if not isinstance(image, str) or not (_IMAGE_ID.fullmatch(image) or _IMAGE_DIGEST.fullmatch(image)):
        raise ParserUnavailable('PDF_PARSER_IMAGE must be a trusted immutable sha256 image ID or repository digest')
    info = _json_control(executable, ['info', '--format', '{{json .}}'])
    if not isinstance(info, dict) or info.get('OSType') != 'linux':
        raise ParserUnavailable('PDF parser requires a Linux Docker runtime')
    security = info.get('SecurityOptions') or []
    if not isinstance(security, list) or not any(isinstance(value, str) and value.startswith('name=seccomp') for value in security):
        raise ParserUnavailable('PDF parser requires Docker seccomp containment')
    if environment not in {'development', 'test'} and 'name=rootless' not in security:
        raise ParserUnavailable('Production PDF parsing requires a rootless/restricted Docker runtime')
    inspected = _json_control(executable, ['image', 'inspect', image])
    if not isinstance(inspected, list) or len(inspected) != 1 or not isinstance(inspected[0], dict):
        raise ParserUnavailable('Configured parser image is unavailable')
    metadata = inspected[0]
    identity = metadata.get('Id', '')
    configuration = metadata.get('Config') or {}
    if not isinstance(identity, str) or not _IMAGE_ID.fullmatch(identity) or metadata.get('Os') != 'linux':
        raise ParserUnavailable('Invalid parser image identity')
    if _IMAGE_ID.fullmatch(image) and identity != image:
        raise ParserUnavailable('Parser image identity did not match configuration')
    if _IMAGE_DIGEST.fullmatch(image) and image not in (metadata.get('RepoDigests') or []):
        raise ParserUnavailable('Parser image repository digest did not match configuration')
    if (configuration.get('Entrypoint') != _ENTRYPOINT or configuration.get('Cmd') not in (None, [])
            or configuration.get('User') != '65532:65532' or configuration.get('WorkingDir') != '/parser'
            or configuration.get('Volumes')):
        raise ParserUnavailable('Configured image does not match the fixed parser contract')
    return identity


def _container_args(name, image, max_bytes, max_pages, max_text):
    """Fixed production arguments; no command, mounts, environment, or user flags."""
    return ['create', '--name', name, '--pull', 'never', '--interactive',
            '--network', 'none', '--user', '65532:65532', '--read-only',
            '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges=true',
            '--pids-limit', '32', '--memory', '384m', '--memory-swap', '384m',
            '--cpus', '1', '--tmpfs', '/tmp:rw,noexec,nosuid,nodev,size=16m,mode=1777',
            # Docker's default PID mode is private; --pid=private is not valid.
            '--ipc', 'private', '--cgroupns', 'private',
            '--ulimit', 'nofile=64:64', '--ulimit', 'core=0:0',
            '--log-driver', 'none', '--restart', 'no',
            image, str(max_bytes), str(max_pages), str(max_text)]


def _remove_container(executable, name):
    # Forced removal kills the actual workload, not merely its attached CLI.
    _control(executable, ['rm', '--force', name])
    remaining = _control(executable, ['container', 'ls', '--all', '--filter', f'name=^/{name}$', '--format', '{{.Names}}'])
    if remaining.strip():
        raise ParserUnavailable('Parser container cleanup was not confirmed')


def _limits(config):
    values = []
    for key, ceiling in [('PDF_MAX_BYTES', 10 * 1024 * 1024), ('PDF_MAX_PAGES', 200), ('PDF_MAX_TEXT', 1000000)]:
        value = config.get(key)
        if type(value) is not int or not 1 <= value <= ceiling:
            raise ParserUnavailable(f'{key} must be within the fixed parser ceiling')
        values.append(value)
    timeout = config.get('PDF_PARSE_TIMEOUT')
    if isinstance(timeout, bool) or not isinstance(timeout, (float, int)) or not math.isfinite(timeout) or not 0 < timeout <= 60:
        raise ParserUnavailable('PDF_PARSE_TIMEOUT must be positive and at most 60 seconds')
    return (*values, timeout)


def _validate_output(code, output, max_pages, max_text):
    try:
        result = json.loads(output)
    except (ValueError, UnicodeError) as error:
        raise ParserRejected('PDF could not be parsed safely') from error
    if not isinstance(result, dict):
        raise ParserRejected('Parser returned invalid output')
    if code or 'error' in result:
        # Only fixed policy messages may leave the sandbox; ignore arbitrary text.
        allowed = {'Encrypted PDFs are not supported', 'PDF exceeds the page limit',
                   'PDF active content is not supported', 'PDF object graph exceeds processing limits',
                   'PDF extracted text exceeds processing limits', 'PDF exceeds the byte limit',
                   'Empty PDF', 'Invalid PDF signature', 'PDF could not be parsed safely'}
        message = result.get('error')
        raise ParserRejected(message if isinstance(message, str) and message in allowed else 'PDF could not be parsed safely')
    pages = result.get('pages')
    if (set(result) != {'pages'} or not isinstance(pages, list) or not 1 <= len(pages) <= max_pages
            or any(not isinstance(page, str) or len(page) > 100000 for page in pages)
            or sum(map(len, pages)) > max_text):
        raise ParserRejected('Parser returned invalid or oversized output')
    return pages


def parse_pdf(content):
    """Return validated page text, or raise ParserRejected / ParserUnavailable.

    Docker is the default and has no subprocess fallback. The explicit development
    mode is a diagnostic-only subprocess and is forbidden when APP_ENV is production
    (even when TESTING is true). ClamAV approval must precede this call in the worker.
    """
    config = current_app.config
    max_bytes, max_pages, max_text, timeout = _limits(config)
    if not isinstance(content, bytes) or not content or len(content) > max_bytes:
        raise ParserRejected('PDF exceeds the byte limit or is empty')
    mode = config.get('PDF_PARSER_MODE', 'docker')
    environment = config.get('APP_ENV', 'production')
    if environment not in {'production', 'development', 'test'}:
        raise ParserUnavailable('Unknown parser application environment')
    stdout_limit = max_text * 6 + max_pages * 4 + 100
    if mode == 'development':
        if environment not in {'development', 'test'}:
            raise ParserUnavailable('Development PDF parser is forbidden in production')
        try:
            with tempfile.TemporaryDirectory(prefix='machivital-pdf-dev-') as directory:
                code, output, _ = _bounded_process(
                    [sys.executable, '-I', str(_PARSER), str(max_bytes), str(max_pages), str(max_text)],
                    content, timeout=timeout, stdout_limit=stdout_limit, cwd=directory)
        except _OutputLimit as error:
            raise ParserRejected('Parser output exceeds limits') from error
        except _Deadline as error:
            raise ParserRejected('PDF processing deadline exceeded') from error
    elif mode == 'docker':
        executable = _docker_executable(config)
        image = _resolve_image(executable, config.get('PDF_PARSER_IMAGE'), environment)
        name = 'machivital-pdf-' + uuid.uuid4().hex
        # Separate create/start means the workload is already identified before
        # stdin/timeout handling begins. Always force-remove even on failed create.
        created = False
        try:
            _control(executable, _container_args(name, image, max_bytes, max_pages, max_text))
            created = True
            try:
                code, output, _ = _bounded_process([executable, 'start', '--attach', '--interactive', name],
                                                   content, timeout=timeout, stdout_limit=stdout_limit)
            except _OutputLimit as error:
                raise ParserRejected('Parser output exceeds limits') from error
            except _Deadline as error:
                raise ParserRejected('PDF processing deadline exceeded') from error
            if code not in {0, 1}:
                raise ParserUnavailable('Parser container could not complete')
        finally:
            if created:
                _remove_container(executable, name)
            else:
                # A create control timeout may still have created the named container.
                names = _control(executable, ['container', 'ls', '--all', '--filter', f'name=^/{name}$', '--format', '{{.Names}}'])
                if names.strip():
                    _remove_container(executable, name)
    else:
        raise ParserUnavailable('Unknown PDF parser mode; no fallback is permitted')
    return _validate_output(code, output, max_pages, max_text)
