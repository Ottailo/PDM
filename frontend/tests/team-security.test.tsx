import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ToastProvider } from "../src/ui";
import { Team } from "../src/Team";
import type { Role } from "../src/types";

function mount(role: Role = "owner") {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: Infinity } } });
  client.setQueryData(["v1", "identity"], { user: { id: 1, name: "Test owner", email: "owner@example.test" }, company: { id: 1, name: "Test plant" }, membership: { id: 1, role }, mfa_enrollment_required: false, capabilities: { manage_team: role === "owner" || role === "admin" } });
  client.setQueryData(["v1", 1, "members"], { members: [{ id: 1, user_id: 1, name: "Test owner", email: "owner@example.test", role: "owner" }, { id: 2, user_id: 2, name: "Test technician", email: "tech@example.test", role: "technician" }, { id: 3, user_id: 3, name: "Test administrator", email: "admin@example.test", role: "admin" }] });
  client.setQueryData(["v1", 1, "invitations"], { invitations: [{ id: 10, email: "pending@example.test", role: "viewer", expires_at: "2030-01-01T00:00:00Z" }] });
  client.setQueryData(["v1", 1, "companies"], { companies: [{ id: 1, name: "Test plant", role }] });
  client.setQueryData(["v1", 1, "mfa-status"], { enabled: true, recovery_codes_remaining: 10 });
  return render(<QueryClientProvider client={client}><MemoryRouter><ToastProvider><Team /></ToastProvider></MemoryRouter></QueryClientProvider>);
}

describe("tenant access administration", () => {
  it("offers member offboarding and pending invitation cancellation to an owner", () => {
    mount();
    expect(screen.getByRole("button", { name: "Remove Test technician" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Cancel invitation for pending@example.test" })).toBeVisible();
  });
  it("requires explicit fresh identity confirmation before a destructive action", async () => {
    mount();
    await userEvent.click(screen.getByRole("button", { name: "Remove Test technician" }));
    expect(screen.getByLabelText(/Confirm your password/)).toBeVisible();
    expect(screen.getByLabelText(/Authenticator or recovery code/)).toBeVisible();
    expect(screen.queryByRole("button", { name: "Remove member" })).not.toBeInTheDocument();
  });
  it("does not let an administrator manage owners or administrators", () => {
    mount("admin");
    expect(screen.queryByRole("button", { name: "Change role for Test owner" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Remove Test administrator" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Remove Test technician" })).toBeVisible();
  });
  it("recovers a stale access confirmation through a real reauthentication form", async () => {
    mount();
    vi.stubGlobal("fetch", vi.fn(async (url: string) => new Response(JSON.stringify(url.endsWith("/csrf") ? { csrf_token: "test" } : url.endsWith("/auth/reauth") ? { message: "Confirmed" } : { error: { code: "reauthentication_required", message: "Confirm identity again" } }), { status: url.includes("/members/2") ? 403 : 200, headers: { "Content-Type": "application/json" } })));
    await userEvent.click(screen.getByRole("button", { name: "Remove Test technician" }));
    await userEvent.type(screen.getByLabelText(/Confirm your password/), "Test-only password");
    await userEvent.type(screen.getByLabelText(/Authenticator or recovery code/), "123456");
    await userEvent.click(screen.getByRole("button", { name: "Confirm identity" }));
    await userEvent.type(await screen.findByLabelText(/Reason for this access change/), "Test removal");
    await userEvent.click(screen.getByRole("button", { name: "Remove member" }));
    await userEvent.click(await screen.findByRole("button", { name: "Confirm identity again" }));
    expect(screen.getByLabelText(/Confirm your password/)).toHaveValue("");
    expect(screen.queryByRole("button", { name: "Remove member" })).not.toBeInTheDocument();
  });
  it("keeps one interactive representation and labeled cells for phone team and invitation cards", () => {
    mount();
    expect(screen.getAllByRole("button", { name: "Remove Test technician" })).toHaveLength(1);
    expect(screen.getAllByRole("button", { name: "Cancel invitation for pending@example.test" })).toHaveLength(1);
    expect(screen.getByText("tech@example.test").closest("td")).toHaveAttribute("data-label", "Work email");
    expect(document.querySelectorAll(".responsive-records")).toHaveLength(2);
  });
  it("keeps access administration absent for a read-only viewer", () => {
    mount("viewer");
    expect(screen.queryByRole("button", { name: /Remove Test|Change role for|Cancel invitation/ })).not.toBeInTheDocument();
  });
});
