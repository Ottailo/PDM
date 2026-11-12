"""Bounded identity, upload admission and worker scheduling remediation.

Revision ID: pilot_0002
Revises: pilot_0001
"""
from alembic import op
import sqlalchemy as sa

revision = 'pilot_0002'
down_revision = 'pilot_0001'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('memberships', sa.Column('revision', sa.Integer(), nullable=False, server_default='1'))
    op.add_column('auth_sessions', sa.Column('access_confirmed_at', sa.DateTime(timezone=True)))
    op.add_column('documents', sa.Column('staging_token', sa.String(64)))
    op.add_column('documents', sa.Column('staging_until', sa.DateTime(timezone=True)))
    op.add_column('documents', sa.Column('storage_released_at', sa.DateTime(timezone=True)))
    op.drop_constraint(op.f('ck_documents_document_status'), 'documents', type_='check')
    op.create_check_constraint('document_status', 'documents', "status IN ('staging','quarantined','processing','ready','failed','deleted')")
    op.add_column('pilot_jobs', sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id')))
    op.add_column('pilot_jobs', sa.Column('token_id', sa.Integer(), sa.ForeignKey('auth_tokens.id')))
    # Parse only exact frozen identity forms. Never infer a default tenant or trust JSON.
    op.execute("""UPDATE pilot_jobs j SET company_id=d.company_id
                  FROM documents d WHERE j.kind='document'
                  AND j.identity ~ '^document:[0-9]+:[0-9]+$'
                  AND split_part(j.identity, ':', 2)=d.id::text
                  AND (j.state IN ('done','cancelled') OR
                       (j.payload->>'document_id'=d.id::text
                        AND j.payload->>'revision'=split_part(j.identity, ':', 3)))""")
    op.execute("""UPDATE pilot_jobs j SET token_id=t.id, company_id=t.company_id
                  FROM auth_tokens t WHERE j.kind='mail'
                  AND j.identity='auth-token:'||t.id::text
                  AND (j.state='done' OR j.payload->>'to'=t.email)""")
    op.execute("""UPDATE pilot_jobs SET state='quarantined', error='Job provenance could not be verified',
                  payload='{}', lease_until=NULL, lease_token=NULL
                  WHERE (kind='document' AND company_id IS NULL)
                     OR (kind='mail' AND token_id IS NULL) OR kind NOT IN ('mail','document')""")
    op.create_table('tenant_schedules',
                    sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id'), primary_key=True),
                    sa.Column('last_dispatched_at', sa.DateTime(timezone=True)))
    op.execute('INSERT INTO tenant_schedules(company_id) SELECT id FROM companies')
    op.create_table('worker_schedules', sa.Column('id', sa.Integer(), primary_key=True), sa.Column('last_kind', sa.String(32)))
    op.execute('INSERT INTO worker_schedules(id) VALUES (1)')
    op.create_table('access_audits',
                    sa.Column('id', sa.Integer(), primary_key=True),
                    sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id'), nullable=False),
                    sa.Column('actor_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
                    sa.Column('target_id', sa.Integer(), sa.ForeignKey('users.id')),
                    sa.Column('membership_id', sa.Integer(), sa.ForeignKey('memberships.id')),
                    sa.Column('invitation_id', sa.Integer(), sa.ForeignKey('auth_tokens.id')),
                    sa.Column('action', sa.String(32), nullable=False),
                    sa.Column('old_role', sa.String(20)), sa.Column('new_role', sa.String(20)),
                    sa.Column('old_active', sa.Boolean()), sa.Column('new_active', sa.Boolean()),
                    sa.Column('reason', sa.String(1000), nullable=False),
                    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False))
    # Append-only even if a future application path accidentally mutates history.
    op.execute("""CREATE FUNCTION pilot_access_audit_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
                  BEGIN RAISE EXCEPTION 'Access audit history is append-only'; END $$""")
    op.execute("""CREATE TRIGGER access_audit_immutable BEFORE UPDATE OR DELETE ON access_audits
                  FOR EACH ROW EXECUTE FUNCTION pilot_access_audit_immutable()""")


def downgrade():
    connection = op.get_bind()
    unsafe = connection.execute(sa.text("""SELECT EXISTS(SELECT 1 FROM access_audits)
                    OR EXISTS(SELECT 1 FROM pilot_jobs WHERE state IN ('staging','queued','running','quarantined'))
                    OR EXISTS(SELECT 1 FROM documents WHERE staging_token IS NOT NULL OR status='staging')""")).scalar()
    if unsafe:
        raise RuntimeError('Downgrade refused: active/staging/quarantined jobs or access audit evidence must be preserved')
    op.drop_table('access_audits')
    op.execute('DROP FUNCTION pilot_access_audit_immutable()')
    op.drop_table('worker_schedules')
    op.drop_table('tenant_schedules')
    op.drop_column('pilot_jobs', 'token_id')
    op.drop_column('pilot_jobs', 'company_id')
    op.drop_constraint(op.f('ck_documents_document_status'), 'documents', type_='check')
    op.create_check_constraint('document_status', 'documents', "status IN ('quarantined','processing','ready','failed','deleted')")
    for name in ('storage_released_at', 'staging_until', 'staging_token'):
        op.drop_column('documents', name)
    op.drop_column('auth_sessions', 'access_confirmed_at')
    op.drop_column('memberships', 'revision')
