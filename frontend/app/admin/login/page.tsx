"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import FormField from "@/components/FormField";
import { adminLogin, adminMe } from "@/lib/api";

export default function AdminLoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    // Primes the csrftoken cookie (ensure_csrf_cookie) and redirects away if
    // a session is already active.
    adminMe().then((result) => {
      if (result.ok) router.replace("/admin");
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);

    const result = await adminLogin(username, password);
    setSubmitting(false);

    if (!result.ok) {
      setError("Those credentials weren't recognised");
      return;
    }
    router.replace("/admin");
  }

  return (
    <div className="mx-auto flex min-h-screen max-w-[380px] flex-col justify-center px-4">
      <p className="eyebrow mb-3">Admin</p>
      <h1 className="mb-8 text-2xl font-semibold">Sign in</h1>

      <form onSubmit={handleSubmit} className="flex flex-col gap-6" noValidate>
        <FormField id="username" label="Username" required>
          {({ describedBy, invalid }) => (
            <input
              id="username"
              type="text"
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              aria-describedby={describedBy}
              aria-invalid={invalid}
              className="w-full border-0 border-b border-rule bg-transparent py-2 text-base focus:border-oxide focus:outline-none"
            />
          )}
        </FormField>

        <FormField id="password" label="Password" required>
          {({ describedBy, invalid }) => (
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              aria-describedby={describedBy}
              aria-invalid={invalid}
              className="w-full border-0 border-b border-rule bg-transparent py-2 text-base focus:border-oxide focus:outline-none"
            />
          )}
        </FormField>

        {error && (
          <p role="alert" className="text-sm text-oxide">
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={submitting}
          className="eyebrow self-start bg-ink px-6 py-3 text-[color:var(--surface)] disabled:opacity-50"
        >
          {submitting ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </div>
  );
}
