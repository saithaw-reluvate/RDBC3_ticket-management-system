# Ticket Management System

A customer support ticket system built for RBDC Exercise 3. Customers report
incidents and track them without ever creating an account; staff manage the
queue from a restricted admin dashboard.

**Live application:** http://3.27.252.118

---

## Table of Contents

- [Overview](#overview)
- [Implemented Features](#implemented-features)
- [Technology Stack](#technology-stack)
- [System Architecture](#system-architecture)
- [Local Development Setup](#local-development-setup)
- [Environment Variables](#environment-variables)
- [Database Setup / Migrations](#database-setup--migrations)
- [Creating a Django Superuser](#creating-a-django-superuser)
- [Running the Backend](#running-the-backend)
- [Running the Frontend](#running-the-frontend)
- [Testing](#testing)
- [Docker Production Deployment](#docker-production-deployment)
- [AWS EC2 Deployment](#aws-ec2-deployment)
- [Security Decisions](#security-decisions)
- [Known Limitations](#known-limitations)
- [Future Improvements](#future-improvements)

---

## Overview

Customers can report an incident without logging in: they submit their name,
email, a category, a description, and optional attachments. The system
emails them a secure tracking link, which they can revisit at any time to see
the ticket's status, history, and any replies from staff — no account, no
password.

Staff sign in to a separate, session-authenticated admin dashboard to triage
the queue, change status/priority/category, reply publicly or leave an
internal note, and manage tracking links.

The project follows a staged build (architecture → database → backend →
frontend → integration → deployment → final docs), documented step by step in
`CLAUDE.md` and `docs/*.md`. Those documents are the authoritative source for
every design decision; this README summarizes the finished system and how to
run it.

## Implemented Features

- Client identification without login, via a secure opaque tracking token
- Ticket submission (name, email, subject, category, description, up to 5
  attachments, 5MB each)
- Email notification on submission, status change, and staff replies
- Self-service "resend tracking link" flow (constant response, no email
  enumeration)
- Ticket status (`OPEN` / `IN_PROGRESS` / `RESOLVED`), priority (`LOW` /
  `MEDIUM` / `HIGH`), and category tracking, each with a full history
- Structured ticket history/audit trail (`TicketEvent`), not just a JSON blob
- Admin dashboard: queue with filters/search/sort/pagination, ticket
  workspace, status/priority/category updates, public replies vs.
  internal-only notes, resend/revoke tracking links
- Session-authenticated admin login with CSRF protection
- Attachment upload and download, access-controlled on both the customer and
  admin side
- Field validation with user-friendly, non-leaking error messages
- Backend logging (`logs/application.log`, `logs/error.log`) with tracking
  tokens explicitly redacted from every log line
- Production Docker Compose deployment to AWS EC2

**Not implemented:** the optional analytics dashboard. The brief marks it
optional, and it was deliberately deferred at every step in favor of the
mandatory features above — see the "Out of Scope" section of each design doc.

## Technology Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14.2 (App Router), React 18, TypeScript, Tailwind CSS |
| Backend | Django 5.1, Django REST Framework 3.15 |
| Database | PostgreSQL 16 |
| Email | Django SMTP backend — Mailpit (dev), Gmail SMTP (production) |
| App server | Gunicorn 23 (backend), Next.js standalone server (frontend) |
| Reverse proxy | nginx (production only) |
| Containerization | Docker + Docker Compose |
| Hosting | AWS EC2 |
| Backend testing | pytest / pytest-django, coverage.py |
| Frontend testing | Jest + React Testing Library |
| End-to-end testing | Playwright |
| API testing | Postman (collection + environment committed under `docs/postman/`) |

## System Architecture

Full detail: `docs/ARCHITECTURE.md`, `docs/BACKEND.md`, `docs/FRONTEND.md`.

### Trust planes

Every endpoint belongs to exactly one of three trust planes:

| Plane | Who | Authentication | Scope |
|---|---|---|---|
| **Public** | Anyone | None, throttled | Submit a ticket; request a resend link |
| **Customer** | Ticket holder | Opaque token in the URL | Read-only: own ticket's status, history, replies, attachments |
| **Admin** | Staff | Django session + CSRF | Full ticket management |

A ticket's numeric ID and its public `TKT-XXXXXXXX` reference are never
usable as proof of identity — only a token minted specifically for that
ticket grants customer-plane access, and only an authenticated staff session
grants admin-plane access.

### Request routing

```
Browser
  │
  ▼
Next.js frontend  ──/api/*──▶  Django backend  ──▶  PostgreSQL
```

The browser only ever talks to the Next.js origin. Next.js's `rewrites()`
proxy every `/api/*` call to Django server-side, so there is a single
browser-visible origin, no CORS, and admin session cookies work with default
`SameSite`/`Secure` settings even over plain HTTP.

### Customer flow

1. Submit the incident form at `/` (name, email, subject, category,
   description, optional attachments).
2. The API creates the ticket and client, mints a tracking token, and emails
   a link — the submission response itself never contains the link
   (deliberate: the email *is* the recovery mechanism).
3. The confirmation page (`/submitted/[reference]`) shows the reference and
   next steps, with a route to request a new link if the email is lost.
4. The emailed link opens `/track/[token]` — a server-rendered page showing
   status, priority, category, the original report, attachments, and the
   full customer-visible history (creation, status changes, public replies).
   Internal staff notes and operational events are never sent to this plane.

### Admin flow

1. Sign in at `/admin/login` (Django session + CSRF).
2. `/admin` shows the ticket queue: filters, search, sort, pagination.
3. `/admin/tickets/[reference]` — update status/priority/category, reply
   publicly (emails the customer a fresh tracking link) or add an
   internal-only note (never emailed, never shown to the customer), resend or
   revoke tracking links, download attachments.

### Data model

`Client`, `Ticket`, `TicketAccessToken`, `Response`, `TicketEvent`,
`Attachment` — one Django app (`tickets`). Full schema, constraints, and
indexes in `docs/DATABASE.md`.

## Local Development Setup

Prerequisites: Docker, Python 3.12+, Node.js 20+.

```bash
git clone <repo-url>
cd Ticket-Management-System_Ex03

# 1. Environment variables
cp .env.example .env                       # backend + Postgres + email config
cp frontend/.env.example frontend/.env.local

# 2. Start Postgres + Mailpit
docker compose up -d db mailpit

# 3. Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver

# 4. Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Frontend: http://localhost:3000 · Backend API: http://localhost:8000 ·
Mailpit UI: http://localhost:8025

## Environment Variables

All backend configuration is environment-driven through one `config/settings.py`
— no separate dev/prod settings files. `.env.example` (root) and
`frontend/.env.example` document every key with placeholder values; copy them
to `.env` / `.env.local` and fill in real values. **Never commit `.env` files
or real credentials** — they are gitignored.

Backend (`.env`, root):

| Key | Purpose |
|---|---|
| `DJANGO_SECRET_KEY` | Django's cryptographic signing key |
| `DJANGO_DEBUG` | `True` locally, `False` in production |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hosts Django will serve |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | The browser-facing origin allowed to make unsafe requests |
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_HOST` / `POSTGRES_PORT` | Database connection |
| `EMAIL_HOST` / `EMAIL_PORT` / `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` / `EMAIL_USE_TLS` | SMTP connection — see below |
| `DEFAULT_FROM_EMAIL` | Sender address on outbound mail |
| `FRONTEND_BASE_URL` | Used to build the tracking link embedded in emails |
| `TICKET_TOKEN_TTL_DAYS` | Tracking token lifetime (default 90) |
| `ATTACHMENT_MAX_BYTES` / `ATTACHMENT_MAX_COUNT` | Per-ticket attachment limits |

Frontend (`.env.local`, `frontend/`):

| Key | Purpose |
|---|---|
| `BACKEND_ORIGIN` | Where the server-side `/api/*` rewrite and Server Components reach Django — `http://localhost:8000` locally, `http://backend:8000` in Docker |

### Email: Mailpit (development) vs. Gmail SMTP (production)

One SMTP code path everywhere — only the environment variable *values*
change:

- **Development:** point at the Mailpit container so tracking links are
  visible and clickable without a real mailbox:
  ```
  EMAIL_HOST=localhost
  EMAIL_PORT=1025
  EMAIL_HOST_USER=
  EMAIL_HOST_PASSWORD=
  EMAIL_USE_TLS=False
  ```
  View sent mail at the Mailpit UI, http://localhost:8025.

- **Production:** Gmail SMTP with a Google App Password (never the account's
  real login password):
  ```
  EMAIL_HOST=smtp.gmail.com
  EMAIL_PORT=587
  EMAIL_HOST_USER=<sending Gmail address>
  EMAIL_HOST_PASSWORD=<16-character Google App Password>
  EMAIL_USE_TLS=True
  ```
  `DEFAULT_FROM_EMAIL` must match `EMAIL_HOST_USER` — Gmail's SMTP relay
  rejects or rewrites a `From` address that isn't the authenticated mailbox
  (or a verified alias on it). An App Password requires 2-Step Verification
  to be enabled on the Google account first (Google Account → Security → App
  passwords).

A mail failure is always logged as an `EMAIL_FAILED` event and never fails
ticket creation, regardless of which provider is configured.

## Database Setup / Migrations

```bash
docker compose up -d db
cd backend
python manage.py migrate                        # apply all migrations
python manage.py makemigrations --check --dry-run   # confirm no model drift
```

PostgreSQL is required — the schema relies on real database-level
`CheckConstraint`s (status/priority/category values, resolution consistency,
token expiry), which SQLite does not enforce the same way. Tests also run
against real PostgreSQL for this reason.

## Creating a Django Superuser

```bash
cd backend
python manage.py createsuperuser
```

A superuser is automatically `is_staff`, which is the only requirement to log
in to the product's own admin dashboard at `/admin/login`. (Django's built-in
`/admin/` site is also present on the backend for direct database inspection,
but it is not the product's admin UI — the Next.js `/admin` routes are.)

## Running the Backend

```bash
cd backend
source .venv/bin/activate
python manage.py runserver
```

Serves the API at http://localhost:8000. Requires Postgres (`docker compose
up -d db`) and, for email to be visible locally, Mailpit (`docker compose up
-d mailpit`).

## Running the Frontend

```bash
cd frontend
npm run dev     # development server, http://localhost:3000
npm run build   # production build
npm run start   # serve the production build
```

## Testing

### Backend — pytest

```bash
cd backend
pytest
coverage run -m pytest && coverage report
```

**Current verified results:** 121 tests passing, 93% statement coverage on
the `tickets` app.

### Frontend — Jest, lint, build

```bash
cd frontend
npm test              # Jest + React Testing Library
npm test -- --coverage
npm run lint           # ESLint
npm run build          # production build
```

**Current verified results:** 38 tests passing across 7 suites, ESLint
clean, production build clean. Statement coverage is 56.6% — component
coverage is strong (~80%), but `lib/api.ts` and `lib/format.ts` bring the
overall figure below the project's 70% target. See
[Known Limitations](#known-limitations).

### End-to-end — Playwright

```bash
docker compose up -d db mailpit
cd backend && python manage.py runserver &      # separate terminal
cd frontend
npx playwright install chromium    # once
npm run test:e2e
```

The suite runs against the real stack (Next.js, Django, PostgreSQL, Mailpit)
with no mocks, seeding its own fixtures (`manage.py seed_e2e`) and clearing
Mailpit before each run. It is written serially (one worker) because it
exercises real per-endpoint throttles (5 ticket submissions/hour, 3
resend-link requests/hour) — running the full suite more than twice against
the same backend process within an hour will trip those throttles; restart
the backend to reset (the throttle cache is in-memory and per-process).

**Current verified results:** 5/5 specs passing (the main
customer-admin-journey spec plus form-validation and public-resend-link)
against a freshly restarted backend.

### API — Postman

The collection under `docs/postman/` exercises all three trust planes,
including edge cases: invalid email, oversized/disallowed attachments,
invalid/expired/revoked tokens, missing CSRF, unauthorized admin access, and
a real throttle trip. Import both files into Postman and run the collection
against a locally running backend (`http://localhost:8000`), or via the CLI:

```bash
npx newman run docs/postman/ticket-system.postman_collection.json \
  -e docs/postman/ticket-system.postman_environment.json
```

**Current verified results:** all 40 requests execute successfully against a
freshly restarted backend, with 39/40 test-scripts passing. The one failing
script covers two attachment-upload requests whose large local fixture file
is referenced by an absolute path saved inside the collection (a Postman-file-picker
convention); this resolves correctly inside the Postman GUI but not always
under a CLI runner on a different machine. The underlying API behavior it
is testing was independently verified directly (a >5MB upload is correctly
rejected with `400 validation_error`) — this is a collection-portability
detail, not an API defect.

## Docker Production Deployment

Full design and rationale: `docs/DEPLOYMENT.md`.

Production runs four containers via `docker-compose.prod.yml`: nginx (the
only container exposed to the host), the Next.js frontend (standalone
build), the Django/Gunicorn backend, and PostgreSQL — plus named volumes for
the database, attachments, static files, and logs. Mailpit is not present in
production; email goes through Gmail SMTP.

```bash
# On the target host, one time:
mkdir -p /opt/ticket-system   # holds the real .env — never committed
vim /opt/ticket-system/.env   # fill in real secrets (see Environment Variables above)

# Build and start
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
```

The backend container runs `migrate` and `collectstatic` automatically before
starting Gunicorn, so a redeploy is a single `build && up -d`. PostgreSQL,
attachments, static files, and logs all persist across container restarts on
named volumes.

## AWS EC2 Deployment

- A single EC2 instance runs the full production Docker Compose stack —
  there is no managed RDS, no load balancer, no container registry.
- nginx serves the application over plain HTTP on the instance's public IP
  (port 80). There is no domain name or TLS in this deployment.
- Secrets live in a single `.env` file on the instance
  (`/opt/ticket-system/.env`), outside the Git checkout, never committed.
- Deployment is a manual SSH runbook: `git pull`, then
  `docker compose -f docker-compose.prod.yml build` followed by
  `docker compose -f docker-compose.prod.yml up -d` on the instance.
- **Live URL:** http://3.27.252.118

## Security Decisions

- **Customer access is token-based, never JWT and never a login.** A
  cryptographically secure opaque token (`secrets.token_urlsafe(32)`, 256
  bits) is emailed to the customer; only that token — never a sequential or
  numeric ticket ID — grants access to that one ticket.
- **Tracking tokens are hashed, never stored raw.** Only a SHA-256 digest is
  persisted; the presented token is hashed and compared, and a ticket may
  have several live tokens at once (one per issued link) since a hash cannot
  be reversed to rebuild an earlier email's link. Tokens expire after 90 days
  and are individually revocable.
- **Admin access uses Django session authentication with CSRF protection.**
  No JWT on the admin side. Every unsafe admin request requires a valid
  `X-CSRFToken`.
- **Public and customer endpoints stay anonymous regardless of any existing
  admin session.** They explicitly skip session-based authentication, so an
  admin's browser session cookie can never trigger CSRF enforcement on the
  public submission or tracking-link endpoints (a real bug found and fixed
  during this project — see the commit history).
- **Attachments are never served from a public static path.** They are
  served only through a Django view that checks the caller's token (customer
  plane) or staff session (admin plane), with `Content-Disposition:
  attachment` and `X-Content-Type-Options: nosniff`.
- **No secrets or tokens ever reach the logs.** A logging filter
  (`RedactTokenPathFilter`) strips token-shaped path segments from every log
  line; raw and hashed tokens are verified absent from logs after every test
  run.
- **Throttling** on ticket submission (5/hour), token lookups (120/hour), and
  resend-link requests (3/hour) blunts spam and email-enumeration attempts.

## Known Limitations

- **No HTTPS / TLS.** The live deployment serves plain HTTP over the EC2
  instance's public IP. Adding nginx TLS (or swapping to Caddy for automatic
  certificates) once a domain is available requires no application code
  changes — see `docs/DEPLOYMENT.md`.
- **The public IP is not permanent.** No Elastic IP is attached to the EC2
  instance, so the address can change if the instance is stopped and
  restarted. The live URL above may need to be re-shared if that happens.
- **No CI/CD.** Backend pytest, frontend Jest/lint/build, and Playwright are
  all run manually/locally — nothing runs them automatically on push.
- **Frontend statement coverage (56.6%) is below the project's 70% target.**
  Component coverage is strong; `lib/api.ts` and `lib/format.ts` are the main
  gap.
- **The Postman collection's two attachment-upload requests are most
  reliable from the Postman GUI**, not a CLI runner on a different machine,
  due to how Postman serializes local file-upload fields.
- **No database backups or point-in-time recovery.** PostgreSQL runs in a
  single container on a named volume with no backup job.
- **Single EC2 instance, no managed database, no horizontal scaling.**
  Acceptable for this exercise; would need revisiting for real traffic.
- **The optional analytics dashboard was not built** (explicitly deferred
  per the brief).

## Future Improvements

- Attach a domain name and enable HTTPS (nginx + certbot, or swap to Caddy).
- Attach an Elastic IP so the public address is stable.
- Add a CI pipeline (backend pytest, frontend Jest/lint/build, and Playwright
  on every push/PR).
- Raise frontend test coverage to the 70% target, focused on `lib/api.ts` and
  `lib/format.ts`.
- Move attachment storage to S3 via `django-storages` — the codebase already
  isolates this behind `MEDIA_ROOT`/the access-checked download view, so it
  is a settings change, not a rewrite.
- Automated database backups for the production PostgreSQL volume.
- Build the optional analytics dashboard (most common issue categories,
  average resolution time) once/if prioritized.
- Consider managed PostgreSQL (RDS) if traffic or durability requirements
  grow beyond a single EC2 instance.
