import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BrowserRouter, MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, it, vi } from "vitest";
import { ApiError } from "../src/api";
import { Dialog, Empty, ErrorNotice, Form, Field, value } from "../src/ui";
import { WorkQueue, Today } from "../src/Today";
import { Machines } from "../src/Machines";
import type { Identity } from "../src/types";
const identity: Identity = {
  user: { id: 1, name: "Test-only Owner", email: "test@example.org" },
  company: { id: 2, name: "Test-only Plant" },
  membership: { id: 4, role: "owner" },
  mfa_enrollment_required: false,
  capabilities: { manage_registry: true, request_work_orders: true },
};
function providers(
  element: React.ReactNode,
  client = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: Infinity } },
  }),
) {
  client.setQueryData(["v1", "identity"], identity);
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>{element}</MemoryRouter>
    </QueryClientProvider>,
  );
}
describe("honest empty and error states", () => {
  it("renders an explicit empty state without example equipment", () => {
    render(
      <Empty title="No machines recorded">Record your first machine.</Empty>,
    );
    expect(screen.getByText("No machines recorded")).toBeVisible();
    expect(
      screen.queryByText(/healthy|online|nominal/i),
    ).not.toBeInTheDocument();
  });
  it("does not render work rows when the real queue is empty", () => {
    render(
      <BrowserRouter>
        <WorkQueue jobs={[]} />
      </BrowserRouter>,
    );
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });
  it("renders actual zero counts and no forecast on an empty organization", () => {
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false, staleTime: Infinity } },
    });
    client.setQueryData(["v1", 2, "summary"], {
      asset_count: 0,
      open_work_order_count: 0,
      awaiting_review_count: 0,
      completed_work_order_count: 0,
      overdue_work_order_count: 0,
      document_count: 0,
    });
    client.setQueryData(["v1", 2, "work-orders", "today"], { work_orders: [] });
    providers(<Today />, client);
    expect(screen.getByText("No open jobs")).toBeVisible();
    expect(screen.getAllByText("0")).toHaveLength(4);
    expect(
      screen.queryByText(/forecast|downtime saved|online/i),
    ).not.toBeInTheDocument();
  });
  it("shows registry empty state without phantom machines", () => {
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false, staleTime: Infinity } },
    });
    client.setQueryData(["v1", 2, "assets", "", "", false], { assets: [] });
    client.setQueryData(["v1", 2, "locations"], { locations: [] });
    providers(<Machines />, client);
    expect(screen.getByText("Your machines start here")).toBeVisible();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Record your first machine" }),
    ).toBeEnabled();
  });
  it("renders HTML in error messages as text and supports retry", async () => {
    const retry = vi.fn();
    render(
      <ErrorNotice
        error={
          new ApiError(400, {
            error: {
              code: "bad",
              message: "<img src=x onerror=alert(1)>",
              fields: { name: "Required" },
            },
          })
        }
        retry={retry}
      />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent(
      "<img src=x onerror=alert(1)>",
    );
    expect(document.querySelector("img")).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(retry).toHaveBeenCalledOnce();
  });
  it("explains revision conflicts instead of silently overwriting", () => {
    render(
      <ErrorNotice
        error={
          new ApiError(409, {
            error: { code: "revision_conflict", message: "Record changed" },
          })
        }
      />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Your changes were not saved",
    );
  });
});
describe("keyboard and forms", () => {
  it("links field labels to real inputs and submits user values", async () => {
    const submit = vi.fn();
    render(
      <Form onSubmit={(data) => submit(value(data, "name"))}>
        <Field name="name" label="Machine name" required />
        <button type="submit">Record machine</button>
      </Form>,
    );
    await userEvent.type(
      screen.getByLabelText("Machine name *"),
      "Test-only pump",
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Record machine" }),
    );
    expect(submit).toHaveBeenCalledExactlyOnceWith("Test-only pump");
  });
  it("gives dialogs semantic labels and a working close button", async () => {
    const close = vi.fn();
    render(
      <Dialog title="Record machine" onClose={close}>
        <Field label="Machine code" />
      </Dialog>,
    );
    expect(
      screen.getByRole("dialog", { name: "Record machine" }),
    ).toHaveAttribute("open");
    await userEvent.click(screen.getByRole("button", { name: "Close dialog" }));
    expect(close).toHaveBeenCalledOnce();
  });
  it("disables dismissal during file transfer instead of leaving an empty handler", () => {
    render(
      <Dialog title="Upload" onClose={vi.fn()} dismissible={false}>
        Sending file
      </Dialog>,
    );
    expect(screen.getByRole("button", { name: "Close dialog" })).toBeDisabled();
  });
});
