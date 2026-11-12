"""Durable identity, tenancy, work history and outbox models."""
from datetime import datetime, timezone
from app import db


def now():
    from flask import current_app, has_app_context
    if has_app_context() and current_app.testing and current_app.config.get('TEST_CLOCK'):
        value = current_app.config['TEST_CLOCK']()
        if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
            raise RuntimeError('TEST_CLOCK must return an aware datetime')
        return value.astimezone(timezone.utc)
    return datetime.now(timezone.utc)


class Membership(db.Model):
    __tablename__ = 'memberships'
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=True)
    revision = db.Column(db.Integer, nullable=False, default=1)
    __table_args__ = (db.UniqueConstraint('company_id', 'user_id'), db.UniqueConstraint('company_id', 'id'), db.CheckConstraint("role IN ('owner','admin','planner','technician','stores','viewer')", name='membership_role'))


class AuthSession(db.Model):
    __tablename__ = 'auth_sessions'
    id = db.Column(db.String(64), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    membership_id = db.Column(db.Integer, db.ForeignKey('memberships.id'), nullable=False)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    revoked_at = db.Column(db.DateTime(timezone=True))
    access_confirmed_at = db.Column(db.DateTime(timezone=True))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now)


class AuthToken(db.Model):
    __tablename__ = 'auth_tokens'
    id = db.Column(db.Integer, primary_key=True)
    digest = db.Column(db.String(64), unique=True, nullable=False)
    kind = db.Column(db.String(20), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'))
    email = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20))
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    consumed_at = db.Column(db.DateTime(timezone=True))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now)


class RateBucket(db.Model):
    __tablename__ = 'rate_buckets'
    key = db.Column(db.String(64), primary_key=True)
    count = db.Column(db.Integer, nullable=False, default=0)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)


class WorkOrder(db.Model):
    __tablename__ = 'work_orders'
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    asset_id = db.Column(db.Integer, nullable=False)
    number = db.Column(db.String(32), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False, default='')
    priority = db.Column(db.String(20), nullable=False, default='medium')
    status = db.Column(db.String(32), nullable=False, default='open')
    assignee_id = db.Column(db.Integer)
    due_at = db.Column(db.DateTime(timezone=True))
    revision = db.Column(db.Integer, nullable=False, default=1)
    notes = db.Column(db.Text, nullable=False, default='')
    completion_notes = db.Column(db.Text, nullable=False, default='')
    checklist = db.Column(db.JSON, nullable=False, default=list)
    labor_minutes = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now)
    completed_at = db.Column(db.DateTime(timezone=True))
    plan_id = db.Column(db.Integer)
    occurrence_id = db.Column(db.Integer)
    notification_generation = db.Column(db.Integer, nullable=False, default=1)
    __table_args__ = (
        db.ForeignKeyConstraint(['company_id', 'plan_id'], ['maintenance_plans.company_id', 'maintenance_plans.id'], name='fk_work_plan'),
        db.ForeignKeyConstraint(['company_id', 'plan_id', 'occurrence_id'], ['plan_occurrences.company_id', 'plan_occurrences.plan_id', 'plan_occurrences.id'], use_alter=True, name='fk_work_occurrence', deferrable=True, initially='DEFERRED'),
        db.CheckConstraint('(plan_id IS NULL) = (occurrence_id IS NULL)', name='work_plan_provenance'),
        db.Index('uq_work_unfinished_plan', 'company_id', 'plan_id', unique=True, postgresql_where=db.text("plan_id IS NOT NULL AND status NOT IN ('completed','cancelled')")),
        db.UniqueConstraint('company_id', 'id'), db.UniqueConstraint('company_id', 'number'),
        db.ForeignKeyConstraint(['company_id', 'asset_id'], ['assets.company_id', 'assets.id']),
        db.ForeignKeyConstraint(['company_id', 'assignee_id'], ['memberships.company_id', 'memberships.id']),
        db.CheckConstraint("status IN ('open','assigned','in_progress','blocked','awaiting_review','completed','cancelled')", name='work_status'),
        db.CheckConstraint("priority IN ('low','medium','high','urgent')", name='work_priority'),
        db.CheckConstraint('labor_minutes >= 0', name='work_labor'),
    )


