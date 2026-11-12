import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { Maintenance } from "../src/Maintenance";
import { Manuals } from "../src/Manuals";
import userEvent from "@testing-library/user-event";

function mount(element: React.ReactNode, route: string) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: Infinity } } });
  client.setQueryData(["v1", "identity"], { user: { id: 1, name: "Test", email: "test@example.test" }, company: { id: 1, name: "Test" }, membership: { id: 1, role: "owner" }, capabilities: { request_work_orders: true, manage_work_orders: true, upload_documents: true } });
  vi.stubGlobal("fetch", vi.fn(async (input: string) => {
    await new Promise((resolve) => setTimeout(resolve, 20));
    const body = input.includes("/assets") ? { assets: [{ id: 42, code: "TEST42", name: "Test equipment", status: "active" }] } : input.includes("/members") ? { members: [] } : input.includes("/documents") ? { documents: [] } : { work_orders: [] };
    return new Response(JSON.stringify(body), { headers: { "Content-Type": "application/json" } });
  }));
  return render(<QueryClientProvider client={client}><MemoryRouter initialEntries={[route]}>{element}</MemoryRouter></QueryClientProvider>);
}

describe("machine context survives asynchronous option loading", () => {
  it("prefills a job from its machine detail link", async () => {
    mount(<Maintenance />, "/app/maintenance?new=1&asset_id=42");
    const select = document.querySelector('dialog select[name="asset_id"]')!;
    await waitFor(() => expect(select).toBeEnabled());
    expect(select).toHaveValue("42");
  });
  it("prefills a manual upload from its machine filter", async () => {
    mount(<Manuals />, "/app/manuals?asset_id=42");
    await userEvent.click(screen.getByRole("button", { name: "Upload PDF" }));
    const select = document.querySelector('dialog select[name="asset_id"]')!;
    await waitFor(() => expect(select).toBeEnabled());
    expect(select).toHaveValue("42");
  });
});
