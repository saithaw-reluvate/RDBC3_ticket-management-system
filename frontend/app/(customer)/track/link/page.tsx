"use client";

import { useState } from "react";
import FormField from "@/components/FormField";
import { ERROR_PRESENTATION, resendLink } from "@/lib/api";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function TrackLinkPage() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [sent, setSent] = useState(false);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setFormError(null);

    if (!email.trim() || !EMAIL_RE.test(email.trim())) {
      setError("Enter a valid email address.");
      return;
    }
    setError(null);
    setSubmitting(true);

    const result = await resendLink(email.trim());
    setSubmitting(false);

    if (!result.ok) {
      setFormError(ERROR_PRESENTATION[result.code].message);
      return;
    }
    setSent(true);
  }

  if (sent) {
    return (
      <div className="mx-auto max-w-[580px] px-4 py-16 text-center xs:px-6">
        <p className="eyebrow mb-3">Tracking link</p>
        <h1 className="mb-4 text-2xl font-semibold">Check your inbox.</h1>
        <p className="text-sm text-muted">
          If that address has reports on file, a tracking link has been sent to it.
        </p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-[580px] px-4 py-16 xs:px-6">
      <p className="eyebrow mb-3">Tracking link</p>
      <h1 className="mb-6 text-2xl font-semibold">Request a new tracking link</h1>
      <p className="mb-8 text-sm text-muted">
        Enter the email you used when filing your report and we&apos;ll send a fresh link.
      </p>

      <form onSubmit={handleSubmit} className="flex flex-col gap-6" noValidate>
        <FormField id="email" label="Email address" required error={error ?? undefined}>
          {({ describedBy, invalid }) => (
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              aria-describedby={describedBy}
              aria-invalid={invalid}
              className="w-full border-0 border-b border-rule bg-transparent py-2 text-base focus:border-oxide focus:outline-none"
            />
          )}
        </FormField>

        {formError && (
          <p role="alert" className="text-sm text-oxide">
            {formError}
          </p>
        )}

        <button
          type="submit"
          disabled={submitting}
          className="eyebrow self-start bg-ink px-6 py-3 text-[color:var(--surface)] disabled:opacity-50"
        >
          {submitting ? "Sending…" : "Send link"}
        </button>
      </form>
    </div>
  );
}
