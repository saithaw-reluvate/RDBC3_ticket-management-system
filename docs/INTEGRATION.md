# Integration Record — RBDC Exercise 3 Ticket Management System

**Status:** Step 4 complete. Unlike Steps 0–3, this document is a record of what
was connected, verified, and fixed — Step 4 has no separate pre-approval planning
gate in `CLAUDE.md`'s Development Flow, so there is no prior "approved plan" version
of this file to compare against.
**Scope:** Full end-to-end verification of frontend + backend + database + email,
and the Playwright E2E test infrastructure that verifies it going forward.
**Precedence:** `docs/RBDC_Ex_3.pdf` > `CLAUDE.md` > `docs/ARCHITECTURE.md` >
`docs/DATABASE.md` > `docs/BACKEND.md` > `docs/FRONTEND.md` > this document.

---

## 1. What Step 4 covers

Steps 1–3 each verified their own layer in isolation (pytest against real
Postgres, Postman against the live API, Jest component tests plus one manual
browser QA pass). Step 4 connects all four pieces — Next.js, Django, Postgres,
Mailpit — and exercises them together through a committed, repeatable
Playwright suite, using the real stack throughout. No mocks.

---

## 2. E2E test infrastructure

```
frontend/
├── playwright.config.ts      # serial, 1 worker, chromium only
├── e2e/
│   ├── global-setup.ts        # seeds fixtures, clears Mailpit
│   ├── helpers/
│   │   ├── fixtures.ts         # reads the JSON global-setup writes
│   │   └── mailpit.ts          # polls Mailpit, extracts tracking tokens
│   ├── fixtures/                # tiny attachment files (pdf, disallowed exe)
│   ├── customer-admin-journey.spec.ts   # the main flow (§3)
│   ├── public-resend-link.spec.ts
│   └── form-validation.spec.ts
backend/tickets/management/commands/seed_e2e.py   # idempotent fixture setup
```

**Running it:** `docker compose up -d db mailpit`, `manage.py runserver` (backend),
then from `frontend/`: `npx playwright install chromium` (once), `npm run test:e2e`.
`playwright.config.ts`'s `webServer` starts `next dev` automatically if nothing is
already listening on port 3000. `global-setup.ts` shells out to the backend's
`manage.py seed_e2e`, which creates a dedicated `e2e_admin` staff user (password via
`E2E_ADMIN_PASSWORD`, dev-only default baked in — see `frontend/.env.example`) and a
ticket with a pre-expired token (the one state the API cannot produce itself).

**Serial by design.** `fullyParallel: false`, `workers: 1`. The suite shares one
real Mailpit inbox and hits real DRF throttles (`ticket_create` 5/hour,
`resend_link` 3/hour) — parallel workers would race on both. The main journey is
written as **one `test()` with `test.step()` stages**, not separate `test()` cases,
because Playwright gives every `test()` its own browser context (fresh cookie jar)
by default even inside `describe.serial`; splitting the journey into multiple
`test()`s silently drops the admin session between stages (found live — see §4).

**Throttle budget.** One full run of the suite uses 1 of 5 `ticket_create` calls/hour
(the journey's real form submission) and 2 of 3 `resend_link` calls/hour (the public
recovery-form spec). Running the full suite more than twice against the same
backend process within an hour will hit real throttling on the second endpoint —
restart the backend (an in-memory `LocMemCache`, so a fresh process clears it) for
a guaranteed-clean run. This is the suite correctly exercising the real Step 2
throttles, not a defect.

---

## 3. The main journey (`customer-admin-journey.spec.ts`)

One continuous flow through the real stack:

1. Customer submits an incident with an attachment through the actual form.
2. The creation email arrives in Mailpit; the tracking link in it opens the ticket.
3. Customer downloads their own attachment.
4. Invalid and expired tokens are distinguished from the valid one.
5. `/admin` and `/admin/tickets/<reference>` both redirect to login while signed out.
6. A wrong admin password is rejected with generic copy (never reveals which field).
7. Admin signs in, finds the ticket via search.
8. Status, priority and category are changed and confirmed to persist after a reload
   (not just in optimistic client state).
9. Admin downloads the customer's attachment.
10. A public reply reaches both the customer's inbox (new email) and their ticket
    page.
11. An internal note is confirmed absent from the customer's page — checked in
    rendered text *and* the raw HTML/RSC payload, not just visible text.
12. Resend-link mints a new working token without revoking the original.
13. Revoke-links invalidates every active token for the ticket (both the original
    and the resent one).
14. Logout ends the session; protected routes redirect again.

Two smaller specs cover what doesn't belong in that stateful flow: the public
`/track/link` recovery form's known/unknown-address parity, and client-side form
validation (empty fields, invalid email, disallowed attachment type) — none of
which touch the network, so they carry no throttle cost.

---

## 4. Defects found and fixed

All are test-infrastructure or test-script defects surfaced by actually running the
real stack together — the application code itself needed no changes in Step 4.

1. **Assertion checked `<script>` tag contents as if they were visible text.**
   `page.textContent("body")` includes inline RSC hydration `<script>` payloads;
   asserting "no `/track/` link on the receipt page" this way falsely failed on the
   page's own legitimate `/track/link` recovery CTA. Fixed by checking actual
   anchor `href`s instead of raw text content.
2. **Per-`test()` browser context drops the admin session.** Splitting the journey
   into separate `test()` cases inside `describe.serial` (assuming session/cookies
   would persist across them) silently broke every test after login, each hitting
   the signed-out redirect and timing out waiting for elements that were never going
   to appear. Fixed by restructuring the journey as one `test()` with `test.step()`
   stages sharing a single `page`/context throughout — see §2.
3. **`page.reload()` raced ahead of in-flight PATCH requests.** Firing three rapid
   `selectOption()` calls (status, priority, category) and immediately reloading
   let the browser abort whichever PATCH requests hadn't finished yet — only one of
   three ever reached the server. This looked exactly like a real persistence bug
   (category silently reverted after reload) until the server log showed only one
   `PATCH` had actually arrived. Fixed by awaiting each `PATCH` response before
   triggering the next change or reloading.

No genuine defect in the shipped Steps 1–3 application code was found. Combined
with the manual browser QA already done in Step 3 (where three real application
defects *were* found and fixed — see the Step 3 QA commit), the stack is now
verified twice, by two different methods, with a clean result on the second pass.

---

## 5. Verification results

- Playwright: 5/5 specs passing (customer-admin-journey's 14 `test.step()` stages,
  plus form-validation ×3, public-resend-link ×1), run twice consecutively against
  a fresh backend process for repeatability.
- Backend: 118 pytest tests passing, `makemigrations --check` clean.
- Frontend: 38 Jest tests passing, ESLint clean, `next build` clean.
- Logs: grepped for raw/hashed token patterns after the full E2E run — clean.

---

## 6. Out of scope for Step 4

Docker packaging and AWS EC2 deployment (Step 5); CI wiring for the E2E suite
(nothing in this repo runs it automatically yet — it is a local, on-demand
command); the optional analytics dashboard.
