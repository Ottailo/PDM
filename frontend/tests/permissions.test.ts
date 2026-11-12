import { describe, expect, it } from "vitest";
import {
  availableActions,
  can,
  dateLabel,
  deviceTimezone,
  jobDateLabel,
  isOverdue,
  plainStatus,
} from "../src/permissions";
import type { Identity, WorkOrder } from "../src/types";
const identity: Identity = {
  user: { id: 99, name: "Test-only User", email: "test@example.org" },
  company: { id: 1, name: "Test-only Org" },
  membership: { id: 7, role: "technician" },
  mfa_enrollment_required: false,
  capabilities: { request_work_orders: true, manage_work_orders: false },
};
const job = { assignee_id: 7, status: "assigned" } as WorkOrder;
describe("authoritative capabilities and job lifecycle", () => {
  it("fails closed for unknown or false capabilities", () => {
    expect(can(identity, "manage_registry")).toBe(false);
    expect(can(identity, "manage_work_orders")).toBe(false);
    expect(can(identity, "request_work_orders")).toBe(true);
  });
  it("compares assignee membership ID, not user ID", () => {
    expect(availableActions(job, identity)).toEqual(["start"]);
    expect(availableActions({ ...job, assignee_id: 99 }, identity)).toEqual([]);
  });
  it("does not let a manager execute another person’s job", () => {
    expect(
      availableActions(job, {
        ...identity,
        membership: { id: 8, role: "owner" },
        capabilities: { request_work_orders: true, manage_work_orders: true },
      }),
    ).toEqual(["cancel"]);
  });
  it("gates submission and review by current status and role", () => {
    expect(
      availableActions({ ...job, status: "in_progress" }, identity),
    ).toEqual(["block", "submit"]);
    expect(
      availableActions({ ...job, status: "awaiting_review" }, identity),
    ).toEqual([]);
    expect(
      availableActions(
        { ...job, status: "awaiting_review" },
        { ...identity, capabilities: { manage_work_orders: true } },
      ),
    ).toEqual(["approve", "cancel"]);
  });
  it("never marks completed or cancelled work overdue", () => {
    const due = { ...job, due_at: "2020-01-01T00:00:00Z" };
    expect(isOverdue(due)).toBe(true);
    expect(isOverdue({ ...due, status: "completed" })).toBe(false);
    expect(isOverdue({ ...due, status: "cancelled" })).toBe(false);
  });
  it("truthfully labels one-off job dates with the device zone without pretending it is the company zone", () => {
    expect(jobDateLabel("2030-01-01T00:00:00Z", true)).toContain(deviceTimezone());
    expect(jobDateLabel(null)).toBe("Not set");
  });
  it("does not invent a date for missing or invalid values", () => {
    expect(dateLabel(null)).toBe("Not set");
    expect(dateLabel("not-a-date")).toBe("Date unavailable");
    expect(plainStatus("awaiting_review")).toBe("Awaiting review");
  });
});
