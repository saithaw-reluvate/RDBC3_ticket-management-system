"use client";

import { useState } from "react";

export default function Composer({
  reporterName,
  onSubmit,
  submitting = false,
}: {
  reporterName: string;
  onSubmit: (message: string, isInternal: boolean) => void | Promise<void>;
  submitting?: boolean;
}) {
  const [isInternal, setIsInternal] = useState(false);
  const [message, setMessage] = useState("");

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!message.trim()) return;
    await onSubmit(message, isInternal);
    setMessage("");
  }

  return (
    <form
      onSubmit={handleSubmit}
      className={`border p-4 ${isInternal ? "border-ochre bg-internal-bg" : "border-rule bg-surface"}`}
    >
      <div role="group" aria-label="Reply visibility" className="mb-3 flex gap-4">
        <button
          type="button"
          aria-pressed={!isInternal}
          onClick={() => setIsInternal(false)}
          className={`eyebrow border-b-2 pb-1 ${!isInternal ? "border-ink text-ink" : "border-transparent text-faint"}`}
        >
          Public reply
        </button>
        <button
          type="button"
          aria-pressed={isInternal}
          onClick={() => setIsInternal(true)}
          className={`eyebrow border-b-2 pb-1 ${isInternal ? "border-ochre text-ochre" : "border-transparent text-faint"}`}
        >
          Internal note
        </button>
      </div>

      <p className="mb-3 text-sm" style={isInternal ? { color: "var(--ochre)" } : undefined}>
        {isInternal
          ? "Visible to staff only — the customer will not see this."
          : `Visible to the customer — ${reporterName} will be emailed a link to read it.`}
      </p>

      <label htmlFor="composer-message" className="sr-only">
        Message
      </label>
      <textarea
        id="composer-message"
        value={message}
        onChange={(event) => setMessage(event.target.value)}
        rows={4}
        required
        className="w-full resize-y border-0 border-b border-rule bg-transparent py-2 text-base focus:border-oxide focus:outline-none"
      />

      <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
        <p className="text-xs text-faint">
          {isInternal
            ? "Kept on the ticket for the support team. No email is sent."
            : "A fresh tracking link is included in every reply email."}
        </p>
        <button
          type="submit"
          disabled={submitting || !message.trim()}
          className={`eyebrow px-4 py-2 text-[color:var(--surface)] disabled:opacity-50 ${
            isInternal ? "bg-ochre" : "bg-ink"
          }`}
        >
          {isInternal ? "Add internal note" : "Send reply"}
        </button>
      </div>
    </form>
  );
}
