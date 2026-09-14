# RBDC Exercise 3 — Ticket Management System

## Project Source of Truth
- `docs/RBDC_Ex_3.pdf` is the original project brief.
- `docs/ARCHITECTURE.md` is the approved Step 0 architecture.
- `docs/DATABASE.md` is the approved Step 1 database design.
- `docs/BACKEND.md` is the approved Step 2 backend design.
- `docs/FRONTEND.md` is the approved Step 3 frontend design.
- `docs/INTEGRATION.md` is the Step 4 integration record (what was connected,
  verified, and fixed — see its own note on why it isn't a pre-approved plan
  like the others).
- Precedence: brief > CLAUDE.md > ARCHITECTURE.md > DATABASE.md > BACKEND.md >
  FRONTEND.md > INTEGRATION.md > implementation.
- Read the relevant design docs before any implementation step.

## Project Goal
Build a Ticket Management System where customers can submit incident tickets without creating an account.

Customer flow:
1. Submit name, email, description, and optional attachment.
2. Backend creates the ticket.
3. Backend generates a secure unique tracking token/link.
4. Tracking link is emailed to the customer.
5. Customer uses the link without logging in.
6. Customer can view ticket status, history, and admin responses.

Admins have a restricted authenticated dashboard for managing tickets.

## Required Stack
- Next.js 14
- Django 5.1
- Django REST Framework
- PostgreSQL
- Docker + Docker Compose
- AWS EC2

These are fixed requirements from the brief.

## Core Models
The brief requires:
- `Client`
- `Ticket`
- `Response`

`Ticket` includes incident details, status, priority, and history.

Example statuses:
- Open
- In Progress
- Resolved

Example priorities:
- Low
- Medium
- High

Approved supporting models (see `docs/DATABASE.md`):
- `TicketAccessToken` — hashed customer access tokens, multiple live per ticket
- `TicketEvent` — structured ticket history/audit trail
- `Attachment` — multiple per ticket

Clients are NEVER Django users. Admins use Django's default `auth.User`; admin access
is `is_staff`. Do not introduce a custom user model.

## Required Features
- Client identification without login
- Secure unique ticket tracking link
- Ticket submission
- Optional attachments
- Ticket status/history tracking
- Admin ticket management
- Status and priority updates
- Admin responses/comments
- Email notifications
- Validation and user-friendly errors
- Backend logging

Analytics dashboard is OPTIONAL. Only consider it after all mandatory features are complete.

## Required Frontend Areas
- Incident Reporting
- Ticket Status
- Restricted Admin Dashboard

## Testing Requirements
- Django model/API tests
- Jest frontend tests
- End-to-end testing
- At least 70% test coverage
- Postman testing of backend APIs before frontend integration
- Test successful requests and relevant error/edge cases

## Git Requirements
- Use meaningful commits.
- Use feature branches where appropriate.
- Examples from the brief:
  - `feature/client-identification`
  - `feature/ticket-creation`

## Deployment
- Dockerize frontend, backend, and PostgreSQL.
- Manage services using Docker Compose.
- Deploy to AWS EC2.
- Final README must document setup, deployment, usage, known issues, and future improvements.
- Final deliverables are GitHub repository + live AWS URL.

AWS EC2 is the deployment target. If any other hosting provider is referenced anywhere, it is disregarded in favour of AWS EC2.

# Approved Project Decisions

## Customer Access
Do NOT use JWT for customers.

Use a cryptographically secure opaque per-ticket token in the emailed tracking link.

The token must be unpredictable and URL-safe.

Do not expose sequential ticket IDs as authentication.

Never log raw ticket access tokens.

Raw customer access tokens are NEVER stored. Only a hash is persisted, and the
presented token is validated against it.

Approved token design (Step 0):
- Generation: `secrets.token_urlsafe(32)` — 256 bits, URL-safe.
- Storage: SHA-256 digest with a unique index. Not bcrypt/Argon2 — this is a
  high-entropy random secret, not a human password, and it must be indexable.
