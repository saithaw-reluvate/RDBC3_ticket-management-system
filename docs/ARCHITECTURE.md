# Architecture — RBDC Exercise 3 Ticket Management System

**Status:** Step 0 complete and approved.
**Scope:** System-level architecture only. Detailed schema, endpoint, and component
design belong to Steps 1–3.
**Precedence:** `docs/RBDC_Ex_3.pdf` (the brief) > this document > implementation.

---

## 1. System Topology

Four containers in development, three in production.

```
Browser
   │
   ▼
┌──────────────────────────┐
│ frontend (Next.js 14)    │  :3000
│  - public pages          │
│  - /api/* → rewrite ─────┼──┐  (server-side proxy, same browser origin)
└──────────────────────────┘  │
                              ▼
                    ┌──────────────────────────┐
                    │ backend (Django 5.1+DRF) │  :8000
                    │  - 3 trust planes        │
                    │  - serves attachments    │
                    │    through access checks │
                    └───────────┬──────────────┘
                                │
                    ┌───────────▼──────────────┐   ┌──────────────────┐
                    │ db (PostgreSQL)          │   │ mail (dev only)  │
                    │  named volume            │   │ Mailpit :8025    │
                    └──────────────────────────┘   └──────────────────┘

Volumes: pgdata, media (attachments), logs
```

Django is **not** publicly exposed in production. The browser only ever talks to the
Next.js origin.

---

## 2. Trust Planes

The core security shape of the application. Every endpoint belongs to exactly one plane.

| Plane | Who | Authentication | Routes |
|---|---|---|---|
| **Public** | Anyone | None, throttled | `POST /api/tickets/` (submission only) |
| **Customer** | Ticket holder | Opaque token in URL | `/api/track/<token>/…` — read status, history, responses; download own attachments |
| **Admin** | Staff | Django session cookie + CSRF | `/api/admin/…` — list, update status/priority, respond |

Rules that hold across the whole system:

- The customer plane is **read-only** apart from the initial submission.
- A token grants access to **its own ticket and nothing else**.
- No endpoint ever accepts a numeric or sequential ticket ID as proof of identity.

---

## 3. Approved Decisions

### Decision 1 — Token storage: multiple hashed tokens per ticket

Raw access tokens are never stored. Only a SHA-256 digest is persisted.

Because a hash cannot be reversed, a tracking link cannot be rebuilt after issue.
Therefore **a ticket may have more than one active access token**: one is minted when
the ticket is created, and each later notification email that needs a link mints a
fresh one. Previously issued links remain valid until they expire or are revoked.

