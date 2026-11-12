"""Run native checks with private isolated environment, never print credentials."""
import argparse
import importlib.util
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def runtime():
    spec = importlib.util.spec_from_file_location('pm_local_runtime', ROOT/'scripts/pilot/pm_runtime.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('kind', choices=['backend','e2e'])
    parser.add_argument('arguments', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    runner = runtime()
    config = runner.load_manifest()
    env = runner.environment(config, 'test_database_url')
    if args.kind == 'backend':
        env['PDM_TEST_DATABASE_URL'] = config['test_database_url']
        env['PDM_PARSER_SANDBOX_IMAGE'] = config['parser_image']
        command = [str(ROOT/'.venv/Scripts/python.exe'), '-m','pytest', *(args.arguments or ['tests/backend','-q'])]
        cwd = ROOT
    else:
        env['PDM_BROWSER_CHANNEL'] = 'msedge'
        env['PDM_E2E_URL'] = f"http://localhost:{config['web_port']}"
        env['PDM_MAILPIT_URL'] = f"http://127.0.0.1:{config['inbox_port']}"
        env['PDM_MANUAL_FIXTURE'] = str(ROOT/'.pilot/fixtures/manual-test-only.pdf')
        command = ['node', str(ROOT/'frontend/node_modules/@playwright/test/cli.js'),'test',*args.arguments]
        cwd = ROOT/'frontend'
    result = subprocess.run(command, cwd=cwd, env=env)
    sys.exit(result.returncode)


if __name__ == '__main__':
    main()
