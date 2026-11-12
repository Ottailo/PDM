"""Separate migration lineage for an explicitly empty PostgreSQL pilot database."""
from alembic import context
from flask import current_app
from sqlalchemy import inspect

config = context.config
target_metadata = current_app.extensions['migrate'].db.metadata
VERSION_TABLE = 'alembic_version_pilot'


def run_migrations_offline():
    context.configure(url=current_app.config['SQLALCHEMY_DATABASE_URI'],target_metadata=target_metadata,literal_binds=True,version_table=VERSION_TABLE,compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    database = current_app.extensions['migrate'].db
    # Alembic uses another connection: an open application transaction can hold
    # relation locks and make this process wait forever on its own session.
    if database.session().in_transaction():
        raise RuntimeError('Close the application transaction before running migrations')
    engine = database.engine
    if engine.dialect.name!='postgresql':
        raise RuntimeError('Pilot migrations require PostgreSQL')
    with engine.connect() as connection:
        from sqlalchemy import text
        connection.execute(text("SET lock_timeout = '5s'"))
        connection.commit()
        tables = inspect(connection).get_table_names()
        # No stamping/import of the legacy schema. Only this new lineage may own this DB.
        if VERSION_TABLE not in tables and any(t!=VERSION_TABLE for t in tables):
            raise RuntimeError('Refusing to initialize pilot lineage in a nonempty database')
        connection.rollback()
        context.configure(connection=connection,target_metadata=target_metadata,version_table=VERSION_TABLE,compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