class WorkEvent(db.Model):
    __tablename__ = 'work_events'
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    work_order_id = db.Column(db.Integer, nullable=False)
    actor_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    actor_kind = db.Column(db.String(10), nullable=False, default='user')
    actor_name = db.Column(db.String(100), nullable=False)
    action = db.Column(db.String(32), nullable=False)
    from_status = db.Column(db.String(32))
    to_status = db.Column(db.String(32), nullable=False)
    notes = db.Column(db.Text, nullable=False, default='')
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now)
    __table_args__ = (db.ForeignKeyConstraint(['company_id','work_order_id'], ['work_orders.company_id','work_orders.id']),
        db.CheckConstraint("(actor_kind='user' AND actor_id IS NOT NULL AND action<>'schedule_create') OR (actor_kind='system' AND actor_id IS NULL AND action='schedule_create' AND actor_name='Schedule')", name='work_event_actor'),)


class Idempotency(db.Model):
    __tablename__ = 'idempotency_records'
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    key = db.Column(db.String(128), nullable=False)
    digest = db.Column(db.String(64), nullable=False)
    response = db.Column(db.JSON)
    status_code = db.Column(db.Integer)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now)
    __table_args__ = (db.UniqueConstraint('company_id','user_id','key'),)


class Document(db.Model):
    __tablename__ = 'documents'
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    asset_id = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    filename = db.Column(db.String(200), nullable=False)
    blob_key = db.Column(db.String(200), unique=True, nullable=False)
    size = db.Column(db.Integer, nullable=False)
    checksum = db.Column(db.String(64), nullable=False)
    status = db.Column(db.String(32), nullable=False, default='quarantined')
    page_count = db.Column(db.Integer)
    pages = db.Column(db.JSON)
    error = db.Column(db.String(300))
    revision = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now)
    deleted_at = db.Column(db.DateTime(timezone=True))
    staging_token = db.Column(db.String(64))
    staging_until = db.Column(db.DateTime(timezone=True))
    storage_released_at = db.Column(db.DateTime(timezone=True))
    __table_args__ = (db.ForeignKeyConstraint(['company_id','asset_id'], ['assets.company_id','assets.id']), db.CheckConstraint("status IN ('staging','quarantined','processing','ready','failed','deleted')", name='document_status'))


class Job(db.Model):
    __tablename__ = 'pilot_jobs'
    id = db.Column(db.Integer, primary_key=True)
    kind = db.Column(db.String(32), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'))
    token_id = db.Column(db.Integer, db.ForeignKey('auth_tokens.id'))
    reminder_id = db.Column(db.Integer)
    identity = db.Column(db.String(100), unique=True, nullable=False)
    payload = db.Column(db.JSON, nullable=False)
    state = db.Column(db.String(20), nullable=False, default='queued')
    attempts = db.Column(db.Integer, nullable=False, default=0)
    available_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now)
    lease_until = db.Column(db.DateTime(timezone=True))
    lease_token = db.Column(db.String(64))
    error = db.Column(db.String(300))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now)
    __table_args__ = (db.Index('ix_pilot_jobs_claim','state','available_at'),
        db.ForeignKeyConstraint(['company_id', 'reminder_id'], ['work_reminders.company_id', 'work_reminders.id'], name='fk_job_reminder'),
        db.CheckConstraint("kind<>'maintenance_mail' OR (company_id IS NOT NULL AND reminder_id IS NOT NULL AND token_id IS NULL)", name='job_reminder_provenance'),)


