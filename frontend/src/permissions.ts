import type { Identity, JobAction, WorkOrder } from "./types";
export function can(identity: Identity, capability: string): boolean {
  const values = identity.capabilities;
  return Array.isArray(values)
    ? values.includes(capability)
    : values?.[capability] === true;
}
export function availableActions(
  job: WorkOrder,
  identity: Identity,
): JobAction[] {
  const manager = can(identity, "manage_work_orders");
  const operator =
    can(identity, "request_work_orders") &&
    job.assignee_id === identity.membership.id;
  const actions: JobAction[] = [];
  if (operator && ["open", "assigned"].includes(job.status))
    actions.push("start");
  if (operator && job.status === "in_progress") actions.push("block", "submit");
  if (operator && job.status === "blocked") actions.push("resume");
  if (manager && job.status === "awaiting_review") actions.push("approve");
  if (manager && !["completed", "cancelled"].includes(job.status))
    actions.push("cancel");
  if (manager && ["completed", "cancelled"].includes(job.status))
    actions.push("reopen");
  return actions;
}
export function isOverdue(job: WorkOrder, now = Date.now()): boolean {
  return (
    !!job.due_at &&
    !["completed", "cancelled"].includes(job.status) &&
    new Date(job.due_at).getTime() < now
  );
}
export function dateLabel(
  value: string | null | undefined,
  withTime = false,
): string {
  if (!value) return "Not set";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Date unavailable";
  return new Intl.DateTimeFormat(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
    ...(withTime ? ({ hour: "numeric", minute: "2-digit" } as const) : {}),
  }).format(date);
}
export function deviceTimezone(): string {
  return Intl.DateTimeFormat().resolvedOptions().timeZone || "device local time";
}
export function jobDateLabel(value: string | null | undefined, withTime = false): string {
  return value ? `${dateLabel(value, withTime)} / ${deviceTimezone()}` : "Not set";
}
export function plainStatus(value: string): string {
  return value
    .replaceAll("_", " ")
    .replace(/^\w/, (char) => char.toUpperCase());
}
