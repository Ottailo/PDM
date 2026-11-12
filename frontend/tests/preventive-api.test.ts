import { beforeEach, describe, expect, it, vi } from "vitest";
import { clearReplayContext, mutate, setReplayContext } from "../src/api";

const response = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
let transport: ReturnType<typeof vi.fn>;
beforeEach(() => {
  transport = vi.fn();
  vi.stubGlobal("fetch", transport);
  clearReplayContext();
  setReplayContext(1, 10);
});
function success() {
  transport.mockResolvedValueOnce(response({ csrf_token: "fresh" })).mockResolvedValueOnce(response({}));
}
function interruption() {
  transport.mockResolvedValueOnce(response({ csrf_token: "fresh" })).mockRejectedValueOnce(new TypeError("Interrupted"));
}
function lastKey() {
  return transport.mock.calls.at(-1)![1].headers["Idempotency-Key"];
}
describe("preventive mutation replay boundaries", () => {
  it.each([
    ["/maintenance-plans", "POST"],
    ["/maintenance-plans/12", "PATCH"],
    ["/maintenance-plans/12/pause", "POST"],
    ["/maintenance-plans/12/resume", "POST"],
    ["/maintenance-reminders/7/ack", "POST"],
    ["/maintenance-reminders/7/retry", "POST"],
  ])("retains an interrupted %s %s key and releases it on success", async (path, method) => {
    interruption();
    await expect(mutate(path, { reason: "Test only", revision: 1 }, method)).rejects.toThrow("Interrupted");
    const key = lastKey();
    expect(key).toMatch(/^[a-z0-9-]{36}$/);
    success();
    await mutate(path, { reason: "Test only", revision: 1 }, method);
    expect(lastKey()).toBe(key);
    success();
    await mutate(path, { reason: "Test only", revision: 1 }, method);
    expect(lastKey()).not.toBe(key);
  });
  it.each([
    ["/maintenance-plans/preview", "POST"],
    ["/maintenance-plans/12/unknown", "POST"],
    ["/maintenance-plans-extra", "POST"],
    ["/maintenance-reminders/7", "PATCH"],
    ["/auth/login", "POST"],
  ])("does not broaden replay into %s %s", async (path, method) => {
    success();
    await mutate(path, {}, method);
    expect(lastKey()).toBeUndefined();
    expect(transport.mock.calls.at(-1)![1].headers["X-CSRF-Token"]).toBe("fresh");
  });
  it("does not carry a failed work-order key across a company or user switch or logout", async () => {
    const path = "/work-orders/1/transition";
    interruption();
    await expect(mutate(path, { revision: 1, action: "start" })).rejects.toThrow();
    const original = lastKey();
    setReplayContext(1, 20);
    success();
    await mutate(path, { revision: 1, action: "start" });
    expect(lastKey()).not.toBe(original);
    setReplayContext(2, 10);
    success();
    await mutate(path, { revision: 1, action: "start" });
    expect(lastKey()).not.toBe(original);
    clearReplayContext();
    setReplayContext(1, 10);
    success();
    await mutate(path, { revision: 1, action: "start" });
    expect(lastKey()).not.toBe(original);
  });
  it("retains failed keys when the same authoritative identity is refreshed", async () => {
    interruption();
    await expect(mutate("/maintenance-plans/2/pause", { revision: 1, reason: "Service shutdown" })).rejects.toThrow();
    const key = lastKey();
    setReplayContext(1, 10);
    success();
    await mutate("/maintenance-plans/2/pause", { revision: 1, reason: "Service shutdown" });
    expect(lastKey()).toBe(key);
  });
  it("rejects a stale success after a tenant switch instead of opening the old tenant's record", async () => {
    transport.mockResolvedValueOnce(response({ csrf_token: "test" })).mockImplementationOnce(async () => {
      setReplayContext(1, 20);
      return response({ plan: { id: 2 } });
    });
    await expect(mutate("/maintenance-plans", { title: "Test" })).rejects.toThrow(/organization|session/i);
  });
  it("rejects a switch away and back during CSRF, even if the company IDs now match", async () => {
    transport.mockImplementationOnce(async () => {
      setReplayContext(1, 20);
      setReplayContext(1, 10);
      return response({ csrf_token: "test" });
    });
    await expect(mutate("/maintenance-plans", {})).rejects.toThrow(/organization|session/i);
    expect(transport).toHaveBeenCalledTimes(1);
  });
  it("does not send a retained tenant mutation when identity changes during CSRF", async () => {
    transport.mockImplementationOnce(async () => {
      setReplayContext(1, 20);
      return response({ csrf_token: "new-tenant" });
    });
    await expect(mutate("/maintenance-plans/2/pause", { revision: 1, reason: "Test" })).rejects.toThrow(/organization|session/i);
    expect(transport).toHaveBeenCalledTimes(1);
  });
});