class TenantSchedule(db.Model):
    __tablename__ = 'tenant_schedules'
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), primary_key=True)
    last_dispatched_at = db.Column(db.DateTime(timezone=True))


class WorkerSchedule(db.Model):
    __tablename__ = 'worker_schedules'
    id = db.Column(db.Integer, primary_key=True)
    last_kind = db.Column(db.String(32))
    rotation_cursor = db.Column(db.Integer, nullable=False, default=0)


class MaintenancePlan(db.Model):
    __tablename__ = 'maintenance_plans'
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    asset_id = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False, default='')
    priority = db.Column(db.String(20), nullable=False, default='medium')
    assignee_id = db.Column(db.Integer)
    checklist = db.Column(db.JSON, nullable=False, default=list)
    timezone = db.Column(db.String(64), nullable=False)
    start_local = db.Column(db.String(16), nullable=False)
    interval_unit = db.Column(db.String(10), nullable=False)
    interval_count = db.Column(db.Integer, nullable=False)
    reminder_hours = db.Column(db.Integer, nullable=False, default=24)
    escalation_member_id = db.Column(db.Integer)
    enabled = db.Column(db.Boolean, nullable=False, default=True)
    revision = db.Column(db.Integer, nullable=False, default=1)
    generation = db.Column(db.Integer, nullable=False, default=1)
    effective_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now)
    next_index = db.Column(db.Integer, nullable=False, default=0)
    next_due_at = db.Column(db.DateTime(timezone=True))
    next_due_local = db.Column(db.String(16))
    paused_at = db.Column(db.DateTime(timezone=True))
    blocked_reason = db.Column(db.String(100))
    last_tick_at = db.Column(db.DateTime(timezone=True))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now)
    __table_args__ = (
        db.UniqueConstraint('company_id', 'id'),
        db.ForeignKeyConstraint(['company_id','asset_id'], ['assets.company_id','assets.id']),
        db.ForeignKeyConstraint(['company_id','assignee_id'], ['memberships.company_id','memberships.id'], name='fk_plan_assignee'),
        db.ForeignKeyConstraint(['company_id','escalation_member_id'], ['memberships.company_id','memberships.id'], name='fk_plan_escalation'),
        db.CheckConstraint("interval_unit IN ('day','week','month') AND interval_count BETWEEN 1 AND 365", name='plan_interval'),
        db.CheckConstraint("priority IN ('low','medium','high','urgent')", name='plan_priority'),
        db.CheckConstraint('reminder_hours BETWEEN 0 AND 72 AND next_index>=0 AND generation>0 AND revision>0', name='plan_bounds'),
        db.Index('ix_plan_tick','company_id','last_tick_at','id'),
    )


class PlanOccurrence(db.Model):
    __tablename__ = 'plan_occurrences'
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    plan_id = db.Column(db.Integer, nullable=False)
    generation = db.Column(db.Integer, nullable=False)
    slot_index = db.Column(db.Integer, nullable=False)
    scheduled_at = db.Column(db.DateTime(timezone=True), nullable=False)
    scheduled_local = db.Column(db.String(16), nullable=False)
    timezone = db.Column(db.String(64), nullable=False)
    snapshot = db.Column(db.JSON, nullable=False)
    work_order_id = db.Column(db.Integer, nullable=False)
    missed_count = db.Column(db.Integer, nullable=False, default=0)
    missed_from = db.Column(db.DateTime(timezone=True))
    missed_through = db.Column(db.DateTime(timezone=True))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now)
    __table_args__ = (
        db.UniqueConstraint('company_id','id'),
        db.UniqueConstraint('company_id','plan_id','id'),
        db.UniqueConstraint('plan_id','generation','slot_index'),
        db.UniqueConstraint('plan_id','generation','scheduled_local'),
        db.UniqueConstraint('company_id','work_order_id'),
        db.ForeignKeyConstraint(['company_id','plan_id'], ['maintenance_plans.company_id','maintenance_plans.id']),
        db.ForeignKeyConstraint(['company_id','work_order_id'], ['work_orders.company_id','work_orders.id'], use_alter=True, name='fk_occurrence_work'),
        db.CheckConstraint('generation>0 AND slot_index>=0 AND missed_count>=0', name='occurrence_bounds'),
    )


