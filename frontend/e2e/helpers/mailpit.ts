import { loadFixtures } from "./fixtures";

interface MailpitMessageSummary {
  ID: string;
  Subject: string;
}

interface MailpitMessage {
  Text: string;
}

/** Polls Mailpit for the newest message whose subject contains `fragment`.
 * Real email delivery is asynchronous relative to the triggering request,
 * so this polls rather than assuming the mail has landed immediately. */
export async function findEmailBySubjectFragment(
  fragment: string,
  timeoutMs = 10_000
): Promise<{ id: string; text: string; subject: string }> {
  const mailpitUrl = loadFixtures().mailpitUrl;
  const deadline = Date.now() + timeoutMs;

  while (Date.now() < deadline) {
    const res = await fetch(`${mailpitUrl}/api/v1/messages?limit=50`);
    const data = (await res.json()) as { messages: MailpitMessageSummary[] };
    const match = data.messages.find((m) => m.Subject.includes(fragment));
    if (match) {
      const full = (await fetch(`${mailpitUrl}/api/v1/message/${match.ID}`).then((r) =>
        r.json()
      )) as MailpitMessage;
      return { id: match.ID, text: full.Text, subject: match.Subject };
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error(`No email found with subject containing "${fragment}" within ${timeoutMs}ms`);
}

export function extractTrackingToken(emailText: string): string {
  const match = emailText.match(/\/track\/([A-Za-z0-9_-]+)\//);
  if (!match) throw new Error(`No tracking link found in email body:\n${emailText}`);
  return match[1];
}
