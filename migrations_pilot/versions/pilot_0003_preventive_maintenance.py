"""Durable local anchored preventive maintenance, reminders and truthful provenance.

Revision ID: pilot_0003
Revises: pilot_0002
Frozen migrations 0001/0002 remain untouched.
"""
from alembic import op
import sqlalchemy as sa

revision = 'pilot_0003'
down_revision = 'pilot_0002'
branch_labels = None
depends_on = None


def tenant():
    return sa.Column('company_id',sa.Integer(),sa.ForeignKey('companies.id'),nullable=False)


def stamp():
    return sa.Column('created_at',sa.DateTime(timezone=True),nullable=False)


def upgrade():
    op.add_column('worker_schedules',sa.Column('rotation_cursor',sa.Integer(),nullable=False,server_default='0'))
    op.create_table('maintenance_plans',
        sa.Column('id',sa.Integer(),primary_key=True),tenant(),
        sa.Column('asset_id',sa.Integer(),nullable=False),sa.Column('title',sa.String(200),nullable=False),
        sa.Column('description',sa.Text(),nullable=False),sa.Column('priority',sa.String(20),nullable=False),
        sa.Column('assignee_id',sa.Integer()),sa.Column('checklist',sa.JSON(),nullable=False),
        sa.Column('timezone',sa.String(64),nullable=False),sa.Column('start_local',sa.String(16),nullable=False),
        sa.Column('interval_unit',sa.String(10),nullable=False),sa.Column('interval_count',sa.Integer(),nullable=False),
        sa.Column('reminder_hours',sa.Integer(),nullable=False),sa.Column('escalation_member_id',sa.Integer()),
        sa.Column('enabled',sa.Boolean(),nullable=False),sa.Column('revision',sa.Integer(),nullable=False),
        sa.Column('generation',sa.Integer(),nullable=False),sa.Column('effective_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('next_index',sa.Integer(),nullable=False),sa.Column('next_due_at',sa.DateTime(timezone=True)),
        sa.Column('next_due_local',sa.String(16)),sa.Column('paused_at',sa.DateTime(timezone=True)),
        sa.Column('blocked_reason',sa.String(100)),sa.Column('last_tick_at',sa.DateTime(timezone=True)),stamp(),
        sa.UniqueConstraint('company_id','id'),
        sa.ForeignKeyConstraint(['company_id','asset_id'],['assets.company_id','assets.id']),
        sa.ForeignKeyConstraint(['company_id','assignee_id'],['memberships.company_id','memberships.id'],name='fk_plan_assignee'),
        sa.ForeignKeyConstraint(['company_id','escalation_member_id'],['memberships.company_id','memberships.id'],name='fk_plan_escalation'),
        sa.CheckConstraint("interval_unit IN ('day','week','month') AND interval_count BETWEEN 1 AND 365",name='plan_interval'),
        sa.CheckConstraint("priority IN ('low','medium','high','urgent')",name='plan_priority'),
        sa.CheckConstraint('reminder_hours BETWEEN 0 AND 72 AND next_index>=0 AND generation>0 AND revision>0',name='plan_bounds'))
    op.create_index('ix_plan_tick','maintenance_plans',['company_id','last_tick_at','id'])
    op.add_column('work_orders',sa.Column('plan_id',sa.Integer()))
    op.add_column('work_orders',sa.Column('occurrence_id',sa.Integer()))
    op.add_column('work_orders',sa.Column('notification_generation',sa.Integer(),nullable=False,server_default='1'))
    op.create_foreign_key('fk_work_plan','work_orders','maintenance_plans',['company_id','plan_id'],['company_id','id'])
    op.create_check_constraint('work_plan_provenance','work_orders','(plan_id IS NULL) = (occurrence_id IS NULL)')
    op.create_index('uq_work_unfinished_plan','work_orders',['company_id','plan_id'],unique=True,
        postgresql_where=sa.text("plan_id IS NOT NULL AND status NOT IN ('completed','cancelled')"))
    op.create_table('plan_occurrences',
        sa.Column('id',sa.Integer(),primary_key=True),tenant(),sa.Column('plan_id',sa.Integer(),nullable=False),
        sa.Column('generation',sa.Integer(),nullable=False),sa.Column('slot_index',sa.Integer(),nullable=False),
        sa.Column('scheduled_at',sa.DateTime(timezone=True),nullable=False),sa.Column('scheduled_local',sa.String(16),nullable=False),
        sa.Column('timezone',sa.String(64),nullable=False),sa.Column('snapshot',sa.JSON(),nullable=False),
        sa.Column('work_order_id',sa.Integer(),nullable=False),sa.Column('missed_count',sa.Integer(),nullable=False),
        sa.Column('missed_from',sa.DateTime(timezone=True)),sa.Column('missed_through',sa.DateTime(timezone=True)),stamp(),
        sa.UniqueConstraint('company_id','id'),sa.UniqueConstraint('company_id','plan_id','id'),
        sa.UniqueConstraint('plan_id','generation','slot_index'),sa.UniqueConstraint('plan_id','generation','scheduled_local'),
        sa.UniqueConstraint('company_id','work_order_id'),
        sa.ForeignKeyConstraint(['company_id','plan_id'],['maintenance_plans.company_id','maintenance_plans.id']),
        sa.ForeignKeyConstraint(['company_id','work_order_id'],['work_orders.company_id','work_orders.id'],name='fk_occurrence_work'),
        sa.CheckConstraint('generation>0 AND slot_index>=0 AND missed_count>=0',name='occurrence_bounds'))
    op.create_foreign_key('fk_work_occurrence','work_orders','plan_occurrences',
        ['company_id','plan_id','occurrence_id'],['company_id','plan_id','id'],deferrable=True,initially='DEFERRED')
    op.alter_column('work_events','actor_id',existing_type=sa.Integer(),nullable=True)
    op.add_column('work_events',sa.Column('actor_kind',sa.String(10),nullable=False,server_default='user'))
    op.create_check_constraint('work_event_actor','work_events',
        "(actor_kind='user' AND actor_id IS NOT NULL AND action<>'schedule_create') OR (actor_kind='system' AND actor_id IS NULL AND action='schedule_create' AND actor_name='Schedule')")
    op.create_table('plan_events',sa.Column('id',sa.Integer(),primary_key=True),tenant(),
        sa.Column('plan_id',sa.Integer(),nullable=False),sa.Column('action',sa.String(32),nullable=False),
        sa.Column('actor_id',sa.Integer(),sa.ForeignKey('users.id')),sa.Column('actor_name',sa.String(100),nullable=False),
        sa.Column('notes',sa.Text(),nullable=False),stamp(),
        sa.ForeignKeyConstraint(['company_id','plan_id'],['maintenance_plans.company_id','maintenance_plans.id']))
    op.create_table('work_reminders',sa.Column('id',sa.Integer(),primary_key=True),tenant(),
        sa.Column('occurrence_id',sa.Integer(),nullable=False),sa.Column('work_order_id',sa.Integer(),nullable=False),
        sa.Column('stage',sa.String(10),nullable=False),sa.Column('recipient_id',sa.Integer(),nullable=False),
        sa.Column('notification_generation',sa.Integer(),nullable=False),sa.Column('state',sa.String(20),nullable=False),
        sa.Column('scheduled_at',sa.DateTime(timezone=True),nullable=False),sa.Column('accepted_at',sa.DateTime(timezone=True)),
        sa.Column('acknowledged_at',sa.DateTime(timezone=True)),sa.Column('attempts',sa.Integer(),nullable=False),
        sa.Column('error',sa.String(300)),stamp(),sa.UniqueConstraint('company_id','id'),
        sa.UniqueConstraint('occurrence_id','stage','recipient_id','notification_generation'),
        sa.ForeignKeyConstraint(['company_id','occurrence_id'],['plan_occurrences.company_id','plan_occurrences.id']),
        sa.ForeignKeyConstraint(['company_id','work_order_id'],['work_orders.company_id','work_orders.id']),
        sa.ForeignKeyConstraint(['company_id','recipient_id'],['memberships.company_id','memberships.id']),
        sa.CheckConstraint("stage IN ('due','overdue')",name='reminder_stage'),
        sa.CheckConstraint("state IN ('queued','running','retrying','accepted','failed','cancelled')",name='reminder_state'),
        sa.CheckConstraint('attempts>=0 AND notification_generation>0',name='reminder_bounds'))
    op.create_index('ix_reminder_pending','work_reminders',['company_id','state','scheduled_at'])
    op.add_column('pilot_jobs',sa.Column('reminder_id',sa.Integer()))
    op.create_foreign_key('fk_job_reminder','pilot_jobs','work_reminders',['company_id','reminder_id'],['company_id','id'])
    op.create_check_constraint('job_reminder_provenance','pilot_jobs',
        "kind<>'maintenance_mail' OR (company_id IS NOT NULL AND reminder_id IS NOT NULL AND token_id IS NULL)")
    op.create_table('reminder_attempts',sa.Column('id',sa.Integer(),primary_key=True),tenant(),
        sa.Column('reminder_id',sa.Integer(),nullable=False),sa.Column('lease_token',sa.String(64),nullable=False),
        sa.Column('outcome',sa.String(20),nullable=False),sa.Column('error',sa.String(300)),stamp(),
        sa.ForeignKeyConstraint(['company_id','reminder_id'],['work_reminders.company_id','work_reminders.id']))
    op.create_table('worker_heartbeats',sa.Column('id',sa.String(64),primary_key=True),
        sa.Column('last_seen_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('last_tick_at',sa.DateTime(timezone=True)),sa.Column('stopped_at',sa.DateTime(timezone=True)))
    op.execute("""CREATE FUNCTION pilot_pm_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN RAISE EXCEPTION 'Preventive maintenance evidence is immutable'; END $$""")
    for table in ('plan_occurrences','plan_events','reminder_attempts'):
        op.execute(f'CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION pilot_pm_immutable()')
    op.execute("""CREATE FUNCTION pilot_pm_work_link() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF NEW.plan_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM plan_occurrences o
              WHERE o.id=NEW.occurrence_id AND o.company_id=NEW.company_id
              AND o.plan_id=NEW.plan_id AND o.work_order_id=NEW.id) THEN
            RAISE EXCEPTION 'Invalid preventive work provenance';
          END IF;
          RETURN NEW;
        END $$""")
    op.execute("""CREATE CONSTRAINT TRIGGER work_pm_link AFTER INSERT OR UPDATE ON work_orders
        DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION pilot_pm_work_link()""")
    op.execute("""CREATE FUNCTION pilot_pm_system_event() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF NEW.actor_kind='system' AND NOT EXISTS (SELECT 1 FROM work_orders w
              WHERE w.id=NEW.work_order_id AND w.company_id=NEW.company_id AND w.plan_id IS NOT NULL) THEN
            RAISE EXCEPTION 'System events require preventive work provenance';
          END IF;
          RETURN NEW;
        END $$""")
    op.execute('CREATE TRIGGER work_pm_system_event BEFORE INSERT OR UPDATE ON work_events FOR EACH ROW EXECUTE FUNCTION pilot_pm_system_event()')


def downgrade():
    connection = op.get_bind()
    unsafe = connection.execute(sa.text("""SELECT EXISTS(SELECT 1 FROM maintenance_plans)
        OR EXISTS(SELECT 1 FROM plan_occurrences) OR EXISTS(SELECT 1 FROM plan_events)
        OR EXISTS(SELECT 1 FROM work_reminders) OR EXISTS(SELECT 1 FROM reminder_attempts)
        OR EXISTS(SELECT 1 FROM pilot_jobs WHERE kind='maintenance_mail')
        OR EXISTS(SELECT 1 FROM work_orders WHERE plan_id IS NOT NULL)
        OR EXISTS(SELECT 1 FROM work_events WHERE actor_kind='system')""")).scalar()
    if unsafe:
        raise RuntimeError('Downgrade refused: preventive maintenance evidence must be preserved')
    op.execute('DROP TRIGGER work_pm_system_event ON work_events')
    op.execute('DROP FUNCTION pilot_pm_system_event()')
    op.execute('DROP TRIGGER work_pm_link ON work_orders')
    op.execute('DROP FUNCTION pilot_pm_work_link()')
    for table in ('plan_occurrences','plan_events','reminder_attempts'):
        op.execute(f'DROP TRIGGER {table}_immutable ON {table}')
    op.execute('DROP FUNCTION pilot_pm_immutable()')
    op.drop_table('worker_heartbeats')
    op.drop_table('reminder_attempts')
    op.drop_constraint(op.f('ck_pilot_jobs_job_reminder_provenance'),'pilot_jobs',type_='check')
    op.drop_constraint('fk_job_reminder','pilot_jobs',type_='foreignkey')
    op.drop_column('pilot_jobs','reminder_id')
    op.drop_table('work_reminders')
    op.drop_table('plan_events')
    op.drop_constraint(op.f('ck_work_events_work_event_actor'),'work_events',type_='check')
    op.drop_column('work_events','actor_kind')
    op.alter_column('work_events','actor_id',existing_type=sa.Integer(),nullable=False)
    op.drop_constraint('fk_work_occurrence','work_orders',type_='foreignkey')
    op.drop_table('plan_occurrences')
    op.drop_index('uq_work_unfinished_plan',table_name='work_orders')
    op.drop_constraint(op.f('ck_work_orders_work_plan_provenance'),'work_orders',type_='check')
    op.drop_constraint('fk_work_plan','work_orders',type_='foreignkey')
    for column in ('notification_generation','occurrence_id','plan_id'):
        op.drop_column('work_orders',column)
    op.drop_table('maintenance_plans')
    op.drop_column('worker_schedules','rotation_cursor')