class PlanEvent(db.Model):
    __tablename__ = 'plan_events'
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    plan_id = db.Column(db.Integer, nullable=False)
    action = db.Column(db.String(32), nullable=False)
    actor_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    actor_name = db.Column(db.String(100), nullable=False)
    notes = db.Column(db.Text, nullable=False, default='')
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now)
    __table_args__ = (db.ForeignKeyConstraint(['company_id','plan_id'], ['maintenance_plans.company_id','maintenance_plans.id']),)


class WorkReminder(db.Model):
    __tablename__ = 'work_reminders'
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    occurrence_id = db.Column(db.Integer, nullable=False)
    work_order_id = db.Column(db.Integer, nullable=False)
    stage = db.Column(db.String(10), nullable=False)
    recipient_id = db.Column(db.Integer, nullable=False)
    notification_generation = db.Column(db.Integer, nullable=False)
    state = db.Column(db.String(20), nullable=False, default='queued')
    scheduled_at = db.Column(db.DateTime(timezone=True), nullable=False)
    accepted_at = db.Column(db.DateTime(timezone=True))
    acknowledged_at = db.Column(db.DateTime(timezone=True))
    attempts = db.Column(db.Integer, nullable=False, default=0)
    error = db.Column(db.String(300))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now)
    __table_args__ = (
        db.UniqueConstraint('company_id','id'),
        db.UniqueConstraint('occurrence_id','stage','recipient_id','notification_generation'),
        db.ForeignKeyConstraint(['company_id','occurrence_id'], ['plan_occurrences.company_id','plan_occurrences.id']),
        db.ForeignKeyConstraint(['company_id','work_order_id'], ['work_orders.company_id','work_orders.id']),
        db.ForeignKeyConstraint(['company_id','recipient_id'], ['memberships.company_id','memberships.id']),
        db.CheckConstraint("stage IN ('due','overdue')", name='reminder_stage'),
        db.CheckConstraint("state IN ('queued','running','retrying','accepted','failed','cancelled')", name='reminder_state'),
        db.CheckConstraint('attempts>=0 AND notification_generation>0', name='reminder_bounds'),
        db.Index('ix_reminder_pending','company_id','state','scheduled_at'),
    )


class ReminderAttempt(db.Model):
    __tablename__ = 'reminder_attempts'
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    reminder_id = db.Column(db.Integer, nullable=False)
    lease_token = db.Column(db.String(64), nullable=False)
    outcome = db.Column(db.String(20), nullable=False)
    error = db.Column(db.String(300))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now)
    __table_args__ = (db.ForeignKeyConstraint(['company_id','reminder_id'], ['work_reminders.company_id','work_reminders.id']),)


class WorkerHeartbeat(db.Model):
    __tablename__ = 'worker_heartbeats'
    id = db.Column(db.String(64), primary_key=True)
    last_seen_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now)
    last_tick_at = db.Column(db.DateTime(timezone=True))
    stopped_at = db.Column(db.DateTime(timezone=True))


class AccessAudit(db.Model):
    __tablename__ = 'access_audits'
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    actor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    target_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    membership_id = db.Column(db.Integer, db.ForeignKey('memberships.id'))
    invitation_id = db.Column(db.Integer, db.ForeignKey('auth_tokens.id'))
    action = db.Column(db.String(32), nullable=False)
    old_role = db.Column(db.String(20))
    new_role = db.Column(db.String(20))
    old_active = db.Column(db.Boolean)
    new_active = db.Column(db.Boolean)
    reason = db.Column(db.String(1000), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now)