- Expiry: 90 days from issue.
- Revocation: tokens are individually revocable; admins can issue a fresh link.
- A ticket MAY have multiple active tokens. One is minted at ticket creation, and
  each later notification email that needs a link mints a fresh one. Previously
  issued links stay valid until they expire or are revoked. This exists because a
  hash cannot be reversed to rebuild a link.

## Admin Authentication
Use Django session-based authentication for admins.

Do not introduce JWT unless we explicitly revisit this decision.

## Ticket History
Use a separate structured ticket history/audit model rather than relying only on an unstructured JSON history field.

Approved (Step 1): the model is `TicketEvent`, with structured `old_value`/`new_value`
columns so status and priority changes record uniformly. Full field list in
`docs/DATABASE.md`.

`TicketEvent.metadata` is a small optional JSON convenience column beside the
structured fields — it is NOT the history mechanism, and must never hold a raw or
hashed token.

Customer-visible events are filtered by a code whitelist (`CREATED`, `STATUS_CHANGED`,
`RESPONSE_ADDED`), not by a database column. All other event types are operational.

## Backend Logging
Use Django/Python logging with persistent log files. Backend log files are wanted particularly for tracking errors and exceptions caught during backend execution.

Planned:
- `logs/application.log`
- `logs/error.log`

Use:
- `logger.info()` for important application events
- `logger.warning()` for warnings
- `logger.error()` where appropriate
- `logger.exception()` inside exception handlers when stack traces are needed

Important events may include:
- ticket creation
- status changes
- priority changes
- admin responses
- email failures
- attachment failures
- unexpected backend exceptions

Do not:
- silently swallow exceptions
- add unnecessary try/except blocks everywhere
- expose stack traces to frontend users
- log passwords, credentials, session secrets, or raw ticket access tokens

Log files must not be committed to Git.

## Routing and Origin
Next.js `rewrites` proxy `/api/*` to Django so the browser sees a single origin.

Do not introduce CORS-with-credentials across separate origins — admin session
cookies would require `SameSite=None; Secure`, which fails over plain HTTP on EC2.

nginx/Caddy may be added in Step 5 if a real domain and HTTPS are wanted. That must
not require application code changes.

## Trust Planes
Every endpoint belongs to exactly one plane:
- Public — anonymous, throttled. Ticket submission only.
- Customer — opaque token in the URL. Read-only, scoped to its own ticket.
- Admin — Django session + CSRF.

Never accept a sequential or numeric ticket ID as proof of identity.

## Email
One SMTP code path everywhere; only environment variables change.
- Development: Mailpit container (tracking links must be clickable in dev).
- Production: AWS SES.
- Approved fallback if the SES sandbox blocks the deadline: Gmail SMTP app password.

Send email synchronously inside the request, wrapped so a mail failure is logged as
an error but never fails ticket creation. Do NOT add Celery or Redis.

## Attachments
Stored on a named Docker volume and served ONLY through a Django view that enforces
the caller's token or admin session.

Attachments must never be served from a public static path. Moving to S3 later should
be a settings change.

## Testing Tooling
- Backend: `pytest-django` + `coverage.py`.
- Frontend components: Jest + React Testing Library.
- End-to-end: Playwright.

Playwright is a deliberate deviation from the brief's literal "Jest for end-to-end"
wording, because Jest cannot drive a browser. Document this in the final README.

## Other Approved Defaults
- Single `settings.py` driven by environment variables. No base/dev/prod split.
- One DRF exception handler returning uniform, user-safe JSON errors.
- DRF built-in throttling on public submission and on token lookups.
- `Referrer-Policy: no-referrer` on customer ticket pages.
- PostgreSQL runs in a container with a named volume. Not RDS.
- Gunicorn for Django; Next.js standalone build.

## Database Rules
Full design in `docs/DATABASE.md`. Rules that must not be violated:
- `Ticket.reference` (`TKT-XXXXXXXX`) is DISPLAY ONLY. Never authentication.
- Statuses are exactly `OPEN`, `IN_PROGRESS`, `RESOLVED`. Do not add `CLOSED`.
- `Ticket.category` is required at submission and admin-reassignable. The category
  set is fixed `TextChoices`, never an editable database table. The seven approved
  values (`ACCOUNT_ACCESS`, `BILLING`, `BUG`, `PERFORMANCE`, `DATA`, `SECURITY`,
  `OTHER`) are enumerated with their labels in `docs/DATABASE.md` §2 Decision 13 —
  that table is the source of truth, do not infer values elsewhere.
