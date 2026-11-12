import secrets
import pytest
from flask_migrate import upgrade,downgrade
from sqlalchemy import text
from app import db
from conftest import ROOT


def test_migration_refuses_open_application_transaction(app):
    with app.app_context():
        db.session.execute(text('SELECT id FROM pilot_jobs LIMIT 1'))
        with pytest.raises(SystemExit) as refusal:
            downgrade(directory=str(ROOT/'migrations_pilot'),revision='pilot_0002')
        assert refusal.value.code==1
        db.session.rollback()
        assert db.session.execute(text('SELECT version_num FROM alembic_version_pilot')).scalar_one()=='pilot_0003'
        db.session.rollback()


def test_migration_refuses_nonempty_unowned_schema(app):
    # A private schema in the disposable _test DB proves the legacy guard without touching any legacy DB.
    schema = 'guard_'+secrets.token_hex(6)
    with app.app_context():
        with db.engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            connection.execute(text(f'CREATE TABLE "{schema}".legacy_archive (id integer)'))
        from unittest.mock import patch
        engine = db.engine.execution_options(schema_translate_map=None)
        original_connect = engine.connect
        def isolated_connect():
            connection = original_connect()
            connection.execute(text(f'SET search_path TO "{schema}"'))
            connection.commit()
            return connection
        try:
            with patch.object(db.engine,'connect',side_effect=isolated_connect):
                with pytest.raises(SystemExit) as rejected:
                    upgrade(directory=str(ROOT/'migrations_pilot'))
                assert rejected.value.code==1
        finally:
            with original_connect() as connection:
                connection.execute(text('SET search_path TO public'))
                connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
                connection.commit()
