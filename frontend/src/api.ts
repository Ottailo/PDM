const BASE = "/api/v1";
export class ApiError extends Error {
  status: number;
  code: string;
  fields: Record<string, string>;
  requestId?: string;
  constructor(
    status: number,
    body: {
      error?: {
        message?: string;
        code?: string;
        fields?: Record<string, string>;
      };
      request_id?: string;
    },
  ) {
    super(
      body.error?.message || `The request could not be completed (${status}).`,
    );
    this.name = "ApiError";
    this.status = status;
    this.code = body.error?.code || "request_failed";
    this.fields = body.error?.fields || {};
    this.requestId = body.request_id;
  }
}
async function decode<T>(response: Response): Promise<T> {
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new ApiError(response.status, body || {});
  if (body === null)
    throw new Error("The server returned an unreadable response. Try again.");
  return body as T;
}
export async function get<T>(path: string, signal?: AbortSignal): Promise<T> {
  return decode<T>(
    await fetch(`${BASE}${path}`, {
      credentials: "include",
      cache: "no-store",
      signal,
      headers: { Accept: "application/json" },
    }),
  );
}
export async function csrf(): Promise<string> {
  const { csrf_token } = await get<{ csrf_token: string }>("/csrf");
  if (!csrf_token)
    throw new Error("Security check unavailable. Refresh and try again.");
  return csrf_token;
}
// Retained retries belong to one authoritative user/organization context, never to a hook.
const replayKeys = new Map<string, string>();
let replayContext = "anonymous";
let replayEpoch = 0;
export function clearReplayContext() {
  replayKeys.clear();
  replayEpoch += 1;
  replayContext = "anonymous";
}
export function setReplayContext(userId: number, companyId: number) {
  const next = `${userId}:${companyId}`;
  if (next !== replayContext) { replayKeys.clear(); replayEpoch += 1; }
  replayContext = next;
}
function retainedMutation(path: string, method: string) {
  // Keep the existing work-order replay family, but match additive PM routes exactly.
  return path.startsWith("/work-orders") ||
    (method === "POST" && (path === "/maintenance-plans" || /^\/maintenance-plans\/\d+\/(pause|resume)$/.test(path) || /^\/maintenance-reminders\/\d+\/(retry|ack)$/.test(path))) ||
    (method === "PATCH" && /^\/maintenance-plans\/\d+$/.test(path));
}
export async function mutate<T>(
  path: string,
  body: unknown = {},
  method = "POST",
): Promise<T> {
  const payload = JSON.stringify(body);
  const maintenance = retainedMutation(path, method);
  const context = replayContext;
  const epoch = replayEpoch;
  const fingerprint = `${epoch}:${context}:${method}:${path}:${payload}`;
  const key = maintenance
    ? replayKeys.get(fingerprint) || crypto.randomUUID()
    : undefined;
  if (key) replayKeys.set(fingerprint, key);
  const token = await csrf();
  if (maintenance && (context !== replayContext || epoch !== replayEpoch))
    throw new Error("Your organization or session changed. Open the current record before retrying.");
  const response = await fetch(`${BASE}${path}`, {
    method,
    credentials: "include",
    cache: "no-store",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      "X-CSRF-Token": token,
      ...(key ? { "Idempotency-Key": key } : {}),
    },
    body: payload,
  });
  const result = await decode<T>(response);
  if (maintenance && (context !== replayContext || epoch !== replayEpoch))
    throw new Error("Your organization or session changed. Check the current record; the previous request may have been saved.");
  if (key) replayKeys.delete(fingerprint);
  return result;
}
export async function uploadManual(
  file: File,
  assetId: number,
  title: string,
  onProgress: (value: number | null) => void,
): Promise<{ document: import("./types").Manual }> {
  const token = await csrf();
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    request.open("POST", `${BASE}/documents`);
    request.withCredentials = true;
    request.setRequestHeader("X-CSRF-Token", token);
    request.setRequestHeader("Accept", "application/json");
    request.upload.onprogress = (event) =>
      onProgress(
        event.lengthComputable
          ? Math.round((event.loaded / event.total) * 100)
          : null,
      );
    request.onerror = () =>
      reject(new Error("Upload interrupted. Check your connection and retry."));
    request.ontimeout = () =>
      reject(new Error("Upload timed out. Retry with a smaller PDF."));
    request.timeout = 120000;
    request.onload = () => {
      let body;
      try {
        body = JSON.parse(request.responseText);
      } catch {
        reject(new Error("The server returned an unreadable upload response."));
        return;
      }
      if (request.status < 200 || request.status >= 300)
        reject(new ApiError(request.status, body));
      else resolve(body);
    };
    const form = new FormData();
    form.append("file", file);
    form.append("asset_id", String(assetId));
    if (title.trim()) form.append("title", title.trim());
    request.send(form);
  });
}
export async function download(
  path: string,
  fallbackName: string,
): Promise<void> {
  const response = await fetch(`${BASE}${path}`, {
    credentials: "include",
    cache: "no-store",
  });
  if (!response.ok) {
    await decode(response);
    return;
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  const match = /filename="?([^";]+)"?/i.exec(
    response.headers.get("Content-Disposition") || "",
  );
  anchor.download = Array.from(match?.[1] || fallbackName, (character) =>
    character.charCodeAt(0) < 32 || character === "/" || character === "\\"
      ? "_"
      : character,
  ).join("");
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export function queryString(
  values: Record<string, string | number | boolean | null | undefined>,
): string {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(values))
    if (value !== undefined && value !== null && value !== "")
      query.set(key, String(value));
  return query.size ? `?${query}` : "";
}
