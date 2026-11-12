"""Initialize isolated maintenance pilot schema
Revision ID: pilot_0001
Revises: 
"""
from alembic import op
import sqlalchemy as sa

revision = 'pilot_0001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Frozen initial pilot schema; never imports application metadata.
    op.create_table('asset_templates',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('manufacturer', sa.String(length=100), nullable=True),
    sa.Column('version', sa.String(length=50), nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_asset_templates')),
    sa.UniqueConstraint('name', name=op.f('uq_asset_templates_name'))
    )
    op.create_table('companies',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('industry', sa.String(length=50), nullable=False),
    sa.Column('contact_email', sa.String(length=120), nullable=False),
    sa.Column('contact_phone', sa.String(length=20), nullable=True),
    sa.Column('address', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('timezone', sa.String(length=64), nullable=False),
    sa.Column('next_work_order', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_companies'))
    )
    op.create_table('event_log',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('timestamp', sa.DateTime(), nullable=False),
    sa.Column('machine_id', sa.String(length=100), nullable=False),
    sa.Column('event_type', sa.String(length=50), nullable=False),
    sa.Column('details', sa.Text(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_event_log'))
    )
    op.create_index('idx_event_time', 'event_log', ['timestamp'], unique=False)
    op.create_index('idx_machine_event', 'event_log', ['machine_id', 'event_type'], unique=False)
    op.create_table('machine_state',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('machine_id', sa.String(length=100), nullable=False),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('health_factor', sa.Float(), nullable=False),
    sa.Column('active_failure', sa.JSON(), nullable=True),
    sa.Column('event_steps_left', sa.Integer(), nullable=False),
    sa.Column('last_updated', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_machine_state')),
    sa.UniqueConstraint('machine_id', name=op.f('uq_machine_state_machine_id'))
    )
    op.create_table('pilot_jobs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('kind', sa.String(length=32), nullable=False),
    sa.Column('identity', sa.String(length=100), nullable=False),
    sa.Column('payload', sa.JSON(), nullable=False),
    sa.Column('state', sa.String(length=20), nullable=False),
    sa.Column('attempts', sa.Integer(), nullable=False),
    sa.Column('available_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('lease_until', sa.DateTime(timezone=True), nullable=True),
    sa.Column('lease_token', sa.String(length=64), nullable=True),
    sa.Column('error', sa.String(length=300), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_pilot_jobs')),
    sa.UniqueConstraint('identity', name=op.f('uq_pilot_jobs_identity'))
    )
    op.create_index('ix_pilot_jobs_claim', 'pilot_jobs', ['state', 'available_at'], unique=False)
    op.create_table('rate_buckets',
    sa.Column('key', sa.String(length=64), nullable=False),
    sa.Column('count', sa.Integer(), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('key', name=op.f('pk_rate_buckets'))
    )
    op.create_table('sensor_data',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('timestamp', sa.DateTime(), nullable=False),
    sa.Column('sensor_id', sa.String(length=100), nullable=False),
    sa.Column('value', sa.Float(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_sensor_data'))
    )
    op.create_index('idx_sensor_time', 'sensor_data', ['sensor_id', 'timestamp'], unique=False)
    op.create_index('idx_timestamp', 'sensor_data', ['timestamp'], unique=False)
    op.create_table('sensor_templates',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('unit', sa.String(length=20), nullable=True),
    sa.Column('data_type', sa.String(length=20), nullable=True),
    sa.Column('min_range', sa.Float(), nullable=True),
    sa.Column('max_range', sa.Float(), nullable=True),
    sa.Column('sampling_rate_hz', sa.Float(), nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_sensor_templates')),
    sa.UniqueConstraint('name', name=op.f('uq_sensor_templates_name'))
    )
    op.create_table('asset_template_sensors',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('asset_template_id', sa.Integer(), nullable=False),
    sa.Column('sensor_template_id', sa.Integer(), nullable=False),
    sa.Column('default_threshold_min', sa.Float(), nullable=True),
    sa.Column('default_threshold_max', sa.Float(), nullable=True),
    sa.ForeignKeyConstraint(['asset_template_id'], ['asset_templates.id'], name=op.f('fk_asset_template_sensors_asset_template_id_asset_templates')),
    sa.ForeignKeyConstraint(['sensor_template_id'], ['sensor_templates.id'], name=op.f('fk_asset_template_sensors_sensor_template_id_sensor_templates')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_asset_template_sensors'))
    )
    op.create_table('failure_mode_templates',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('asset_template_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('severity', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['asset_template_id'], ['asset_templates.id'], name=op.f('fk_failure_mode_templates_asset_template_id_asset_templates')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_failure_mode_templates'))
    )
    op.create_table('locations',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('company_id', sa.Integer(), nullable=False),
    sa.Column('parent_id', sa.Integer(), nullable=True),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('type', sa.String(length=50), nullable=False),
    sa.Column('path', sa.String(length=500), nullable=True),
    sa.CheckConstraint("type IN ('Site', 'Area', 'Line')", name=op.f('ck_locations_location_type')),
    sa.ForeignKeyConstraint(['company_id', 'parent_id'], ['locations.company_id', 'locations.id'], name=op.f('fk_locations_company_id_locations')),
    sa.ForeignKeyConstraint(['company_id'], ['companies.id'], name=op.f('fk_locations_company_id_companies')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_locations')),
    sa.UniqueConstraint('company_id', 'id', name=op.f('uq_locations_company_id_id'))
    )
    op.create_index(op.f('ix_locations_path'), 'locations', ['path'], unique=False)
    op.create_table('machines',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('machine_id', sa.String(length=50), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('machine_type', sa.String(length=50), nullable=False),
    sa.Column('manufacturer', sa.String(length=100), nullable=True),
    sa.Column('model', sa.String(length=100), nullable=True),
    sa.Column('serial_number', sa.String(length=100), nullable=True),
    sa.Column('installation_date', sa.DateTime(), nullable=True),
    sa.Column('location', sa.String(length=200), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=True),
    sa.Column('company_id', sa.Integer(), nullable=False),
    sa.Column('sensor_config', sa.JSON(), nullable=True),
    sa.Column('thresholds', sa.JSON(), nullable=True),
    sa.Column('maintenance_schedule', sa.JSON(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.Column('created_by', sa.String(length=100), nullable=True),
    sa.ForeignKeyConstraint(['company_id'], ['companies.id'], name=op.f('fk_machines_company_id_companies')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_machines')),
    sa.UniqueConstraint('machine_id', name=op.f('uq_machines_machine_id'))
    )
    op.create_table('maintenance_records',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('machine_id', sa.String(length=50), nullable=False),
    sa.Column('maintenance_type', sa.String(length=50), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('performed_by', sa.String(length=100), nullable=True),
    sa.Column('duration_hours', sa.Float(), nullable=True),
    sa.Column('cost', sa.Float(), nullable=True),
    sa.Column('parts_replaced', sa.JSON(), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('scheduled_date', sa.DateTime(), nullable=True),
    sa.Column('completed_date', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('company_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['company_id'], ['companies.id'], name=op.f('fk_maintenance_records_company_id_companies')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_maintenance_records'))
    )
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('username', sa.String(length=64), nullable=False),
    sa.Column('email', sa.String(length=120), nullable=False),
    sa.Column('password_hash', sa.String(length=255), nullable=True),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('email_verified_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('is_enabled', sa.Boolean(), nullable=False),
    sa.Column('totp_secret', sa.Text(), nullable=True),
    sa.Column('totp_last_counter', sa.BigInteger(), nullable=False),
    sa.Column('totp_pending_secret', sa.Text(), nullable=True),
    sa.Column('totp_pending_until', sa.DateTime(timezone=True), nullable=True),
    sa.Column('recovery_hashes', sa.JSON(), nullable=False),
    sa.Column('role', sa.String(length=20), nullable=True),
    sa.Column('company_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('last_login', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['company_id'], ['companies.id'], name=op.f('fk_users_company_id_companies')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_users')),
    sa.UniqueConstraint('email', name=op.f('uq_users_email')),
    sa.UniqueConstraint('username', name=op.f('uq_users_username'))
    )
    op.create_table('assets',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('asset_template_id', sa.Integer(), nullable=True),
    sa.Column('location_id', sa.Integer(), nullable=True),
    sa.Column('company_id', sa.Integer(), nullable=False),
    sa.Column('code', sa.String(length=64), nullable=False),
    sa.Column('manufacturer', sa.String(length=100), nullable=True),
    sa.Column('model', sa.String(length=100), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('criticality', sa.String(length=20), nullable=False),
    sa.Column('revision', sa.Integer(), nullable=False),
    sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('serial_number', sa.String(length=100), nullable=True),
    sa.Column('install_date', sa.DateTime(), nullable=True),
    sa.Column('status', sa.String(length=50), nullable=True),
    sa.CheckConstraint("criticality IN ('low', 'medium', 'high', 'critical')", name=op.f('ck_assets_asset_criticality')),
    sa.ForeignKeyConstraint(['asset_template_id'], ['asset_templates.id'], name=op.f('fk_assets_asset_template_id_asset_templates')),
    sa.ForeignKeyConstraint(['company_id', 'location_id'], ['locations.company_id', 'locations.id'], name=op.f('fk_assets_company_id_locations')),
    sa.ForeignKeyConstraint(['company_id'], ['companies.id'], name=op.f('fk_assets_company_id_companies')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_assets')),
    sa.UniqueConstraint('company_id', 'code', name=op.f('uq_assets_company_id_code')),
    sa.UniqueConstraint('company_id', 'id', name=op.f('uq_assets_company_id_id'))
    )
    op.create_table('auth_tokens',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('digest', sa.String(length=64), nullable=False),
    sa.Column('kind', sa.String(length=20), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('company_id', sa.Integer(), nullable=True),
    sa.Column('email', sa.String(length=120), nullable=False),
    sa.Column('role', sa.String(length=20), nullable=True),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('consumed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['company_id'], ['companies.id'], name=op.f('fk_auth_tokens_company_id_companies')),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_auth_tokens_user_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_auth_tokens')),
    sa.UniqueConstraint('digest', name=op.f('uq_auth_tokens_digest'))
    )
    op.create_table('idempotency_records',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('company_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('key', sa.String(length=128), nullable=False),
    sa.Column('digest', sa.String(length=64), nullable=False),
    sa.Column('response', sa.JSON(), nullable=True),
    sa.Column('status_code', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['company_id'], ['companies.id'], name=op.f('fk_idempotency_records_company_id_companies')),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_idempotency_records_user_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_idempotency_records')),
    sa.UniqueConstraint('company_id', 'user_id', 'key', name=op.f('uq_idempotency_records_company_id_user_id_key'))
    )
    op.create_table('memberships',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('company_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('role', sa.String(length=20), nullable=False),
    sa.Column('active', sa.Boolean(), nullable=False),
    sa.CheckConstraint("role IN ('owner','admin','planner','technician','stores','viewer')", name=op.f('ck_memberships_membership_role')),
    sa.ForeignKeyConstraint(['company_id'], ['companies.id'], name=op.f('fk_memberships_company_id_companies')),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_memberships_user_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_memberships')),
    sa.UniqueConstraint('company_id', 'id', name=op.f('uq_memberships_company_id_id')),
    sa.UniqueConstraint('company_id', 'user_id', name=op.f('uq_memberships_company_id_user_id'))
    )
    op.create_table('asset_sensors',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('asset_id', sa.Integer(), nullable=False),
    sa.Column('sensor_template_id', sa.Integer(), nullable=False),
    sa.Column('channel_id', sa.String(length=100), nullable=False),
    sa.Column('config_overrides', sa.JSON(), nullable=True),
    sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], name=op.f('fk_asset_sensors_asset_id_assets')),
    sa.ForeignKeyConstraint(['sensor_template_id'], ['sensor_templates.id'], name=op.f('fk_asset_sensors_sensor_template_id_sensor_templates')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_asset_sensors'))
    )
    op.create_table('auth_sessions',
    sa.Column('id', sa.String(length=64), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('membership_id', sa.Integer(), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['membership_id'], ['memberships.id'], name=op.f('fk_auth_sessions_membership_id_memberships')),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_auth_sessions_user_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_auth_sessions'))
    )
    op.create_table('documents',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('company_id', sa.Integer(), nullable=False),
    sa.Column('asset_id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('filename', sa.String(length=200), nullable=False),
    sa.Column('blob_key', sa.String(length=200), nullable=False),
    sa.Column('size', sa.Integer(), nullable=False),
    sa.Column('checksum', sa.String(length=64), nullable=False),
    sa.Column('status', sa.String(length=32), nullable=False),
    sa.Column('page_count', sa.Integer(), nullable=True),
    sa.Column('pages', sa.JSON(), nullable=True),
    sa.Column('error', sa.String(length=300), nullable=True),
    sa.Column('revision', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint("status IN ('quarantined','processing','ready','failed','deleted')", name=op.f('ck_documents_document_status')),
    sa.ForeignKeyConstraint(['company_id', 'asset_id'], ['assets.company_id', 'assets.id'], name=op.f('fk_documents_company_id_assets')),
    sa.ForeignKeyConstraint(['company_id'], ['companies.id'], name=op.f('fk_documents_company_id_companies')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_documents')),
    sa.UniqueConstraint('blob_key', name=op.f('uq_documents_blob_key'))
    )
    op.create_table('work_orders',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('company_id', sa.Integer(), nullable=False),
    sa.Column('asset_id', sa.Integer(), nullable=False),
    sa.Column('number', sa.String(length=32), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('priority', sa.String(length=20), nullable=False),
    sa.Column('status', sa.String(length=32), nullable=False),
    sa.Column('assignee_id', sa.Integer(), nullable=True),
    sa.Column('due_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('revision', sa.Integer(), nullable=False),
    sa.Column('notes', sa.Text(), nullable=False),
    sa.Column('completion_notes', sa.Text(), nullable=False),
    sa.Column('checklist', sa.JSON(), nullable=False),
    sa.Column('labor_minutes', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint("priority IN ('low','medium','high','urgent')", name=op.f('ck_work_orders_work_priority')),
    sa.CheckConstraint("status IN ('open','assigned','in_progress','blocked','awaiting_review','completed','cancelled')", name=op.f('ck_work_orders_work_status')),
    sa.CheckConstraint('labor_minutes >= 0', name=op.f('ck_work_orders_work_labor')),
    sa.ForeignKeyConstraint(['company_id', 'asset_id'], ['assets.company_id', 'assets.id'], name=op.f('fk_work_orders_company_id_assets')),
    sa.ForeignKeyConstraint(['company_id', 'assignee_id'], ['memberships.company_id', 'memberships.id'], name=op.f('fk_work_orders_company_id_memberships')),
    sa.ForeignKeyConstraint(['company_id'], ['companies.id'], name=op.f('fk_work_orders_company_id_companies')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_work_orders')),
    sa.UniqueConstraint('company_id', 'id', name=op.f('uq_work_orders_company_id_id')),
    sa.UniqueConstraint('company_id', 'number', name=op.f('uq_work_orders_company_id_number'))
    )
    op.create_table('work_events',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('company_id', sa.Integer(), nullable=False),
    sa.Column('work_order_id', sa.Integer(), nullable=False),
    sa.Column('actor_id', sa.Integer(), nullable=False),
    sa.Column('actor_name', sa.String(length=100), nullable=False),
    sa.Column('action', sa.String(length=32), nullable=False),
    sa.Column('from_status', sa.String(length=32), nullable=True),
    sa.Column('to_status', sa.String(length=32), nullable=False),
    sa.Column('notes', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['actor_id'], ['users.id'], name=op.f('fk_work_events_actor_id_users')),
    sa.ForeignKeyConstraint(['company_id', 'work_order_id'], ['work_orders.company_id', 'work_orders.id'], name=op.f('fk_work_events_company_id_work_orders')),
    sa.ForeignKeyConstraint(['company_id'], ['companies.id'], name=op.f('fk_work_events_company_id_companies')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_work_events'))
    )
    

def downgrade():
    # Frozen initial pilot schema; never imports application metadata.
    op.drop_table('work_events')
    op.drop_table('work_orders')
    op.drop_table('documents')
    op.drop_table('auth_sessions')
    op.drop_table('asset_sensors')
    op.drop_table('memberships')
    op.drop_table('idempotency_records')
    op.drop_table('auth_tokens')
    op.drop_table('assets')
    op.drop_table('users')
    op.drop_table('maintenance_records')
    op.drop_table('machines')
    op.drop_index(op.f('ix_locations_path'), table_name='locations')
    op.drop_table('locations')
    op.drop_table('failure_mode_templates')
    op.drop_table('asset_template_sensors')
    op.drop_table('sensor_templates')
    op.drop_index('idx_timestamp', table_name='sensor_data')
    op.drop_index('idx_sensor_time', table_name='sensor_data')
    op.drop_table('sensor_data')
    op.drop_table('rate_buckets')
    op.drop_index('ix_pilot_jobs_claim', table_name='pilot_jobs')
    op.drop_table('pilot_jobs')
    op.drop_table('machine_state')
    op.drop_index('idx_machine_event', table_name='event_log')
    op.drop_index('idx_event_time', table_name='event_log')
    op.drop_table('event_log')
    op.drop_table('companies')
    op.drop_table('asset_templates')
    
