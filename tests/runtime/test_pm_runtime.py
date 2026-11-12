"""No application/database fixtures: isolated runtime safety negative controls."""
import importlib.util
import os
from pathlib import Path
from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet

ROOT = Path(__file__).resolve().parents[2]


def module():
    spec = importlib.util.spec_from_file_location('runtime_under_test', ROOT/'scripts/pilot/pm_runtime.py')
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def fixture(runner):
    name = 'machivital_pm_'+'a'*12
    return dict(namespace=name, run_dir=str(ROOT/'.pilot'/name), secret_key='b'*64, mfa_key=Fernet.generate_key().decode(), api_port=5053,web_port=5174,smtp_port=11027,inbox_port=8027, parser_image=runner.PARSER_IMAGE,mail_image=runner.MAIL_IMAGE,mail_container=name+'-mail', **{key:'postgresql+psycopg://local:private@127.0.0.1:55432/'+name+suffix for key,suffix in [('database_url',''),('test_database_url','_test'),('restore_database_url','_restore')]})


def test_browser_rehearsal_allowance_is_only_in_disposable_runtime():
    runner = module()
    value = fixture(runner)
    from app import create_app
    with patch.dict(os.environ, {}, clear=True), patch.object(runner, 'environment', return_value={}), patch('app.create_app', return_value='isolated-app') as factory:
        assert runner.application(value, testing=True) == 'isolated-app'
    config = factory.call_args.args[0]
    assert config['AUTH_RATE_LIMIT'] == 500
    assert config['APP_ENV'] == 'development' and config['LOAD_PILOT_ENV'] is False
    # The public production factory is not changed by a local rehearsal setting.
    assert create_app is not factory


def test_runtime_refuses_original_restored_path_with_wrong_namespace():
    runner=module()
    value=fixture(runner)
    value['restore_database_url']=value['database_url']
    with pytest.raises(ValueError,match='unsafe database'):
        runner.validate_manifest(value)


def test_fresh_runtime_keys_are_not_copied_from_source_config():
    runner=module()
    value=fixture(runner)
    with patch.dict(os.environ,{'ANTHROPIC_API_KEY':'private-provider','CLAMAV_HOST':'remote.example','SMTP_HOST':'remote.example','DOCKER_HOST':'tcp://remote.example:2375'}), patch.object(runner.shutil,'which',return_value='C:/Program Files/Docker/docker.exe'):
        env=runner.environment(value)
        assert env['CLAMAV_HOST']=='127.0.0.1' and env['SMTP_HOST']=='127.0.0.1'
        assert not {'ANTHROPIC_API_KEY','DOCKER_HOST'} & env.keys()


def test_partial_provisioning_manifest_is_preserved_and_refused(tmp_path):
    runner = module()
    value = fixture(runner)
    value['preparation_state']='provisioning'
    with patch.object(runner,'private_path',return_value=tmp_path/'manifest.json'):
        import json
        (tmp_path/'manifest.json').write_text(json.dumps(value),encoding='utf-8')
        with pytest.raises(ValueError,match='Partial preparation'):
            runner.load_manifest(tmp_path/'manifest.json')


def test_disposable_targets_and_no_source_secret_export():
    runner = module()
    value = fixture(runner)
    with patch.dict(os.environ, {'SECRET_KEY':'original-key','OPENAI_API_KEY':'original-provider','AWS_ACCESS_KEY_ID':'original-aws','SMTP_PASSWORD':'original-smtp','STORAGE_BACKEND':'s3'}), patch.object(runner.shutil,'which',return_value='C:/Program Files/Docker/docker.exe'):
        env = runner.environment(value)
        assert env['SECRET_KEY'] == value['secret_key']
        assert env['STORAGE_BACKEND'] == 'local'
        assert not {'OPENAI_API_KEY','AWS_ACCESS_KEY_ID','SMTP_PASSWORD'} & env.keys()
        assert env['DATABASE_URL'].endswith(value['namespace'])
        assert env['SMTP_PORT']=='11027'
    assert runner.validate_manifest(value) is value


@pytest.mark.parametrize('change', [
    {'database_url':'postgresql+psycopg://local:private@127.0.0.1:55432/machivital_pilot'},
    {'test_database_url':'postgresql+psycopg://local:private@remote.example:55432/machivital_pm_aaaaaaaaaaaa_test'},
    {'namespace':'machivital_pilot'}, {'run_dir':str(ROOT/'instance')},
    {'smtp_port':5053}, {'parser_image':'python:latest'}, {'mail_container':'machivital-pilot-mail'},
])
def test_runtime_rejects_original_remote_mutable_or_shared_targets(change):
    runner = module()
    with pytest.raises((ValueError, KeyError)):
        runner.validate_manifest({**fixture(runner),**change})