- The customer plane must filter `Response.is_internal=False`.
- Deletion policy: `Client → Ticket` is `PROTECT`; Ticket children `CASCADE`; staff
  references `SET_NULL` so audit rows survive staff removal.
- Value/consistency rules are enforced by DB-level `CheckConstraint`s, not only by
  Django validators.
- All models live in a single `tickets` app.
- Run tests against real PostgreSQL, never SQLite — constraint behaviour differs.

## API Rules
Full design in `docs/BACKEND.md`. Rules that must not be violated:
- Admin routes key on `Ticket.reference`, never the primary key.
- The customer plane is read-only. It must filter `Response.is_internal=False` and the
  customer-visible event whitelist, and must never expose response authors.
- The submit response never contains the tracking link. Email is the only delivery
  path for links.
- Every email needing a link mints a fresh token.
- Email failures log and record an `EMAIL_FAILED` event, but NEVER fail the request.
- Never log a raw or hashed token, in any form, at any level.
- Token failures are distinguished: invalid (404), expired (410), revoked (410).
- Attachments are served only through an access-checked view, with
  `Content-Disposition: attachment` and `X-Content-Type-Options: nosniff`. SVG is
  never an allowed upload type.
- Views stay thin. State changes go through `tickets/services/`, and history is
  recorded by explicit service calls — never Django signals.
- All errors use the single error envelope. Stack traces never cross the API boundary.

## UI Rules
Full design in `docs/FRONTEND.md`. Rules that must not be violated:
- Poppins is the ONLY font family. Ticket references are made distinctive by weight
  and letter-spacing, never by adding a second face.
- Editorial record, not a SaaS dashboard: ledger rules instead of cards, sharp
  corners, underlined form fields.
- Status and priority are never carried by colour alone — always mark plus label.
- Customer-facing screens must NEVER expose HTTP status codes or API error codes.
- Customer responses carry no author, and customer events arrive already filtered by
  the backend. Never invent an author, and never re-filter events on the client.
- The submit response never carries the tracking link, so the receipt screen must
  carry the trust: reference, the email echoed back, and a resend route.
- The admin composer shows a persistent banner in BOTH modes; internal mode retints
  the container and its button reads "Add internal note".
- `/track/[token]` is a Server Component. Server-side fetches use the internal
  origin (`http://backend:8000`), never the browser origin.

## Pending Decisions
None open at Step 0, Step 1, Step 2, Step 3, or Step 4. Items deliberately deferred to later steps are listed in
`docs/ARCHITECTURE.md` §9.

# Development Flow

Follow ONLY this project flow:

**STEP 0 — Overall Architecture**
Plan → Review → Approve

**STEP 1 — Database**
Plan → Implement → Test

**STEP 2 — Backend**
Plan → Implement → Test with Postman

**STEP 3 — Frontend**
Plan → Implement → Test

**STEP 4 — Full Integration**
Connect frontend/backend/database → End-to-end verification

**STEP 5 — Docker + AWS**
Dockerize → Deploy to AWS EC2 → Verify

**STEP 6 — Final Testing + README**
Coverage → Final QA → Documentation

Do not create additional milestones unless explicitly requested.

For Steps 1–3:
- plan before implementation
- stop for approval after planning
- then implement
- test before declaring the step complete

Planning for the next step may happen while implementation of the current step is running, but avoid multiple implementation sessions modifying overlapping code.

# Working Rules

- Do not over-engineer the exercise.
- Prefer simple, secure, maintainable solutions.
- Do not silently make significant architecture decisions.
- If an important decision is unclear, give 2–4 options, recommend one, and wait for approval.
- Never claim something works without testing/verifying it.
- Keep tests alongside implementation rather than leaving all tests until Step 6.
- Do not add unnecessary technologies or infrastructure.
- Never commit secrets or credentials.
