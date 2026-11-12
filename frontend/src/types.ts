export type Role =
  "owner" | "admin" | "planner" | "technician" | "stores" | "viewer";
export interface User {
  id: number;
  name: string;
  email: string;
}
export interface Company {
  id: number;
  name: string;
  role?: Role;
  timezone?: string;
}
export interface Membership {
  id: number;
  role: Role;
  user_id?: number;
}
export interface Identity {
  user: User;
  company: Company;
  membership: Membership;
  mfa_enrollment_required: boolean;
  capabilities: Record<string, boolean> | string[];
}
export interface Location {
  id: number;
  name: string;
  type: string;
  parent_id: number | null;
}
export interface Asset {
  id: number;
  code: string;
  name: string;
  manufacturer: string;
  model: string;
  serial_number: string;
  criticality: string;
  location_id: number | null;
  location_name: string | null;
  status: string;
  description: string;
  revision: number;
  telemetry_status: "not_connected";
}
export interface Invitation {
  id: number;
  email: string;
  role: Role;
  expires_at: string;
}
export interface Member {
  id: number;
  user_id: number;
  name: string;
  email: string;
  role: Role;
}
export type JobStatus =
  | "open"
  | "assigned"
  | "in_progress"
  | "blocked"
  | "awaiting_review"
  | "completed"
  | "cancelled";
export type JobAction =
  "start" | "block" | "resume" | "submit" | "approve" | "cancel" | "reopen";
export interface ChecklistItem {
  id?: number;
  text: string;
  completed: boolean;
  required?: boolean;
}
export interface WorkOrder {
  id: number;
  number: string;
  title: string;
  description: string;
  asset_id: number;
  asset_name: string;
  priority: string;
  status: JobStatus;
  assignee_id: number | null;
  assignee_name: string | null;
  due_at: string | null;
  revision: number;
  created_at: string;
  completed_at: string | null;
  notes: string;
  completion_notes: string;
  labor_minutes: number;
  checklist: ChecklistItem[];
  plan_id?: number | null;
  occurrence_id?: number | null;
}
export interface JobEvent {
  id: number;
  actor_kind?: "user" | "system";
  actor_name: string;
  action: string;
  from_status: string | null;
  to_status: string;
  notes: string;
  created_at: string;
}
export interface Manual {
  id: number;
  title: string;
  filename: string;
  asset_id: number;
  asset_name: string;
  status: string;
  page_count: number | null;
  error?: string | null;
  created_at: string;
  checksum: string;
  revision: number;
}
export interface Summary {
  asset_count: number;
  open_work_order_count: number;
  awaiting_review_count: number;
  completed_work_order_count: number;
  overdue_work_order_count: number;
  document_count: number;
}
export interface Message {
  message: string;
}
export type IntervalUnit = "day" | "week" | "month";
export interface MaintenancePlan {
  id: number;
  asset_id: number;
  asset_name: string;
  title: string;
  description: string;
  priority: string;
  assignee_id: number | null;
  assignee_name: string | null;
  checklist: { text: string }[];
  timezone: string;
  start_local: string;
  interval_unit: IntervalUnit;
  interval_count: number;
  reminder_hours: number;
  escalation_member_id: number | null;
  enabled: boolean;
  revision: number;
  generation: number;
  next_due_at: string | null;
  next_due_local: string | null;
  blocked_reason: string | null;
  created_at: string;
}
export interface PlanOccurrence {
  id: number;
  plan_id: number;
  generation: number;
  scheduled_at: string;
  scheduled_local: string;
  work_order_id: number | null;
  missed_count: number;
  missed_from: string | null;
  missed_through: string | null;
  created_at: string;
}
export interface PlanEvent {
  id: number;
  action: string;
  actor_name: string;
  notes: string;
  created_at: string;
}
export interface MaintenanceReminder {
  id: number;
  occurrence_id: number;
  work_order_id: number;
  stage: "due" | "overdue";
  recipient_name: string | null;
  state: "queued" | "running" | "retrying" | "accepted" | "failed" | "cancelled";
  scheduled_at: string;
  accepted_at: string | null;
  acknowledged_at: string | null;
  attempts: number;
  error: string | null;
  created_at: string;
}
export interface PlanRecord {
  plan: MaintenancePlan;
  occurrences: PlanOccurrence[];
  events: PlanEvent[];
  reminders: MaintenanceReminder[];
}
export interface PlanPreview {
  dates: { scheduled_local: string; scheduled_at: string; timezone: string }[];
  policy: { month_end: string; dst_gap: string; dst_fold: string; catch_up: string };
}
