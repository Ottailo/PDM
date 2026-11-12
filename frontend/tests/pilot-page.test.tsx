import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { PilotPage } from "../src/PilotPage";

function renderPage(path = "/") {
  return render(<MemoryRouter initialEntries={[path]}><PilotPage /></MemoryRouter>);
}
describe("public pilot publishing boundary", () => {
  it("explains the pilot without mounting private queries or account controls", () => {
    const fetch = vi.fn();
    vi.stubGlobal("fetch", fetch);
    renderPage();
    expect(screen.getByRole("heading", { level: 1 })).toBeVisible();
    expect(screen.getByText(/Accounts, organization/)).toHaveTextContent("uploads are unavailable here");
    expect(document.querySelector("form, input, textarea, select")).toBeNull();
    expect(fetch).not.toHaveBeenCalled();
    expect(screen.getByRole("link", { name: "Machivital home" })).toHaveAttribute("href", "/");
  });
  it("provides working native disclosures and valid navigation anchors", async () => {
    const { container } = renderPage();
    const details = container.querySelectorAll("details");
    expect(details.length).toBeGreaterThanOrEqual(3);
    await userEvent.click(details[1].querySelector("summary")!);
    expect(details[1]).toHaveAttribute("open");
    await userEvent.click(details[1].querySelector("summary")!);
    expect(details[1]).not.toHaveAttribute("open");
    for (const anchor of container.querySelectorAll<HTMLAnchorElement>('a[href^="#"]')) {
      expect(document.getElementById(anchor.hash.slice(1))).not.toBeNull();
    }
  });
  it("cannot expose an account form through a private URL", () => {
    renderPage("/signup");
    expect(document.querySelector("form, input")).toBeNull();
    expect(screen.queryByRole("button", { name: /create account/i })).toBeNull();
  });
});
