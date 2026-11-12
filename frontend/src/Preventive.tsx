import { useState } from "react";
import { Link, NavLink, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { ArrowLeft, Plus, Search } from "lucide-react";
import { useMutation } from "@tanstack/react-query";
import { ApiError, mutate, queryString } from "./api";
import { queryClient, refreshData, useIdentity, useResource } from "./query";
import { can, dateLabel, plainStatus } from "./permissions";
import type { Asset, Identity, IntervalUnit, MaintenancePlan, MaintenanceReminder, Member, PlanPreview, PlanRecord } from "./types";
import { Definition, Dialog, Empty, ErrorNotice, Field, Form, Loading, numeric, PageHeader, Select, Status, Submit, Textarea, useAction, value } from "./ui";

export function MaintenanceTabs() {
  return <nav className="maintenance-tabs" aria-label="Maintenance records">
    <NavLink to="/app/maintenance" end>Jobs</NavLink>
    <NavLink to="/app/maintenance/plans">Preventive plans</NavLink>
  </nav>;
}
function cadence(plan: MaintenancePlan) {
  return `Every ${plan.interval_count} ${plan.interval_unit}${plan.interval_count === 1 ? "" : "s"}`;
}
function LocalDate({ local, zone, utc }: { local: string | null; zone: string; utc?: string | null }) {
  // Local strings have no offset: never parse them through the browser's time zone.
  return local ? <span className="schedule-date"><span>{local.replace("T", " ")} / {zone}</span>{utc && <small>UTC: {utc}</small>}</span> : <span>No next date recorded</span>;
}
function ConflictRefresh({ error, onClose }: { error: Error | null; onClose: () => void }) {
  return error instanceof ApiError && error.code === "revision_conflict" ? <button type="button" className="button secondary" onClick={() => { onClose(); void refreshData(); }}>Close and refresh record</button> : null;
}
function PlanForm({ identity, plan, initialAsset = "", onClose }: { identity: Identity; plan?: MaintenancePlan; initialAsset?: string; onClose: () => void }) {
  const navigate = useNavigate();
  const assets = useResource<{ assets: Asset[] }>(["assets", "plan-form"], "/assets", !plan);
  const members = useResource<{ members: Member[] }>(["members"], "/members");
  const [asset, setAsset] = useState(String(plan?.asset_id || initialAsset));
  const [assignee, setAssignee] = useState(String(plan?.assignee_id || ""));
  const [escalation, setEscalation] = useState(String(plan?.escalation_member_id || ""));
  const [steps, setSteps] = useState(plan?.checklist.map((step) => step.text) || [""]);
  const [calendar, setCalendar] = useState({ start_local: plan?.start_local || "", timezone: plan?.timezone || identity.company.timezone || "Africa/Lagos", interval_unit: plan?.interval_unit || "day" as IntervalUnit, interval_count: String(plan?.interval_count || 1) });
  const calendarPayload = { ...calendar, interval_count: Number(calendar.interval_count) };
  const fingerprint = JSON.stringify(calendarPayload);
  const preview = useMutation({
    mutationFn: async (request: typeof calendarPayload) => ({ fingerprint: JSON.stringify(request), result: await mutate<PlanPreview>("/maintenance-plans/preview", request) }),
    onError: (error) => { if (error instanceof ApiError && error.status === 401) void queryClient.invalidateQueries({ queryKey: ["v1", "identity"] }); },
  });
  const currentPreview = preview.data?.fingerprint === fingerprint ? preview.data.result : null;
  const save = useAction((form: FormData) => mutate<{ plan: MaintenancePlan }>(plan ? `/maintenance-plans/${plan.id}` : "/maintenance-plans", {
    ...(plan ? { revision: plan.revision } : { asset_id: numeric(form, "asset_id") }),
    title: value(form, "title"), description: value(form, "description"), priority: value(form, "priority"),
    assignee_id: assignee ? Number(assignee) : null,
    escalation_member_id: escalation ? Number(escalation) : null,
    checklist: steps.filter((text) => text.trim()).map((text) => ({ text: text.trim() })),
    reminder_hours: numeric(form, "reminder_hours"), ...calendarPayload,
  }, plan ? "PATCH" : "POST"), plan ? "Preventive plan updated. Existing job instructions are unchanged." : "Preventive plan created.", (data) => { onClose(); navigate(`/app/maintenance/plans/${data.plan.id}`); });
  const eligible = members.data?.members.filter((member) => ["owner", "admin", "planner", "technician"].includes(member.role)) || [];
  const managers = eligible.filter((member) => ["owner", "admin", "planner"].includes(member.role));
  const calendarValid = !!calendar.start_local && !!calendar.timezone.trim() && Number.isInteger(Number(calendar.interval_count)) && Number(calendar.interval_count) >= 1 && Number(calendar.interval_count) <= 365;
  const cannotSave = save.isPending || !currentPreview?.dates.length || members.isPending || !!members.error || (!plan && (assets.isPending || !!assets.error));
  return <Dialog title={plan ? "Edit preventive plan" : "Create preventive plan"} onClose={onClose} dismissible={!save.isPending}>
    <p className="form-intro">A fixed calendar schedule creates a job, not a completed maintenance record. {plan && "Changes apply to future snapshots; existing jobs keep their instructions and dates. Calendar changes start a new schedule generation."}</p>
    <Form onSubmit={(form) => { if (!cannotSave) save.mutate(form); }}>
      {plan ? <p><strong>Machine:</strong> {plan.asset_name}</p> : <Select label="Machine" name="asset_id" value={asset} required disabled={assets.isPending || !!assets.error} onChange={(event) => setAsset(event.target.value)}><option value="">Choose a machine</option>{assets.data?.assets.filter((item) => item.status !== "archived").map((item) => <option key={item.id} value={item.id}>{item.code} / {item.name}</option>)}</Select>}
      <ErrorNotice error={assets.error} retry={() => void assets.refetch()} />
      {!plan && assets.data?.assets.length === 0 && <p className="notice">Record a machine first. <Link to="/app/machines">Open machines</Link></p>}
      <Field label="Plan title" name="title" defaultValue={plan?.title} required maxLength={200} />
      <Textarea label="Work instructions" name="description" defaultValue={plan?.description} maxLength={10000} />
      <Select label="Priority" name="priority" defaultValue={plan?.priority || "medium"}>{["low", "medium", "high", "urgent"].map((item) => <option key={item} value={item}>{plainStatus(item)}</option>)}</Select>
      <Select label="Assigned person" name="assignee_id" value={assignee} onChange={(event) => setAssignee(event.target.value)} disabled={members.isPending || !!members.error}><option value="">Unassigned / needs assignment before work</option>{plan?.assignee_id && !eligible.some((member) => member.id === plan.assignee_id) && <option value={plan.assignee_id}>{plan.assignee_name || "Previous assignee"} / no longer eligible</option>}{eligible.map((member) => <option key={member.id} value={member.id}>{member.name} ({member.role})</option>)}</Select>
      <ErrorNotice error={members.error} retry={() => void members.refetch()} />
      <fieldset><legend>Calendar schedule</legend><div className="form calendar-fields">
        <Field label="First due date and time" name="start_local" type="datetime-local" value={calendar.start_local} required onChange={(event) => setCalendar({ ...calendar, start_local: event.target.value })} hint="Local wall-clock time in the plan's zone, not this device's zone." />
        <Field label="Time zone (IANA)" name="timezone" value={calendar.timezone} required maxLength={64} onChange={(event) => setCalendar({ ...calendar, timezone: event.target.value })} hint="For example Africa/Lagos or America/New_York. The server validates the zone." />
        <div className="form-grid"><Field label="Every" name="interval_count" type="number" min={1} max={365} step={1} required value={calendar.interval_count} onChange={(event) => setCalendar({ ...calendar, interval_count: event.target.value })} /><Select label="Interval unit" name="interval_unit" value={calendar.interval_unit} onChange={(event) => setCalendar({ ...calendar, interval_unit: event.target.value as IntervalUnit })}><option value="day">Days</option><option value="week">Weeks</option><option value="month">Months</option></Select></div>
        <button type="button" className="button secondary" disabled={!calendarValid || preview.isPending} onClick={() => preview.mutate(calendarPayload)}>{preview.isPending ? "Calculating dates…" : "Preview dates"}</button>
        <ErrorNotice error={preview.error} />
        {currentPreview ? <section className="schedule-preview" aria-label="Server calendar preview" aria-live="polite"><h3>Resolved dates</h3>{currentPreview.dates.length ? <ol>{currentPreview.dates.map((date) => <li key={date.scheduled_at}><LocalDate local={date.scheduled_local} zone={date.timezone} utc={date.scheduled_at} /></li>)}</ol> : <p>No dates were returned. Recheck the schedule before saving.</p>}<dl>{Object.entries(currentPreview.policy).map(([name, policy]) => <div key={name}><dt>{plainStatus(name)}</dt><dd>{plainStatus(policy)}</dd></div>)}</dl></section> : <p className="muted">Preview the current schedule before saving. Month ends and daylight-saving changes are resolved by the server.</p>}
      </div></fieldset>
      <Field label="Email reminder lead (hours)" name="reminder_hours" type="number" defaultValue={plan?.reminder_hours ?? 24} min={0} max={72} step={1} required hint="One assignee reminder before a generated job is due. Email acceptance is not proof the person received it." />
      <Select label="Overdue escalation manager" name="escalation_member_id" value={escalation} onChange={(event) => setEscalation(event.target.value)} disabled={members.isPending || !!members.error} hint="Optional: one escalation 24 hours after the due date."><option value="">No email escalation</option>{plan?.escalation_member_id && !managers.some((member) => member.id === plan.escalation_member_id) && <option value={plan.escalation_member_id}>Previous manager / no longer eligible</option>}{managers.map((member) => <option key={member.id} value={member.id}>{member.name} ({member.role})</option>)}</Select>
      <fieldset className="checklist-editor"><legend>Work checklist</legend><p className="muted">Optional. Added steps must be completed before job submission.</p>{steps.map((text, index) => <div className="checklist-editor-row" key={index}><Field label={`Step ${index + 1}`} value={text} maxLength={500} onChange={(event) => setSteps((items) => items.map((item, position) => position === index ? event.target.value : item))} /><button type="button" className="button secondary small" aria-label={`Remove step ${index + 1}`} onClick={() => setSteps((items) => items.filter((_, position) => position !== index))}>Remove</button></div>)}<button className="button secondary small" type="button" disabled={steps.length >= 100} onClick={() => setSteps((items) => [...items, ""])}><Plus size={16} aria-hidden />Add step</button></fieldset>
      <ErrorNotice error={save.error} /><ConflictRefresh error={save.error} onClose={onClose} />
      <div className="form-actions"><button className="button secondary" type="button" onClick={onClose} disabled={save.isPending}>Cancel</button><button className="button primary" type="submit" disabled={cannotSave}>{save.isPending ? "Saving…" : plan ? "Save plan" : "Create plan"}</button></div>
    </Form>
  </Dialog>;
}
export function Preventive() {
  const identity = useIdentity().data!;
  const [params, setParams] = useSearchParams();
  const [search, setSearch] = useState("");
  const asset = params.get("asset_id") || "";
  const plans = useResource<{ plans: MaintenancePlan[] }>(["maintenance-plans", asset], `/maintenance-plans${queryString({ asset_id: asset })}`);
  const filtered = plans.data?.plans.filter((plan) => `${plan.title} ${plan.asset_name} ${plan.assignee_name || ""}`.toLowerCase().includes(search.toLowerCase())) || [];
  function close() { const next = new URLSearchParams(params); next.delete("new"); setParams(next, { replace: true }); }
  return <><PageHeader eyebrow="Calendar / responsibility / history" title="Preventive plans" description="Recurring tasks anchored to your plant's calendar. People still perform and review the work." actions={can(identity, "manage_preventive_maintenance") && <button className="button primary" onClick={() => { const next = new URLSearchParams(params); next.set("new", "1"); setParams(next); }}><Plus size={18} aria-hidden />Create preventive plan</button>} /><MaintenanceTabs />
    <div className="toolbar"><label className="search-field"><Search size={19} aria-hidden /><span className="sr-only">Search preventive plans</span><input type="search" placeholder="Search plans or machines" value={search} onChange={(event) => setSearch(event.target.value)} /></label>{asset && <Link className="button secondary" to="/app/maintenance/plans">Clear machine filter</Link>}</div>
    {plans.isPending ? <Loading label="Loading preventive plans…" /> : plans.error ? <ErrorNotice error={plans.error} retry={() => void plans.refetch()} /> : !filtered.length ? <section className="panel"><Empty title={search ? "No plans match this search" : "No preventive plans recorded"}>{search ? "Change the search to see other plans." : "Create a fixed calendar task for a recorded machine. No jobs or reminders are invented here."}</Empty></section> : <section className="panel"><div className="table-wrap responsive-records"><table><thead><tr><th>Plan</th><th>Machine</th><th>Schedule</th><th>Assigned person</th><th>Next due</th><th>State</th></tr></thead><tbody>{filtered.map((plan) => <tr key={plan.id}><td data-label="Plan"><Link className="record-name" to={`/app/maintenance/plans/${plan.id}`}><strong>{plan.title}</strong><span>Generation {plan.generation}</span></Link></td><td data-label="Machine"><Link to={`/app/machines/${plan.asset_id}`}>{plan.asset_name}</Link></td><td data-label="Schedule">{cadence(plan)}</td><td data-label="Assigned person">{plan.assignee_name || "Needs assignment"}</td><td data-label="Next due"><LocalDate local={plan.next_due_local} zone={plan.timezone} /></td><td data-label="State"><Status value={plan.enabled ? "active" : "paused"} />{plan.blocked_reason && <small className="overdue">{plainStatus(plan.blocked_reason)}</small>}</td></tr>)}</tbody></table></div></section>}
    {params.get("new") === "1" && can(identity, "manage_preventive_maintenance") && <PlanForm identity={identity} initialAsset={asset} onClose={close} />}
  </>;
}
function PlanStateDialog({ plan, onClose }: { plan: MaintenancePlan; onClose: () => void }) {
  const action = plan.enabled ? "pause" : "resume";
  const save = useAction((form: FormData) => mutate(`/maintenance-plans/${plan.id}/${action}`, { revision: plan.revision, reason: value(form, "reason") }), plan.enabled ? "Plan paused. Existing jobs remain." : "Plan resumed. Paused periods are not replayed.", onClose);
  return <Dialog title={plan.enabled ? "Pause preventive plan" : "Resume preventive plan"} onClose={onClose} dismissible={!save.isPending}><p className="form-intro">{plan.title}</p><p className="notice">{plan.enabled ? "New occurrences and unsent reminders stop. Existing jobs remain and must still be handled. Email already being sent cannot be recalled." : "Paused periods are skipped and recorded in history. Cancelled emails and jobs are not resurrected."}</p><Form onSubmit={(form) => save.mutate(form)}><Textarea label="Reason" name="reason" required maxLength={1000} /><ErrorNotice error={save.error} /><ConflictRefresh error={save.error} onClose={onClose} /><div className="form-actions"><button className="button secondary" type="button" onClick={onClose} disabled={save.isPending}>Back</button><Submit pending={save.isPending}>Confirm {action}</Submit></div></Form></Dialog>;
}
function ReminderDialog({ reminder, action, onClose }: { reminder: MaintenanceReminder; action: "retry" | "ack"; onClose: () => void }) {
  const save = useAction((form: FormData) => mutate(`/maintenance-reminders/${reminder.id}/${action}`, action === "retry" ? { reason: value(form, "reason") } : {}), action === "retry" ? "Reminder retry requested; delivery is not yet confirmed." : "Reminder acknowledged. Work status is unchanged.", onClose);
  return <Dialog title={action === "retry" ? "Retry failed reminder" : "Acknowledge reminder"} onClose={onClose} dismissible={!save.isPending}><p className="form-intro">{reminder.recipient_name || "No eligible recipient recorded"} / {plainStatus(reminder.stage)} reminder</p><p className="notice">{action === "retry" ? "The server rechecks the current plan, job, and recipient before retrying a terminal failure. Accepted or cancelled mail cannot be retried." : "Only the recipient or a factory manager may acknowledge this reminder. Acknowledgment records attention, not email receipt, work completion, or approval."}</p><Form onSubmit={(form) => save.mutate(form)}>{action === "retry" && <Textarea label="Reason for retry" name="reason" required maxLength={1000} />}<ErrorNotice error={save.error} /><div className="form-actions"><button type="button" className="button secondary" disabled={save.isPending} onClick={onClose}>Back</button><Submit pending={save.isPending}>{action === "retry" ? "Request retry" : "Confirm acknowledgment"}</Submit></div></Form></Dialog>;
}
export function PlanDetail() {
  const { id } = useParams();
  const identity = useIdentity().data!;
  const record = useResource<PlanRecord>(["maintenance-plan", id], `/maintenance-plans/${id}`);
  const [edit, setEdit] = useState(false);
  const [changeState, setChangeState] = useState(false);
  const [reminderAction, setReminderAction] = useState<{ reminder: MaintenanceReminder; action: "ack" | "retry" } | null>(null);
  if (record.isPending) return <Loading label="Loading preventive plan…" />;
  if (record.error) return <ErrorNotice error={record.error} retry={() => void record.refetch()} />;
  const { plan, occurrences, reminders, events } = record.data!;
  const manager = can(identity, "manage_preventive_maintenance");
  return <><Link className="back-link" to="/app/maintenance/plans"><ArrowLeft size={16} aria-hidden />All preventive plans</Link><PageHeader eyebrow={`Preventive plan / generation ${plan.generation}`} title={plan.title} description={plan.asset_name} actions={manager && <><button className="button secondary" onClick={() => setEdit(true)}>Edit plan</button><button className="button secondary" onClick={() => setChangeState(true)}>{plan.enabled ? "Pause plan" : "Resume plan"}</button></>} /><MaintenanceTabs />
    <div className="job-state-bar"><Status value={plan.enabled ? "active" : "paused"} /><Status value={plan.priority} /><span>{cadence(plan)}</span></div>{plan.blocked_reason && <div className="notice warning">Plan needs attention: {plainStatus(plan.blocked_reason)}. Existing work is not automatically completed.</div>}
    <div className="detail-columns"><section className="panel"><div className="section-heading"><h2>Work instructions</h2></div><div className="record-body"><p className="preserve-lines">{plan.description || "No additional work instructions recorded."}</p><h3>Checklist for future jobs</h3>{plan.checklist.length ? <ol className="plan-checklist">{plan.checklist.map((step, index) => <li key={index}>{step.text}</li>)}</ol> : <p className="muted">No checklist steps recorded.</p>}<p className="muted">One unfinished generated job at a time, including jobs awaiting review. Completion does not move the calendar anchor.</p></div></section><aside className="panel"><div className="section-heading"><h2>Schedule details</h2></div><Definition items={[["Machine", <Link to={`/app/machines/${plan.asset_id}`}>{plan.asset_name}</Link>], ["Assigned person", plan.assignee_name || "Needs assignment"], ["First local due", <LocalDate local={plan.start_local} zone={plan.timezone} />], ["Next due", <LocalDate local={plan.next_due_local} zone={plan.timezone} utc={plan.next_due_at} />], ["Reminder lead", `${plan.reminder_hours} hours`], ["Escalation", plan.escalation_member_id ? "Selected manager / 24 hours overdue" : "No email escalation"], ["Created", dateLabel(plan.created_at, true)]]} /></aside></div>
    <section className="panel"><div className="section-heading"><h2>Occurrences & linked jobs</h2></div>{occurrences.length ? <ul className="record-cards occurrence-list">{occurrences.map((item) => <li key={item.id}><LocalDate local={item.scheduled_local} zone={item.generation === plan.generation ? plan.timezone : "captured local time / historical zone not provided"} utc={item.scheduled_at} /><p className="muted">Schedule generation {item.generation}</p>{item.missed_count > 0 && <p className="notice warning">{item.missed_count} missed calendar slots summarized{item.missed_from && item.missed_through ? ` / ${dateLabel(item.missed_from, true)} to ${dateLabel(item.missed_through, true)} (device time)` : ""}. No completion is inferred.</p>}{item.work_order_id ? <Link className="button secondary" to={`/app/maintenance/${item.work_order_id}`}>Open job #{item.work_order_id}</Link> : <p>No linked job returned.</p>}</li>)}</ul> : <Empty title="No occurrences recorded yet">The scheduler creates eligible work within the reminder horizon. This page does not simulate a scheduler run.</Empty>}</section>
    <section className="panel"><div className="section-heading"><h2>Reminder history</h2></div><p className="record-body muted reminder-explanation">SMTP acceptance does not prove human receipt. Acknowledgment does not complete or approve maintenance. Only the recipient or a manager can acknowledge; the server checks permission.</p>{reminders.length ? <ul className="record-cards">{reminders.map((reminder) => <li key={reminder.id}><h3>{plainStatus(reminder.stage)} reminder / {reminder.recipient_name || "Needs eligible recipient"}</h3><p><strong>{reminder.state === "accepted" ? "SMTP accepted" : plainStatus(reminder.state)}</strong></p><Definition items={[["Scheduled", `${dateLabel(reminder.scheduled_at, true)} (device time)`], ["Mail accepted", reminder.accepted_at ? `${dateLabel(reminder.accepted_at, true)} (device time)` : "Not recorded"], ["Acknowledged", reminder.acknowledged_at ? `${dateLabel(reminder.acknowledged_at, true)} (device time)` : "Not acknowledged"], ["Attempts", String(reminder.attempts)]]} />{reminder.error && <p className="notice error">{reminder.error}</p>}<div className="form-actions record-actions"><Link className="button secondary" to={`/app/maintenance/${reminder.work_order_id}`}>View job #{reminder.work_order_id}</Link>{(manager || can(identity, "request_work_orders")) && !reminder.acknowledged_at && reminder.state !== "cancelled" && <button className="button secondary" aria-label={`Acknowledge reminder ${reminder.id}`} onClick={() => setReminderAction({ reminder, action: "ack" })}>Acknowledge</button>}{manager && reminder.state === "failed" && <button className="button secondary" aria-label={`Retry reminder ${reminder.id}`} onClick={() => setReminderAction({ reminder, action: "retry" })}>Retry failed reminder</button>}</div></li>)}</ul> : <Empty title="No reminders recorded">Delivery and acknowledgment history appears only when the server has real reminder records.</Empty>}</section>
    <section className="panel"><div className="section-heading"><h2>Plan history</h2></div>{events.length ? <ol className="event-list">{events.map((event) => <li key={event.id}><span className="event-marker" aria-hidden /><div><strong>{plainStatus(event.action)} <span className="muted">by {event.actor_name}</span></strong>{event.notes && <p className="preserve-lines">{event.notes}</p>}<time dateTime={event.created_at}>{dateLabel(event.created_at, true)} (device time)</time></div></li>)}</ol> : <Empty title="No plan events returned">Refresh to check the permanent plan record.</Empty>}</section>
    {edit && manager && <PlanForm key={plan.revision} identity={identity} plan={plan} onClose={() => setEdit(false)} />}{changeState && manager && <PlanStateDialog plan={plan} onClose={() => setChangeState(false)} />}{reminderAction && <ReminderDialog {...reminderAction} onClose={() => setReminderAction(null)} />}
  </>;
}
