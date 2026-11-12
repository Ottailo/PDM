import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, get, mutate, queryString, uploadManual } from "../src/api";
const response = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
describe("same-origin API contract", () => {
  let fetchMock: ReturnType<typeof vi.fn>;
  beforeEach(() => {
    fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
  });
  it("sends credentials and never invents records for an empty envelope", async () => {
    fetchMock.mockResolvedValue(response({ assets: [] }));
    expect(await get("/assets")).toEqual({ assets: [] });
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/assets",
      expect.objectContaining({ credentials: "include", cache: "no-store" }),
    );
  });
  it("fetches a fresh CSRF token for every mutation including login", async () => {
    fetchMock
      .mockResolvedValueOnce(response({ csrf_token: "anonymous" }))
      .mockResolvedValueOnce(response({ message: "signed in" }))
      .mockResolvedValueOnce(response({ csrf_token: "rotated" }))
      .mockResolvedValueOnce(response({ asset: { id: 2 } }));
    await mutate("/auth/login", {
      email: "test@example.org",
      password: "test-only-password",
    });
    await mutate("/assets", { name: "Test-only machine" });
    expect(fetchMock.mock.calls[1][1].headers["X-CSRF-Token"]).toBe(
      "anonymous",
    );
    expect(fetchMock.mock.calls[3][1].headers["X-CSRF-Token"]).toBe("rotated");
  });
  it("preserves the same idempotency key after an interrupted maintenance mutation", async () => {
    fetchMock
      .mockResolvedValueOnce(response({ csrf_token: "token" }))
      .mockRejectedValueOnce(new TypeError("Network failure"));
    await expect(
      mutate("/work-orders/112/transition", { revision: 1, action: "start" }),
    ).rejects.toThrow("Network failure");
    const key = fetchMock.mock.calls[1][1].headers["Idempotency-Key"];
    expect(key).toMatch(/^[a-z0-9-]{36}$/);
    fetchMock
      .mockResolvedValueOnce(response({ csrf_token: "token" }))
      .mockResolvedValueOnce(response({ work_order: { id: 112 } }));
    await mutate("/work-orders/112/transition", {
      revision: 1,
      action: "start",
    });
    expect(fetchMock.mock.calls[3][1].headers["Idempotency-Key"]).toBe(key);
  });
  it("uses a different idempotency key when the maintenance payload changes", async () => {
    fetchMock
      .mockResolvedValueOnce(response({ csrf_token: "token" }))
      .mockResolvedValueOnce(
        response(
          { error: { code: "revision_conflict", message: "Record changed" } },
          409,
        ),
      );
    await expect(
      mutate("/work-orders/113/transition", { revision: 1, action: "start" }),
    ).rejects.toMatchObject({ status: 409 });
    const first = fetchMock.mock.calls[1][1].headers["Idempotency-Key"];
    fetchMock
      .mockResolvedValueOnce(response({ csrf_token: "token" }))
      .mockResolvedValueOnce(response({ work_order: {} }));
    await mutate("/work-orders/113/transition", {
      revision: 2,
      action: "start",
    });
    expect(fetchMock.mock.calls[3][1].headers["Idempotency-Key"]).not.toBe(
      first,
    );
  });
  it("retains structured errors without HTML rendering", async () => {
    fetchMock.mockResolvedValue(
      response(
        {
          error: {
            code: "invalid_fields",
            message: "<script>unsafe</script>",
            fields: { name: "Required" },
          },
          request_id: "ref-42",
        },
        400,
      ),
    );
    await expect(get("/assets")).rejects.toMatchObject({
      message: "<script>unsafe</script>",
      code: "invalid_fields",
      fields: { name: "Required" },
      requestId: "ref-42",
    });
  });
  it("reports invalid successful JSON instead of manufacturing a fallback", async () => {
    fetchMock.mockResolvedValue(new Response("not JSON", { status: 200 }));
    await expect(get("/summary")).rejects.toThrow("unreadable response");
  });
  it("rejects a missing CSRF token before making a write", async () => {
    fetchMock.mockResolvedValue(response({}));
    await expect(mutate("/assets", {})).rejects.toThrow(
      "Security check unavailable",
    );
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
  it("encodes filters and preserves explicit false and zero values", () => {
    expect(
      queryString({
        q: "pump & line",
        include_archived: false,
        page: 0,
        unused: "",
        empty: null,
      }),
    ).toBe("?q=pump+%26+line&include_archived=false&page=0");
  });
  it("only reports actual upload events and uses private multipart submission", async () => {
    fetchMock.mockResolvedValue(response({ csrf_token: "upload-token" }));
    let xhr: FakeXHR;
    class FakeXHR {
      upload = {
        onprogress: null as
          | null
          | ((event: {
              lengthComputable: boolean;
              loaded: number;
              total: number;
            }) => void),
      };
      onload: (() => void) | null = null;
      status = 202;
      responseText = JSON.stringify({
        document: { id: 8, status: "quarantined" },
      });
      withCredentials = false;
      timeout = 0;
      headers: Record<string, string> = {};
      form?: FormData;
      constructor() {
        // Capture the actual test transport so its headers can be asserted.
        // eslint-disable-next-line @typescript-eslint/no-this-alias
        xhr = this;
      }
      open = vi.fn();
      setRequestHeader(key: string, val: string) {
        this.headers[key] = val;
      }
      send(form: FormData) {
        this.form = form;
        this.upload.onprogress?.({
          lengthComputable: true,
          loaded: 5,
          total: 10,
        });
        this.onload?.();
      }
    }
    vi.stubGlobal("XMLHttpRequest", FakeXHR);
    const progress = vi.fn();
    const result = await uploadManual(
      new File(["%PDF-test-only"], "test-only.pdf", {
        type: "application/pdf",
      }),
      4,
      "",
      progress,
    );
    expect(result.document.status).toBe("quarantined");
    expect(progress).toHaveBeenCalledExactlyOnceWith(50);
    expect(xhr!.withCredentials).toBe(true);
    expect(xhr!.headers["X-CSRF-Token"]).toBe("upload-token");
    expect(xhr!.form?.get("asset_id")).toBe("4");
    expect(xhr!.form?.has("title")).toBe(false);
  });
  it("constructs useful error defaults", () => {
    expect(new ApiError(503, {}).message).toContain("503");
  });
});
