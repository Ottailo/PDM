import { useState } from "react";
import {
  Link,
  useNavigate,
  useParams,
  useSearchParams,
} from "react-router-dom";
import {
  ArrowLeft,
  ArrowUpRight,
  Check,
  ClipboardList,
  Download,
  LayoutList,
  Columns3,
  Pencil,
  Plus,
  Search,
} from "lucide-react";
import { ApiError, download, mutate, queryString } from "./api";
import { MaintenanceTabs } from "./Preventive";
import { refreshData, useIdentity, useResource } from "./query";
import {
  availableActions,
  can,
  dateLabel,
  deviceTimezone,
  jobDateLabel,
  isOverdue,
  plainStatus,
} from "./permissions";
import type {
  Asset,
  Identity,
  JobAction,
  JobEvent,
  Member,
  WorkOrder,
} from "./types";
import {
  Definition,
  Dialog,
  Empty,
  ErrorNotice,
  Field,
  Form,
  Loading,
  numeric,
  PageHeader,
  Select,
  Status,
  Submit,
  Textarea,
  useAction,
  value,
} from "./ui";

const statuses = [
  "open",
  "assigned",
  "in_progress",
  "blocked",
  "awaiting_review",
  "completed",
  "cancelled",
];
const actionLabels: Record<JobAction, string> = {
  start: "Start work",
  block: "Mark blocked",
  resume: "Resume work",
  submit: "Submit for review",
  approve: "Approve completion",
  cancel: "Cancel job",
  reopen: "Reopen job",
};
function MembersSelect({
  members,
  defaultValue = "",
  required = false,
}: {
  members?: Member[];
  defaultValue?: number | string;
  required?: boolean;
}) {
  const [selectedMember, setSelectedMember] = useState(String(defaultValue));
  return (
    <Select
      label="Assigned person"
      name="assignee_id"
      value={selectedMember}
      onChange={(event) => setSelectedMember(event.target.value)}
      required={required}
    >
      <option value="">Unassigned</option>
      {members
        ?.filter((member) =>
          ["owner", "admin", "planner", "technician"].includes(member.role),
        )
        .map((member) => (
          <option key={member.id} value={member.id}>
            {member.name} ({member.role})
          </option>
        ))}
    </Select>
  );
}
function PrioritySelect({ value = "medium" }: { value?: string }) {
  return (
    <Select label="Priority" name="priority" defaultValue={value}>
      <option value="low">Low</option>
      <option value="medium">Medium</option>
      <option value="high">High</option>
      <option value="urgent">Urgent</option>
    </Select>
  );
}
function dueValue(date: string | null) {
  if (!date) return "";
  const local = new Date(date);
  local.setMinutes(local.getMinutes() - local.getTimezoneOffset());
  return local.toISOString().slice(0, 16);
}
function duePayload(form: FormData) {
  const raw = value(form, "due_at");
  return raw ? new Date(raw).toISOString() : null;
}
function JobForm({
  identity,
  initialAsset,
  onClose,
}: {
  identity: Identity;
  initialAsset: string;
  onClose: () => void;
}) {
  const navigate = useNavigate();
  const manager = can(identity, "manage_work_orders");
  const assets = useResource<{ assets: Asset[] }>(
    ["assets", "job-form"],
    "/assets",
  );
  const members = useResource<{ members: Member[] }>(
    ["members"],
    "/members",
    manager,
  );
  const [steps, setSteps] = useState<string[]>([""]);
  const [selectedAsset, setSelectedAsset] = useState(initialAsset);
  const create = useAction(
    (form: FormData) =>
      mutate<{ work_order: WorkOrder }>("/work-orders", {
        asset_id: numeric(form, "asset_id"),
        title: value(form, "title"),
        description: value(form, "description"),
        priority: value(form, "priority"),
        due_at: duePayload(form),
        ...(manager ? { assignee_id: numeric(form, "assignee_id") } : {}),
        checklist: steps
          .filter((step) => step.trim())
          .map((text) => ({ text: text.trim() })),
      }),
    "Maintenance job created.",
    (data) => {
      onClose();
      navigate(`/app/maintenance/${data.work_order.id}`);
    },
  );
  return (
    <Dialog title="Create a maintenance job" onClose={onClose}>
      <p className="form-intro">
        Give the next person a clear task, the right machine, and the steps to
        finish it.
      </p>
      <Form onSubmit={(form) => create.mutate(form)}>
        <Select
          label="Machine"
          name="asset_id"
          value={selectedAsset}
          onChange={(event) => setSelectedAsset(event.target.value)}
          required
          disabled={assets.isPending || !!assets.error}
        >
          <option value="">Choose a machine</option>
          {assets.data?.assets.map((asset) => (
            <option key={asset.id} value={asset.id}>
              {asset.code} / {asset.name}
            </option>
          ))}
        </Select>
        <ErrorNotice error={assets.error} retry={() => void assets.refetch()} />
        {assets.data?.assets.length === 0 && (
          <p className="notice">
            Record a machine before creating a job.{" "}
            <Link to="/app/machines">Open machines</Link>
          </p>
        )}
        <Field label="Job title" name="title" required maxLength={200} />
        <Textarea
          label="Work description"
          name="description"
          maxLength={10000}
        />
        <div className="form-grid">
          <PrioritySelect />
          <Field
            label="Due date and time"
            name="due_at"
            type="datetime-local"
            hint={`Entered in this device's time zone: ${deviceTimezone()}.`}
          />
        </div>
        {manager && (
          <>
            <MembersSelect members={members.data?.members} />
            <ErrorNotice
              error={members.error}
              retry={() => void members.refetch()}
            />
          </>
        )}
        <fieldset className="checklist-editor">
          <legend>Checklist</legend>
          <p className="muted">
            Optional. Every added step must be completed before submission.
          </p>
          {steps.map((step, index) => (
            <div key={index} className="checklist-editor-row">
              <Field
                label={`Step ${index + 1}`}
                value={step}
                maxLength={500}
                onChange={(event) =>
                  setSteps((current) =>
                    current.map((item, position) =>
                      position === index ? event.target.value : item,
                    ),
                  )
                }
              />
              <button
                className="button secondary small"
                type="button"
                aria-label={`Remove step ${index + 1}`}
                onClick={() =>
                  setSteps((current) =>
                    current.filter((_, position) => position !== index),
                  )
                }
              >
                Remove
              </button>
            </div>
          ))}
          <button
            className="button secondary small"
            type="button"
            disabled={steps.length >= 100}
            onClick={() => setSteps((current) => [...current, ""])}
          >
            <Plus size={16} aria-hidden />
            Add step
          </button>
        </fieldset>
        <ErrorNotice error={create.error} />
        <div className="form-actions">
          <button className="button secondary" type="button" onClick={onClose}>
            Cancel
          </button>
          <Submit pending={create.isPending}>Create job</Submit>
        </div>
      </Form>
    </Dialog>
  );
}
export function Maintenance() {
  const identity = useIdentity().data!;
  const [params, setParams] = useSearchParams();
  const [view, setView] = useState<"list" | "board">("list");
  const [search, setSearch] = useState("");
  const status = params.get("status") || "";
  const mine = params.get("assigned_to_me") === "true";
  const overdue = params.get("overdue") === "1";
  const jobs = useResource<{ work_orders: WorkOrder[] }>(
    ["work-orders", status, mine],
    `/work-orders${queryString({ status, assigned_to_me: mine })}`,
  );
  const filtered =
    jobs.data?.work_orders.filter(
      (job) =>
        (!overdue || isOverdue(job)) &&
        `${job.number} ${job.title} ${job.asset_name} ${job.assignee_name || ""}`
          .toLowerCase()
          .includes(search.toLowerCase()),
    ) || [];
  function filter(name: string, value: string) {
    const next = new URLSearchParams(params);
    if (value) next.set(name, value);
    else next.delete(name);
    setParams(next, { replace: true });
  }
  return (
    <>
      <PageHeader
        eyebrow="Plan / carry out / review"
        title="Maintenance"
        description="Clear tasks. Named responsibility. A record of what happened."
        actions={
          can(identity, "request_work_orders") && (
            <button
              className="button primary"
              onClick={() => filter("new", "1")}
            >
              <Plus size={18} aria-hidden />
              Create job
            </button>
          )
        }
      />
      <MaintenanceTabs />
      <div className="toolbar">
        <label className="search-field">
          <Search size={19} aria-hidden />
          <span className="sr-only">Search maintenance jobs</span>
          <input
            type="search"
            placeholder="Search jobs or machines"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </label>
        <Select
          label="Status"
          value={status}
          onChange={(event) => filter("status", event.target.value)}
        >
          <option value="">All statuses</option>
          {statuses.map((status) => (
            <option key={status} value={status}>
              {plainStatus(status)}
            </option>
          ))}
        </Select>
        <label className="check-row">
          <input
            type="checkbox"
            checked={mine}
            onChange={(event) =>
              filter("assigned_to_me", event.target.checked ? "true" : "")
            }
          />
          Assigned to me
        </label>
        <label className="check-row">
          <input
            type="checkbox"
            checked={overdue}
            onChange={(event) =>
              filter("overdue", event.target.checked ? "1" : "")
            }
          />
          Overdue only
        </label>
        <div className="view-switch" aria-label="Maintenance view">
          <button
            aria-pressed={view === "list"}
            aria-label="List view"
            onClick={() => setView("list")}
          >
            <LayoutList size={19} />
          </button>
          <button
            aria-pressed={view === "board"}
            aria-label="Board view"
            onClick={() => setView("board")}
          >
            <Columns3 size={19} />
          </button>
        </div>
      </div>
      {jobs.isPending ? (
        <Loading label="Loading maintenance jobs…" />
      ) : jobs.error ? (
        <ErrorNotice error={jobs.error} retry={() => void jobs.refetch()} />
      ) : !filtered.length ? (
        <section className="panel">
          <Empty
            title={
              status || mine || overdue || search
                ? "No jobs match this view"
                : "The first job starts a useful history"
            }
            action={
              can(identity, "request_work_orders") && (
                <button
                  className="button primary"
                  onClick={() => filter("new", "1")}
                >
                  Create a maintenance job
                </button>
              )
            }
          >
            {status || mine || overdue || search
              ? "Change your filters to see other jobs."
              : "Record a task for a machine, assign the work, and keep the completion record."}
          </Empty>
        </section>
      ) : view === "list" ? (
        <section className="panel">
          <div className="table-wrap responsive-records">
            <table>
              <thead>
                <tr>
                  <th>Job</th>
                  <th>Machine</th>
                  <th>Assigned to</th>
                  <th>Due</th>
                  <th>Priority</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((job) => (
                  <tr key={job.id}>
                    <td data-label="Job">
                      <Link
                        className="record-name"
                        to={`/app/maintenance/${job.id}`}
                      >
                        <strong>{job.title}</strong>
                        <span>{job.number}</span>
                      </Link>
                    </td>
                    <td data-label="Machine">
                      <Link to={`/app/machines/${job.asset_id}`}>
                        {job.asset_name}
                      </Link>
                    </td>
                    <td data-label="Assigned to">{job.assignee_name || "Unassigned"}</td>
                    <td data-label="Due" className={isOverdue(job) ? "overdue" : ""}>
                      {jobDateLabel(job.due_at)}
                      {isOverdue(job) && <small>Overdue</small>}
                    </td>
                    <td data-label="Priority">
                      <Status value={job.priority} />
                    </td>
                    <td data-label="Status">
                      <Status value={job.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : (
        <div className="board">
          {(status ? [status] : statuses).map((stage) => {
            const stageJobs = filtered.filter((job) => job.status === stage);
            return (
              <section className="board-column" key={stage}>
                <h2>
                  {plainStatus(stage)}
                  <span>{stageJobs.length}</span>
                </h2>
                {stageJobs.length ? (
                  stageJobs.map((job) => (
                    <Link
                      className="board-card"
                      to={`/app/maintenance/${job.id}`}
                      key={job.id}
                    >
                      <span className="eyebrow">{job.number}</span>
                      <h3>{job.title}</h3>
                      <p>{job.asset_name}</p>
                      <div>
                        <Status value={job.priority} />
                        <ArrowUpRight size={17} aria-hidden />
                      </div>
                      <small>{job.assignee_name || "Unassigned"}</small>
                      <small className={isOverdue(job) ? "overdue" : ""}>
                        {job.due_at
                          ? `Due ${jobDateLabel(job.due_at)}`
                          : "No due date"}
                      </small>
                    </Link>
                  ))
                ) : (
                  <p className="board-empty">No jobs in this stage.</p>
                )}
              </section>
            );
          })}
        </div>
      )}
      {params.get("new") === "1" && can(identity, "request_work_orders") && (
        <JobForm
          identity={identity}
          initialAsset={params.get("asset_id") || ""}
          onClose={() => filter("new", "")}
        />
      )}
    </>
  );
}
function AssignmentForm({
  job,
  onClose,
}: {
  job: WorkOrder;
  onClose: () => void;
}) {
  const members = useResource<{ members: Member[] }>(["members"], "/members");
  const save = useAction(
    (data: FormData) =>
      mutate(
        `/work-orders/${job.id}`,
        {
          revision: job.revision,
          assignee_id: numeric(data, "assignee_id"),
          due_at: duePayload(data),
          priority: value(data, "priority"),
        },
        "PATCH",
      ),
    "Job assignment updated.",
    onClose,
  );
  return (
    <Dialog title="Plan this job" onClose={onClose}>
      <Form onSubmit={(data) => save.mutate(data)}>
        <MembersSelect
          members={members.data?.members}
          defaultValue={job.assignee_id || ""}
        />
        <ErrorNotice
          error={members.error}
          retry={() => void members.refetch()}
        />
        <PrioritySelect value={job.priority} />
        <Field
          label="Due date and time"
          name="due_at"
          type="datetime-local"
          defaultValue={dueValue(job.due_at)}
          hint={`Entered in this device's time zone: ${deviceTimezone()}.`}
        />
        <ErrorNotice error={save.error} />
        {save.error instanceof ApiError &&
          save.error.code === "revision_conflict" && (
            <button
              className="button secondary"
              type="button"
              onClick={() => {
                onClose();
                void refreshData();
              }}
            >
              Close and refresh record
            </button>
          )}
        <Submit pending={save.isPending}>Save plan</Submit>
      </Form>
    </Dialog>
  );
}
function TransitionForm({
  job,
  action,
  onClose,
}: {
  job: WorkOrder;
  action: JobAction;
  onClose: () => void;
}) {
  const [checklist, setChecklist] = useState(
    job.checklist.map((item) => ({
      text: item.text,
      completed: item.completed,
    })),
  );
  const required = ["block", "submit", "cancel", "reopen"].includes(action);
  const save = useAction(
    (form: FormData) =>
      mutate(`/work-orders/${job.id}/transition`, {
        revision: job.revision,
        action,
        notes: value(form, "notes"),
        ...(["submit", "block"].includes(action) ? { checklist } : {}),
        ...(action === "submit"
          ? { labor_minutes: numeric(form, "labor_minutes") || 0 }
          : {}),
      }),
    `Job ${action === "submit" ? "submitted for review" : action === "approve" ? "approved" : action === "start" ? "started" : action === "resume" ? "resumed" : action === "block" ? "marked blocked" : action === "cancel" ? "cancelled" : "reopened"}.`,
    onClose,
  );
  return (
    <Dialog title={actionLabels[action]} onClose={onClose}>
      <p className="form-intro">
        {job.number} / {job.title}
      </p>
      {action === "approve" && (
        <div className="notice">
          <p>
            Review the completion notes and checklist before approving. Approval
            records this job as completed.
          </p>
        </div>
      )}
      {action === "reopen" && (
        <div className="notice warning">
          Reopening removes the current assignment and resets the checklist. The
          previous completion remains in the job record.
        </div>
      )}
      <Form onSubmit={(form) => save.mutate(form)}>
        {["submit", "block"].includes(action) && checklist.length > 0 && (
          <fieldset className="job-checklist">
            <legend>Work checklist</legend>
            {checklist.map((item, index) => (
              <label className="check-row" key={index}>
                <input
                  type="checkbox"
                  checked={item.completed}
                  onChange={(event) =>
                    setChecklist((current) =>
                      current.map((step, position) =>
                        position === index
                          ? { ...step, completed: event.target.checked }
                          : step,
                      ),
                    )
                  }
                />
                {item.text}
              </label>
            ))}
            <p className="muted">
              Checklist changes are saved with this action, not while ticking
              boxes.
            </p>
          </fieldset>
        )}
        <Textarea
          label={
            action === "submit"
              ? "Completion notes"
              : action === "block"
                ? "What is blocking the work?"
                : action === "cancel" || action === "reopen"
                  ? "Reason"
                  : "Notes"
          }
          name="notes"
          required={required}
          maxLength={10000}
          hint={
            required
              ? "This note becomes part of the permanent job record."
              : "Optional. Add useful context for the next shift."
          }
        />
        {action === "submit" && (
          <Field
            label="Time spent (minutes)"
            name="labor_minutes"
            type="number"
            min={0}
            max={525600}
            step={1}
            defaultValue={job.labor_minutes || 0}
            required
          />
        )}
        <ErrorNotice error={save.error} />
        {save.error instanceof ApiError &&
          save.error.code === "revision_conflict" && (
            <button
              className="button secondary"
              type="button"
              onClick={() => {
                onClose();
                void refreshData();
              }}
            >
              Close and refresh record
            </button>
          )}
        <div className="form-actions">
          <button type="button" className="button secondary" onClick={onClose}>
            Back
          </button>
          <button
            className={`button ${action === "cancel" ? "danger" : "primary"}`}
            type="submit"
            disabled={
              save.isPending ||
              (action === "submit" && checklist.some((item) => !item.completed))
            }
          >
            {save.isPending ? "Saving…" : actionLabels[action]}
          </button>
        </div>
        {action === "submit" && checklist.some((item) => !item.completed) && (
          <p className="muted">
            Complete every checklist step to submit for review.
          </p>
        )}
      </Form>
    </Dialog>
  );
}
export function JobDetail() {
  const { id } = useParams();
  const identity = useIdentity().data!;
  const [action, setAction] = useState<JobAction | null>(null);
  const [edit, setEdit] = useState(false);
  const record = useResource<{ work_order: WorkOrder; events: JobEvent[] }>(
    ["work-order", id],
    `/work-orders/${id}`,
  );
  const exportJob = useAction(
    () => download(`/work-orders/${id}/export`, `work-order-${id}.csv`),
    "Job record downloaded.",
  );
  if (record.isPending) return <Loading label="Loading job record…" />;
  if (record.error)
    return (
      <ErrorNotice error={record.error} retry={() => void record.refetch()} />
    );
  const job = record.data!.work_order;
  const actions = availableActions(job, identity);
  return (
    <>
      <Link className="back-link" to="/app/maintenance">
        <ArrowLeft size={16} aria-hidden />
        All maintenance
      </Link>
      <PageHeader
        eyebrow={job.number}
        title={job.title}
        description={job.asset_name}
        actions={
          <>
            <button
              className="button secondary"
              disabled={exportJob.isPending}
              onClick={() => exportJob.mutate()}
            >
              <Download size={17} aria-hidden />
              Export record
            </button>
            {can(identity, "manage_work_orders") &&
              !["completed", "cancelled", "awaiting_review"].includes(
                job.status,
              ) && (
                <button
                  className="button secondary"
                  onClick={() => setEdit(true)}
                >
                  <Pencil size={17} aria-hidden />
                  Plan & assign
                </button>
              )}
          </>
        }
      />
      <ErrorNotice error={exportJob.error} />
      {job.plan_id && <p className="notice">Generated from a preventive plan. <Link to={`/app/maintenance/plans/${job.plan_id}`}>View preventive plan</Link></p>}
      <div className="job-state-bar">
        <Status value={job.status} />
        <Status value={job.priority} />
        <span className={isOverdue(job) ? "overdue" : "muted"}>
          {job.due_at
            ? `Due ${jobDateLabel(job.due_at, true)}${isOverdue(job) ? " / Overdue" : ""}`
            : "No due date"}
        </span>
        <div className="job-actions">
          {actions.map((item) => (
            <button
              className={`button ${["start", "submit", "approve", "resume"].includes(item) ? "primary" : "secondary"} small`}
              key={item}
              onClick={() => setAction(item)}
            >
              {actionLabels[item]}
            </button>
          ))}
        </div>
      </div>
      {!job.assignee_id && ["open", "assigned"].includes(job.status) && (
        <div className="notice">
          <ClipboardList size={20} aria-hidden />
          <p>
            Assign this job before starting work. Only the assigned person can
            start, block, resume, or submit it.
          </p>
        </div>
      )}
      <div className="detail-columns">
        <section className="panel">
          <div className="section-heading">
            <h2>Work instructions</h2>
          </div>
          <div className="record-body">
            <p className="preserve-lines">
              {job.description ||
                "No additional work description was recorded."}
            </p>
            <h3>Checklist</h3>
            {job.checklist.length ? (
              <ul className="read-checklist">
                {job.checklist.map((item, index) => (
                  <li key={index}>
                    <span
                      className={`check-box ${item.completed ? "checked" : ""}`}
                      aria-label={
                        item.completed ? "Completed" : "Not completed"
                      }
                    >
                      {item.completed && <Check size={15} />}
                    </span>
                    {item.text}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="muted">
                No checklist steps were added to this job.
              </p>
            )}
            {job.completion_notes && (
              <>
                <h3>Completion notes</h3>
                <p className="preserve-lines">{job.completion_notes}</p>
              </>
            )}
            {job.notes && job.notes !== job.completion_notes && (
              <>
                <h3>Latest note</h3>
                <p className="preserve-lines">{job.notes}</p>
              </>
            )}
          </div>
        </section>
        <aside className="panel">
          <div className="section-heading">
            <h2>Job details</h2>
          </div>
          <Definition
            items={[
              [
                "Machine",
                <Link to={`/app/machines/${job.asset_id}`}>
                  {job.asset_name}
                </Link>,
              ],
              ["Assigned person", job.assignee_name || "Unassigned"],
              ["Created", dateLabel(job.created_at, true)],
              ["Due", jobDateLabel(job.due_at, true)],
              [
                "Completed",
                job.completed_at
                  ? dateLabel(job.completed_at, true)
                  : "Not completed",
              ],
              ["Time recorded", `${job.labor_minutes || 0} minutes`],
            ]}
          />
        </aside>
      </div>
      <section className="panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Permanent work record</p>
            <h2>What happened</h2>
          </div>
        </div>
        {record.data!.events.length ? (
          <ol className="event-list">
            {record.data!.events.map((event) => (
              <li key={event.id}>
                <span className="event-marker" aria-hidden />
                <div>
                  <strong>
                    {plainStatus(event.action)}{" "}
                    <span className="muted">by {event.actor_name}</span>
                  </strong>
                  <p>
                    {event.from_status
                      ? `${plainStatus(event.from_status)} → `
                      : ""}
                    {plainStatus(event.to_status)}
                  </p>
                  {event.notes && (
                    <p className="preserve-lines">{event.notes}</p>
                  )}
                  <time dateTime={event.created_at}>
                    {dateLabel(event.created_at, true)}
                  </time>
                </div>
              </li>
            ))}
          </ol>
        ) : (
          <Empty title="No events returned">
            Refresh to check the job’s chronological record.
          </Empty>
        )}
      </section>
      {edit && <AssignmentForm job={job} onClose={() => setEdit(false)} />}
      {action && (
        <TransitionForm
          key={`${job.revision}-${action}`}
          job={job}
          action={action}
          onClose={() => setAction(null)}
        />
      )}
    </>
  );
}
