# Preventive maintenance local milestone contract — 2026-11-12

Scope: approved local-only PM, no production deployment/inference/equipment/real mail. Preserve0001/0002 and all original data/config/keys. See approved plan and ORIGINAL_VISION_CROSSCHECK_2026-11-12.md. Existing /api/v1 error envelope retained. New schema pilot_0003.

## Plan API

All resource IDs derive company from authoritative current membership. GET for active members, mutation owner/admin/planner with existing owner/admin MFA. Mutations use Idempotency-Key and revision. No supplied company_id. Stable error codes for validation/foreign/revision/capacity. Unknown fields rejected.

- GET /maintenance-plans → {plans:[Plan]}; query asset_id optional.
- POST /maintenance-plans → {plan:Plan},201. Fields asset_id,title,description?,priority?,assignee_id?,checklist:[{text}],timezone (valid IANA),start_local (YYYY-MM-DDTHH:mm, no offset),interval_unit:day|week|month,interval_count:1..365,reminder_hours:0..72(default24),escalation_member_id?(active owner/admin/planner). No end_date/meter/cron.
- GET /maintenance-plans/<id> → {plan:Plan,occurrences:[Occurrence],events:[PlanEvent],reminders:[Reminder]} (bounded100 each; newest first).
- PATCH /maintenance-plans/<id> same editable fields except asset_id + revision → {plan}. Schedule fields affect future generation; immutable existing work snapshots unaffected. Local start preview needed; no changing calendar silently.
- POST /maintenance-plans/<id>/pause or /resume {revision,reason} → {plan}. Existing work retained, unsent plan reminders invalidated on pause. Resume skips paused periods with audit; no cancelled job resurrection.
- POST /maintenance-plans/preview {start_local,timezone,interval_unit,interval_count} → {dates:[{scheduled_local,scheduled_at,timezone}],policy:{month_end,dst_gap,dst_fold,catch_up}}. This is read-only calculation; requires member and CSRF, not mutation idempotency; at most5 future anchor slots.
- POST /maintenance-reminders/<id>/retry {reason} manager only → {reminder}; terminal failed only and all current authority/provenance revalidated, no resend accepted/cancelled.
- POST /maintenance-reminders/<id>/ack {} own recipient (or manager within company) → {reminder}. Ack doesn't approve work or imply SMTP receipt.

Plan JSON: id,asset_id,asset_name,title,description,priority,assignee_id,assignee_name,checklist:[{text}],timezone,start_local,interval_unit,interval_count,reminder_hours,escalation_member_id,enabled,revision,generation,next_due_at,next_due_local,blocked_reason,created_at. Date fields UTC ISO except named local fields. Add company.timezone and capability manage_preventive_maintenance to auth identity (additive).
Occurrence JSON: id,plan_id,generation,scheduled_at,scheduled_local,work_order_id,missed_count,missed_from,missed_through,created_at. Current serializer does not include captured timezone; UI labels historical-zone absence explicitly, never guesses old zone after edits. Immutable snapshot linkage; missed summaries via PlanEvent, no synthetic completion.
PlanEvent: id,action,actor_name,notes,created_at. System schedule events named Schedule, never technician impersonation.
Reminder JSON: id,occurrence_id,work_order_id,stage:due|overdue,recipient_name,state:queued|running|retrying|accepted|failed|cancelled,scheduled_at,accepted_at,acknowledged_at,attempts,error,created_at. Sanitized generic error, no email-body/token/secret leakage.
WorkOrder JSON additive plan_id,occurrence_id (null for ordinary jobs). WorkEvent JSON additive actor_kind:user|system (system allowed only schedule_create, null actor_id). Existing human paths unchanged.

## Durable semantics

Fixed local anchor day/week/month (not completion based). Month31→Feblast→March31; leap/DST gap advance by gap, fold earlier instant. Capture zone per generation. One unfinished order per plan includes awaiting_review. Materialize first next due within reminder_hours. Downtime without active job coalesces to latest due slot (missed count/date range); active job retains original due, later slots summarized as missed. On completion/cancel continue next future anchor; don't replay backlog. Reopen conflicts if another plan order unfinished. Pause stops future jobs/reminders not actual work; resume skip paused intervals. Scheduler pass and per-tenant/plan limits bounded; no massive date loop. Every generation/slot identity unique; transaction work+event+reminders+cursor atomic.

Reminder identity occurrence/stage/recipient/due-assignment generation, NOT ordinary work revision. Due/start/block changes not new mail unless due/assignee actually changes. Completion/cancel/pause/offboard revalidated immediately before delivery. New maintenance_mail Job backed by real Reminder row; auth mail valid_mail token rules unchanged. Auth priority with bounded rotation/doc+reminder tenant fairness. No locks over external IO; leases fenced, transient retries bounded, permanent recipient refusal failed. Deterministic Message-ID dedupe aids but doesn't make SMTP exactly once; already-started sends unretractable. Acceptance != acknowledgment != completed maintenance.

run_once API kept (all/mail/document + additive maintenance_mail). New foreground service callable/CLI; explicit bounded scheduler tick clock injection for tests only. No HTTP time-control endpoint. Heartbeat/queue evidence, no fake ready claims. Freeze0001/0002; downgrade0003 refuses evidence. Existing0002 fixtures don't auto-delete originals.

## Quality/security gates

Native Flask+PostgreSQL+React+existing outbox; T1078/T1190 control maps, CSF PR.AA/PR.PS/PR.IR/DE.CM/RC.RP; no AI/money path. Tenant-role/MFA/CSRF/unknown fields, composite refs, unique generation+slot and reminder, shared/exclusive guard then tenant/scheduler/Company→plan→Job→domain consistent locks. A worker never invokes decorated endpoint or fabricates g. Direct UI clients identified frontend Maintenance/Today/query/api/types; old route contract backward-compatible. No PDM GitNexus index so source+test tracing authoritative.

Acceptance: calendar/DST/month/leap red-green tests; repeated/concurrent tick/restart/missed/pause/edit/reopen/archive/offboard; reminder forgery/auth token regressions/retry/refusal/leases/fairness; mobile320/375/390 visible44px actions plus keyboard; actual Mailpit/scanner/parser in new run. Full serial disposable _test pytest, frontend type/lint/unit/build, Edge, new scratch app+blob+testkey restore, original fingerprint unchanged. No completion claim before freshly executed proof.
