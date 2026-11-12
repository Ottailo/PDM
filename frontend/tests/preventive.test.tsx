import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { Preventive, PlanDetail } from "../src/Preventive";
import { ToastProvider } from "../src/ui";
import type { Identity, MaintenancePlan, MaintenanceReminder } from "../src/types";

const identity: Identity = { user: { id: 1, name: "Test planner", email: "planner@example.test" }, company: { id: 3, name: "Test plant", timezone: "America/New_York" }, membership: { id: 8, role: "planner" }, mfa_enrollment_required: false, capabilities: { manage_preventive_maintenance: true } };
const plan: MaintenancePlan = { id: 20, asset_id: 42, asset_name: "Test press", title: "Monthly safety inspection", description: "Isolate before inspection", priority: "high", assignee_id: 9, assignee_name: "Test technician", checklist: [{ text: "Inspect interlock" }], timezone: "America/New_York", start_local: "2030-01-31T02:30", interval_unit: "month", interval_count: 1, reminder_hours: 24, escalation_member_id: 8, enabled: true, revision: 2, generation: 1, next_due_at: "2030-02-28T07:30:00Z", next_due_local: "2030-02-28T02:30", blocked_reason: null, created_at: "2030-01-01T00:00:00Z" };
const reminder: MaintenanceReminder = { id: 5, occurrence_id: 4, work_order_id: 31, stage: "due", recipient_name: "Test technician", state: "accepted", scheduled_at: "2030-02-27T07:30:00Z", accepted_at: "2030-02-27T07:31:00Z", acknowledged_at: null, attempts: 1, error: null, created_at: "2030-02-27T00:00:00Z" };
const envelope = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
let transport: ReturnType<typeof vi.fn>;
beforeEach(() => {
  transport = vi.fn(async (url: string, init?: RequestInit) => {
    if (url.endsWith("/csrf")) return envelope({ csrf_token: "test" });
    if (url.endsWith("/maintenance-plans/preview")) return envelope({ dates: [{ scheduled_local: "2030-01-31T02:30", scheduled_at: "2030-01-31T07:30:00Z", timezone: "America/New_York" }, { scheduled_local: "2030-02-28T02:30", scheduled_at: "2030-02-28T07:30:00Z", timezone: "America/New_York" }], policy: { month_end: "Clamp to last day then return to anchor", dst_gap: "Advance by gap", dst_fold: "Earlier instant", catch_up: "One latest due job" } });
    if (url.endsWith("/maintenance-plans") && init?.method === "POST") return envelope({ plan }, 201);
    if (init?.method) return envelope({ plan, reminder });
    return envelope({});
  });
  vi.stubGlobal("fetch", transport);
});
function mount(route = "/app/maintenance/plans", current = identity) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: Infinity } } });
  client.setQueryData(["v1", "identity"], current);
  client.setQueryData(["v1", 3, "maintenance-plans", ""], { plans: [plan] });
  client.setQueryData(["v1", 3, "assets", "plan-form"], { assets: [{ id: 42, name: "Test press", code: "TEST-42", status: "active" }] });
  client.setQueryData(["v1", 3, "members"], { members: [{ id: 8, user_id: 1, name: "Test planner", role: "planner" }, { id: 9, user_id: 2, name: "Test technician", role: "technician" }] });
  client.setQueryData(["v1", 3, "maintenance-plan", "20"], { plan, occurrences: [{ id: 4, plan_id: 20, generation: 1, scheduled_at: "2030-02-28T07:30:00Z", scheduled_local: "2030-02-28T02:30", work_order_id: 31, missed_count: 2, missed_from: "2030-01-01T07:30:00Z", missed_through: "2030-02-01T07:30:00Z", created_at: "2030-02-28T00:00:00Z" }], events: [{ id: 2, action: "schedule_create", actor_name: "Schedule", notes: "Two missed slots summarized", created_at: "2030-02-28T00:00:00Z" }], reminders: [reminder, { ...reminder, id: 6, state: "failed", accepted_at: null, error: "Mail refused" }] });
  const view = render(<QueryClientProvider client={client}><MemoryRouter initialEntries={[route]}><ToastProvider><Routes><Route path="/app/maintenance/plans" element={<Preventive />} /><Route path="/app/maintenance/plans/:id" element={<PlanDetail />} /></Routes></ToastProvider></MemoryRouter></QueryClientProvider>);
  return { ...view, client };
}
describe("plant-local preventive workflow", () => {
  it("shows server schedule fields and a linked immutable occurrence without treating mail as completion", () => {
    mount("/app/maintenance/plans/20");
    expect(screen.getByRole("link", { name: /Open job.*31/i })).toHaveAttribute("href", "/app/maintenance/31");
    expect(screen.getByText(/2 missed/i)).toBeVisible();
    expect(screen.getAllByText(/America\/New_York/).length).toBeGreaterThan(0);
    expect(screen.getByText(/SMTP accepted/i)).toBeVisible();
    expect(screen.getByText(/acceptance.*receipt|accepted.*receipt/i)).toBeVisible();
    expect(screen.getAllByRole("button", { name: /Retry reminder/ })).toHaveLength(1);
  });
  it("sends raw plant-local input and renders the server's local and UTC preview", async () => {
    mount();
    await userEvent.click(screen.getByRole("button", { name: "Create preventive plan" }));
    expect(screen.getByLabelText(/Time zone/)).toHaveValue("America/New_York");
    await userEvent.selectOptions(screen.getByLabelText(/^Machine/), "42");
    await userEvent.type(screen.getByLabelText(/Plan title/), "Monthly test");
    await userEvent.type(screen.getByLabelText(/First due date and time/), "2030-01-31T02:30");
    await userEvent.selectOptions(screen.getByLabelText(/Interval unit/), "month");
    await userEvent.click(screen.getByRole("button", { name: "Preview dates" }));
    await screen.findByText(/2030-02-28T07:30:00Z/);
    const previewCall = transport.mock.calls.find(([url]) => url.endsWith("/maintenance-plans/preview"))!;
    expect(JSON.parse(previewCall[1]!.body as string)).toEqual({ start_local: "2030-01-31T02:30", timezone: "America/New_York", interval_unit: "month", interval_count: 1 });
    await userEvent.click(screen.getByRole("button", { name: "Create plan" }));
    await waitFor(() => expect(transport.mock.calls.some(([url, init]) => url.endsWith("/maintenance-plans") && init?.method === "POST")).toBe(true));
    const call = transport.mock.calls.find(([url, init]) => url.endsWith("/maintenance-plans") && init?.method === "POST")!;
    expect(JSON.parse(call[1]!.body as string)).toMatchObject({ start_local: "2030-01-31T02:30", timezone: "America/New_York", asset_id: 42, interval_unit: "month", interval_count: 1 });
  });
  it("does not label an old occurrence with the edited generation's current timezone", async () => {
    const { client } = mount("/app/maintenance/plans/20");
    const cached = client.getQueryData<Record<string, unknown>>(["v1", 3, "maintenance-plan", "20"])!;
    client.setQueryData(["v1", 3, "maintenance-plan", "20"], { ...cached, plan: { ...plan, timezone: "Africa/Lagos", generation: 2 } });
    expect(await screen.findByText(/historical zone not provided/)).toBeVisible();
    expect(screen.getByText(/2030-02-28 02:30.*historical zone/)).not.toHaveTextContent("Africa/Lagos");
  });
  it("invalidates preview when calendar fields change", async () => {
    mount("/app/maintenance/plans/20");
    await userEvent.click(screen.getByRole("button", { name: "Edit plan" }));
    await userEvent.click(screen.getByRole("button", { name: "Preview dates" }));
    await within(screen.getByRole("dialog")).findByText(/2030-02-28T07:30:00Z/);
    await userEvent.clear(screen.getByLabelText(/Every/));
    await userEvent.type(screen.getByLabelText(/Every/), "2");
    expect(within(screen.getByRole("dialog")).queryByText(/2030-02-28T07:30:00Z/)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save plan" })).toBeDisabled();
  });
  it("keeps planner mutation controls absent for read-only membership", () => {
    mount("/app/maintenance/plans/20", { ...identity, membership: { id: 10, role: "viewer" }, capabilities: {} });
    expect(screen.queryByRole("button", { name: /Edit plan|Pause plan|Retry reminder/ })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Open job.*31/i })).toBeVisible();
  });
  it("edits only contract fields and retains the server revision, not an editable machine", async () => {
    mount("/app/maintenance/plans/20");
    await userEvent.click(screen.getByRole("button", { name: "Edit plan" }));
    expect(within(screen.getByRole("dialog")).queryByRole("combobox", { name: /^Machine/ })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Preview dates" }));
    await within(screen.getByRole("dialog")).findByText(/2030-02-28T07:30:00Z/);
    await userEvent.click(screen.getByRole("button", { name: "Save plan" }));
    await waitFor(() => expect(transport.mock.calls.some(([url, init]) => url.endsWith("/maintenance-plans/20") && init?.method === "PATCH")).toBe(true));
    const payload = JSON.parse(transport.mock.calls.find(([url, init]) => url.endsWith("/maintenance-plans/20") && init?.method === "PATCH")![1]!.body as string);
    expect(payload).toMatchObject({ revision: 2, start_local: "2030-01-31T02:30", timezone: "America/New_York", checklist: [{ text: "Inspect interlock" }], assignee_id: 9, escalation_member_id: 8 });
    expect(payload).not.toHaveProperty("asset_id");
    expect(payload).not.toHaveProperty("company_id");
  });
  it("uses revision and reason when resuming a paused plan", async () => {
    const { client } = mount("/app/maintenance/plans/20");
    const cached = client.getQueryData<Record<string, unknown>>(["v1", 3, "maintenance-plan", "20"])!;
    client.setQueryData(["v1", 3, "maintenance-plan", "20"], { ...cached, plan: { ...plan, enabled: false } });
    await userEvent.click(await screen.findByRole("button", { name: "Resume plan" }));
    await userEvent.type(screen.getByLabelText(/^Reason/), "Production restarting");
    await userEvent.click(screen.getByRole("button", { name: "Confirm resume" }));
    await waitFor(() => expect(transport.mock.calls.some(([url]) => url.endsWith("/20/resume"))).toBe(true));
    expect(JSON.parse(transport.mock.calls.find(([url]) => url.endsWith("/20/resume"))![1]!.body as string)).toEqual({ revision: 2, reason: "Production restarting" });
  });
  it("acknowledges with an empty payload, without a work-order transition", async () => {
    mount("/app/maintenance/plans/20");
    await userEvent.click(screen.getByRole("button", { name: "Acknowledge reminder 5" }));
    await userEvent.click(screen.getByRole("button", { name: "Confirm acknowledgment" }));
    await waitFor(() => expect(transport.mock.calls.some(([url]) => url.endsWith("/maintenance-reminders/5/ack"))).toBe(true));
    expect(JSON.parse(transport.mock.calls.find(([url]) => url.endsWith("/5/ack"))![1]!.body as string)).toEqual({});
    expect(transport.mock.calls.some(([url]) => url.includes("/transition"))).toBe(false);
  });
  it("requires a reason before requesting retry of a terminal failed reminder", async () => {
    mount("/app/maintenance/plans/20");
    await userEvent.click(screen.getByRole("button", { name: "Retry reminder 6" }));
    await userEvent.type(screen.getByLabelText(/Reason for retry/), "Local mailbox restored");
    await userEvent.click(screen.getByRole("button", { name: "Request retry" }));
    await waitFor(() => expect(transport.mock.calls.some(([url]) => url.endsWith("/6/retry"))).toBe(true));
    expect(JSON.parse(transport.mock.calls.find(([url]) => url.endsWith("/6/retry"))![1]!.body as string)).toEqual({ reason: "Local mailbox restored" });
  });
  it("preserves a revision conflict and offers refresh rather than overwriting", async () => {
    mount("/app/maintenance/plans/20");
    await userEvent.click(screen.getByRole("button", { name: "Pause plan" }));
    await userEvent.type(screen.getByLabelText(/^Reason/), "Plant shutdown");
    transport.mockImplementation(async (url: string) => url.endsWith("/csrf") ? envelope({ csrf_token: "test" }) : envelope({ error: { code: "revision_conflict", message: "Plan changed" } }, 409));
    await userEvent.click(screen.getByRole("button", { name: "Confirm pause" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Your changes were not saved");
    expect(screen.getByRole("button", { name: "Close and refresh record" })).toBeEnabled();
    expect(screen.getByLabelText(/^Reason/)).toHaveValue("Plant shutdown");
  });
  it("confirms pause with revision and a human reason, retaining existing work", async () => {
    mount("/app/maintenance/plans/20");
    await userEvent.click(screen.getByRole("button", { name: "Pause plan" }));
    expect(screen.getByText(/existing.*work.*retained|existing.*jobs.*remain/i)).toBeVisible();
    await userEvent.type(screen.getByLabelText(/^Reason/), "Plant shutdown");
    await userEvent.click(screen.getByRole("button", { name: "Confirm pause" }));
    await waitFor(() => expect(transport.mock.calls.some(([url]) => url.endsWith("/20/pause"))).toBe(true));
    expect(JSON.parse(transport.mock.calls.find(([url]) => url.endsWith("/20/pause"))![1]!.body as string)).toEqual({ revision: 2, reason: "Plant shutdown" });
  });
});
