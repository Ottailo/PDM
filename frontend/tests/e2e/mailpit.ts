import type { APIRequestContext } from "@playwright/test";
// Local E2E helper only. Never imported by customer runtime.
const MAILPIT = process.env.PDM_MAILPIT_URL || "http://127.0.0.1:8026";
const mailOrigin = new URL(MAILPIT);
if (!["127.0.0.1", "localhost"].includes(mailOrigin.hostname) || mailOrigin.protocol !== "http:") throw new Error("E2E mail must use an isolated loopback Mailpit origin");
export async function waitForMailLink(
  request: APIRequestContext,
  email: string,
  path: string,
): Promise<string> {
  const until = Date.now() + 45000;
  while (Date.now() < until) {
    const response = await request.get(`${MAILPIT}/api/v1/messages`);
    if (!response.ok())
      throw new Error(
        `Local Mailpit unavailable (${response.status()}). Start the real SMTP sink before integration testing.`,
      );
    const list = (await response.json()) as {
      messages: { ID: string; To: { Address: string }[] }[];
    };
    for (const message of list.messages || []) {
      if (
        !message.To.some(
          (recipient) =>
            recipient.Address.toLowerCase() === email.toLowerCase(),
        )
      )
        continue;
      const detailResponse = await request.get(
        `${MAILPIT}/api/v1/message/${message.ID}`,
      );
      const detail = (await detailResponse.json()) as {
        Text?: string;
        HTML?: string;
      };
      const body = `${detail.Text || ""}\n${detail.HTML || ""}`.replaceAll(
        "&amp;",
        "&",
      );
      const links = body.match(/https?:\/\/[^\s<>"']+/g) || [];
      const link = links.find((candidate) => {
        try {
          const url = new URL(candidate);
          return url.pathname === path && !!url.searchParams.get("token");
        } catch {
          return false;
        }
      });
      if (link) return link;
    }
    await new Promise((resolve) => setTimeout(resolve, 700));
  }
  throw new Error(
    `No real SMTP message for ${email} with a ${path} link arrived within 45 seconds.`,
  );
}