*Rationale:* the only option that satisfies "never store the raw token" without
degrading the product. Rejected alternatives: notification emails without links
(poor UX, weakens the brief's notification requirement); a single reversibly
encrypted token (key compromise exposes every token).

### Decision 2 — Token generation, expiry, revocation

- **Generation:** `secrets.token_urlsafe(32)` — 256 bits of entropy, URL-safe.
- **Storage:** SHA-256 digest with a unique index. Chosen over bcrypt/Argon2
  deliberately: this is a high-entropy random secret, not a human password. It must
  be *indexable* for lookup, and key stretching adds nothing against 256 bits.
- **Expiry:** 90 days from issue. Comfortably outlives a support ticket while
  bounding exposure if a mailbox is later compromised.
- **Revocation:** tokens can be revoked individually. Admins can revoke and issue a
  fresh tracking link.
- **Never logged.** Log lines reference the ticket's internal ID, never the token.

### Decision 3 — Single-origin routing via Next.js rewrites

Next.js `rewrites` proxy `/api/*` to Django, so the browser sees **one origin**.

*Rationale:* admin session cookies plus a separate frontend origin would require
`SameSite=None; Secure`, which fails over plain HTTP on an EC2 IP address. A single
origin means session cookies and CSRF work with default-safe settings, no CORS
configuration, and no additional container. If a real domain and HTTPS are wanted
later, nginx or Caddy can be added in Step 5 without touching application code.

### Decision 4 — Email: Mailpit in development, Gmail SMTP in production

One SMTP code path on both sides; only environment variables change.

Mailpit is used in development specifically so the tracking link can be *clicked*,
which is what makes the identification flow testable end to end.

*Updated in Step 5 (`docs/DEPLOYMENT.md`):* production uses Gmail SMTP
(`smtp.gmail.com:587`, STARTTLS, a Google App Password) rather than the originally
planned AWS SES. This was already the project's pre-approved fallback for exactly
this decision — switching to it as the primary choice removes the AWS
account/sandbox dependency entirely, with the same one-SMTP-code-path, only-env-vars-
change mechanism.

### Decision 5 — Attachments on a Docker volume, served through access checks

Attachments live on a named Docker volume and are served **only** through a Django
view that enforces the caller's token or admin session.

*Rationale:* no AWS setup, no new dependency, and access control is real. The
architectural commitment is that attachments are **never** served from a public
static path. Migrating to S3 via `django-storages` later is a settings change.

### Decision 6 — Jest for components, Playwright for end-to-end

The brief says "Use Jest for frontend component testing and end-to-end tests." Jest
cannot drive a browser, so Jest covers component tests and Playwright covers true
end-to-end flows.

This is a deliberate, documented deviation from the brief's literal wording and will
be explained in the final README.

---

## 4. Repository Layout

Monorepo, single Git repository. Top level only; internals are Steps 1–3 work.

```
/
├── CLAUDE.md
├── README.md
├── .env.example                 # committed; .env is gitignored
├── docker-compose.yml           # development
├── docker-compose.prod.yml      # EC2
├── docs/
│   ├── RBDC_Ex_3.pdf
│   ├── ARCHITECTURE.md
│   └── postman/                 # collection + environment, committed
├── backend/
└── frontend/
```

---

## 5. Cross-Cutting Concerns

**Configuration.** A single `settings.py` driven by environment variables; `.env`
loaded in development, real environment variables on EC2. No `base/dev/prod` settings
split — unnecessary at this size. `.env.example` documents every key with dummy values.

**Logging.** Two file handlers — `logs/application.log` at INFO and `logs/error.log`
at ERROR — plus console output. Mounted as a Docker volume and gitignored. A small
central helper handles ticket-event logging so that access tokens cannot leak into a
log line by accident.

**Error handling.** One DRF exception handler returns a uniform, user-safe JSON error
body and logs the underlying exception with `logger.exception()`. Stack traces never
cross the API boundary.

**Email dispatch.** Synchronous, inside the request, wrapped so that a mail failure is
logged as an error but never fails ticket creation. No Celery or Redis — unjustified
infrastructure at this scale.

**Abuse control.** DRF's built-in anonymous throttle on the public submission
endpoint, and a throttle on token lookups to blunt guessing. Built in, no new
dependency.

**Referrer leakage.** `Referrer-Policy: no-referrer` on customer ticket pages, since
the access token lives in the URL path by design.

---

## 6. Testing Architecture

- **Backend:** `pytest-django` + `coverage.py`, tests beside each app.
- **Frontend components:** Jest + React Testing Library.
- **End-to-end:** Playwright, covering the full flow — submit → email captured in
  Mailpit → open tracking link → admin responds → customer sees the update.
- **Postman:** collection committed under `docs/postman/`, exercised at the end of
  Step 2 **before** any frontend integration.
- **Coverage:** at least 70%, measured per side and reported in the README at Step 6.

Tests are written alongside each step, never deferred wholesale to Step 6.

---

## 7. Deployment

A single EC2 instance running `docker compose -f docker-compose.prod.yml up -d`.

- PostgreSQL in a container with a named volume. Managed RDS is out of scope.
- Multi-stage Dockerfiles. Next.js built in standalone mode; Django served by Gunicorn.
- Secrets injected as environment variables on the instance — never baked into images,
  never committed.

---

## 8. Git Plan

`main` stays deployable. One branch per unit of work, including the brief's named
examples:

```
feature/database-schema         (Step 1)
feature/client-identification   (Step 2 — tokens + tracking)
feature/ticket-creation         (Step 2 — submission API)
feature/admin-management        (Step 2)
feature/frontend-*              (Step 3)
feature/docker-deployment       (Step 5)
```

---

## 9. Deferred to Later Steps

Deliberately **not** decided here:

- Exact model names, fields, relationships, indexes, and constraints — **Step 1**.
- Ticket history/audit model shape and recording behaviour — **Step 1**.
- Attachment multiplicity and validation rules (type, size limits) — **Step 1/2**.
- Concrete endpoint paths, serializers, permissions, and status codes — **Step 2**.
- Page structure, component breakdown, and styling approach — **Step 3**.
- Whether the optional analytics dashboard is built at all — only after every
  mandatory feature is complete.
