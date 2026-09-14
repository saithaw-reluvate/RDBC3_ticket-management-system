# Deployment Design — RBDC Exercise 3 Ticket Management System

**Status:** Step 5 design complete and approved. Not yet implemented.
**Scope:** Production Docker Compose topology, reverse proxy, environment variables,
secrets handling, static/media file strategy, and the manual EC2 deploy runbook.
Dockerfiles, `docker-compose.prod.yml`, and the actual EC2 deploy are the
implementation that follows approval of this document.
**Precedence:** `docs/RBDC_Ex_3.pdf` > `CLAUDE.md` > `docs/ARCHITECTURE.md` >
`docs/DATABASE.md` > `docs/BACKEND.md` > `docs/FRONTEND.md` > `docs/INTEGRATION.md` >
this document.

---

## 1. Purpose

Turn the existing dev-only `docker-compose.yml` (Postgres + Mailpit, application code
run outside containers) into a production stack for the existing AWS EC2 instance:
containerized Next.js frontend, containerized Django/Gunicorn backend, containerized
PostgreSQL, a reverse proxy, and persistent volumes — with production email routed
through Gmail SMTP instead of Mailpit.

Step 5 is complete only when `docker compose -f docker-compose.prod.yml up -d` on the
EC2 instance serves the full application over its public IP and every flow verified
in Step 4 still works end to end against the containerized stack.

---

## 2. Approved Decisions

| # | Decision | Rationale |
|---|---|---|
| 1 | **Bare EC2 public IP, HTTP only. No domain, no TLS in this pass.** | Matches the brief's "live AWS URL" deliverable with zero extra setup. `ARCHITECTURE.md` Decision 3 already reserves adding nginx/Caddy + a domain + HTTPS later without touching application code, so this is not a dead end. |
| 2 | **nginx as the reverse proxy.** | No domain means no automatic-TLS benefit from Caddy. nginx is the more ubiquitous choice and all it needs to do here is proxy to the frontend container and serve `/static/` from a shared volume. |
| 3 | **nginx has exactly one proxied upstream: the frontend container.** | The Next.js `/api/*` rewrite (`BACKEND_ORIGIN`) already proxies API calls to the backend server-side, container-to-container — that mechanism does not change in production. nginx does not need its own `/api/` routing rule; it forwards everything except `/static/` to `frontend:3000`. |
| 4 | **Static files: `collectstatic` into a shared named volume; nginx serves `/static/` directly from it.** | Covers Django's built-in `/admin/` site and DRF's default `BrowsableAPIRenderer`, both of which need CSS/JS to render. No new Python dependency (rejected: `whitenoise`) — nginx already exists and doing this is one `location` block. |
| 5 | **Attachments remain served only through the Django access-checked view — nginx never gets a `/media/` location block.** | Unchanged from `CLAUDE.md`/Decision 5 in `ARCHITECTURE.md`: attachments must never be reachable from a public static path. This is a hard constraint carried into Step 5, not a new decision. |
| 6 | **Secrets: a plain `.env` file at `/opt/ticket-system/.env` on the EC2 host (never committed), referenced by an explicit absolute path in `docker-compose.prod.yml`'s `env_file:`.** | Identical mechanism to development (`settings.py` already reads env vars the same way either source). No new AWS service, no IAM role to provision — matches "no unnecessary infrastructure." The path is absolute and explicit, not a bare `env_file: .env`, because the file lives outside the repository working copy on purpose (§5). |
| 7 | **Deploy via manual SSH runbook: `git pull` + `docker compose -f docker-compose.prod.yml build && up -d` on the instance itself.** | Matches `ARCHITECTURE.md` §7's single-instance scope exactly. No registry, no CI pipeline — appropriately sized for this exercise. Documented as a runbook in the README per `CLAUDE.md`'s Step 5/6 requirements. |
| 8 | **Production email: Gmail SMTP, same `django.core.mail.backends.smtp.EmailBackend` code path.** | No code change — only new env var *values* (`smtp.gmail.com`, port `587`, a Gmail address as the SMTP username, a Google App Password as the SMTP password, `EMAIL_USE_TLS=True`). Supersedes the originally planned AWS SES (`ARCHITECTURE.md` Decision 4) — this was already the project's pre-approved fallback, and switching to it removes the AWS account/sandbox dependency entirely. |
| 9 | **Postgres, media, and logs each get their own named Docker volume; Postgres is not exposed on a host port in production.** | `pgdata` already exists in dev for exactly this reason (§ current `docker-compose.yml`). Media and logs need the same durability across container recreation. Postgres has no reason to be reachable from outside the Docker network in production, unlike dev where a host tool might want to connect directly. |
| 10 | **Migrations and `collectstatic` run automatically via a backend container entrypoint script, before Gunicorn starts.** | Keeps the deploy runbook to one command. Low risk at this project's size and matches "verify then serve" — not a separate manual step to forget. |

---

## 3. Container Topology

Three containers reachable from the host network, one internal-only.

```
Browser (EC2 public IP, port 80)
   │
   ▼
┌─────────────────────────────┐
│ nginx                       │  :80 (published)
│  - / , /_next/*, everything │──────────┐
│    else → frontend:3000     │          │
│  - /static/* → shared       │          │
│    staticfiles volume       │          ▼
└─────────────────────────────┘  ┌──────────────────────────┐
                                  │ frontend (Next.js,       │  :3000 (internal)
                                  │ standalone build)        │
                                  │  - /api/* rewrite ────┐  │
                                  └────────────────────────┼──┘
                                                            ▼
                                                  ┌──────────────────────────┐
                                                  │ backend (Django+Gunicorn)│  :8000 (internal)
                                                  │  - migrate + collectstatic│
                                                  │    on start, then serve   │
                                                  └───────────┬──────────────┘
                                                              │
                                                  ┌───────────▼──────────────┐
                                                  │ db (PostgreSQL)          │  internal only
                                                  │  named volume: pgdata    │
                                                  └──────────────────────────┘

Volumes: pgdata, media, logs, staticfiles
Mailpit is NOT present in production — Gmail SMTP replaces it entirely.
```

**nginx is the only service that reaches the host network.** It is the sole service
with a `ports:` mapping (`80:80`). `frontend`, `backend`, and `db` are internal-only
Compose services with no host port mapping at all — reachable exclusively from other
containers on the Compose network, never directly from the host or the public
internet. This is the same trust shape as development where Django is "not publicly
exposed" (`ARCHITECTURE.md` §1) — nginx is simply now what stands in front of the
frontend instead of `next dev` binding directly to the host.

**A note on the public IP:** the EC2 instance's current public IPv4 address is not
guaranteed stable across a stop/start unless an Elastic IP is associated with the
instance. This does not block this exercise's deployment — the "live AWS URL"
deliverable can simply be re-checked/re-shared if the instance is ever stopped and
restarted — but is worth knowing before treating the current IP as permanent (e.g. in
a submitted README link). Attaching an Elastic IP is a console/CLI action outside this
repo, not a change to anything planned here.

---

## 4. Environment Variables

All existing dev keys from `.env.example` carry over unchanged in *name*; only
*values* change for production. New keys are marked **(new)**.

### Backend

| Key | Dev value | Production value |
|---|---|---|
| `DJANGO_SECRET_KEY` | dev placeholder | Real random secret, generated once, stored only in the EC2 `.env` |
| `DJANGO_DEBUG` | `True` | `False` |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | `backend` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `http://localhost:3000` | `http://<EC2_PUBLIC_IP>` |
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` | dev defaults | Real values, generated once, stored only in the EC2 `.env` |
| `POSTGRES_HOST` | `localhost` | `db` (the Compose service name) |
| `POSTGRES_PORT` | `5432` | `5432` |
| `EMAIL_HOST` | `localhost` (Mailpit) | `smtp.gmail.com` |
| `EMAIL_PORT` | `1025` | `587` |
| `EMAIL_HOST_USER` | empty | The sending Gmail address |
| `EMAIL_HOST_PASSWORD` | empty | A Google App Password (16 characters, generated for this app — never the account's real login password) |
| `EMAIL_USE_TLS` | `False` | `True` |
| `DEFAULT_FROM_EMAIL` | `support@example.com` | The same Gmail address as `EMAIL_HOST_USER` — see note below |
| `FRONTEND_BASE_URL` | `http://localhost:3000` | `http://<EC2_PUBLIC_IP>` |
| `TICKET_TOKEN_TTL_DAYS` | `90` | `90` (unchanged) |
| `ATTACHMENT_MAX_BYTES` / `ATTACHMENT_MAX_COUNT` | `5242880` / `5` | unchanged |

### Frontend

| Key | Dev value | Production value |
|---|---|---|
| `BACKEND_ORIGIN` | `http://localhost:8000` | `http://backend:8000` — the Compose service name, per the comment already in `frontend/.env.example` anticipating this exact Step 5 change |

No `NEXT_PUBLIC_*` variables exist or are needed — the frontend never talks to the
backend from browser JavaScript using an absolute URL; it always goes through the
same-origin `/api/*` rewrite or, for Server Components, `BACKEND_ORIGIN` server-side.

> **`DJANGO_ALLOWED_HOSTS` tracks the internal destination, not the public
> address.** Django is only ever reached via the frontend's server-side `/api/*`
> proxy call, so the `Host` header it sees is always the proxy's destination —
> `backend:8000` — regardless of what the browser's original request targeted.
> `DJANGO_CSRF_TRUSTED_ORIGINS` is the opposite: the browser's `Origin` header is
> forwarded through unchanged by the proxy, so that one *does* need the
> public-facing address. Verified against a real `DisallowedHost` 400 hit during
> local testing of this plan before either was understood correctly.

> **Build-time, not just runtime.** Next.js resolves `next.config.mjs`'s
> `rewrites()` destination once at `next build` and bakes it into the standalone
> output's routes manifest — it is not re-read from `process.env` when the
> container starts. `BACKEND_ORIGIN` must therefore be passed as a Docker build
> ARG for the frontend image (fixed at `http://backend:8000`, matching the
> Compose service name), in addition to being set as a normal runtime
> environment variable for the Server Component code path that reads
> `process.env.BACKEND_ORIGIN` directly. Both are the same value here, so this
> has no operational impact beyond needing an image rebuild — not just a
> restart — if the backend's internal address were ever to change.

### Gmail SMTP setup (informational, not a code/settings change)

Gmail itself is provisioned outside the repo: enable 2-Step Verification on the
sending Google account (required before an App Password can be generated), then
generate a 16-character Google App Password scoped to this app (Google Account →
Security → App passwords). Only the Gmail address and the App Password land in the
EC2 `.env`; nothing else in the stack talks to any Google API.

**`DEFAULT_FROM_EMAIL` must match `EMAIL_HOST_USER`.** Gmail's SMTP relay
authenticates the connection as a specific mailbox and will reject or silently
rewrite a `From` address that isn't that mailbox (or a verified "Send mail as" alias
on it) — unlike AWS SES, which allows any verified sender address independent of the
SMTP credentials used. This is the one real behavioural difference the switch
introduces; it does not require a code change since both values are already
independent environment variables.

---

## 5. Secrets on EC2

A single `.env` file is created directly on the EC2 instance at
`/opt/ticket-system/.env`, outside of Git entirely — not even matching a gitignored
path inside the working copy, to remove any risk of an accidental `git add -f`.
`docker-compose.prod.yml` references it by that exact absolute path —
`env_file: /opt/ticket-system/.env` — on the `db` and `backend` services, not a bare
`env_file: .env`, since the file does not live inside (or relative to) the repository
checkout on the instance. It is created once by hand over SSH and updated by hand
when a value changes; nothing automates its contents.

One consequence of the file living outside the Compose project directory: Compose
does not auto-load it for `${VAR}`-style substitution *within* `docker-compose.prod.yml`
itself (that auto-load only happens for a `.env` beside the compose file). Anywhere
the compose file needs a value at the shell level — e.g. the Postgres healthcheck
command — it must reference the variable as `$$VAR` (escaped) so Compose leaves it
for the container's own shell to expand from the `env_file`-provided runtime
environment, rather than trying to substitute it itself at parse time.

This mirrors the existing dev pattern exactly — `.env.example` documents every key
with a dummy value, `settings.py` already reads from the environment however it got
there, and no code path cares whether that env var came from a `.env` file or the
real shell/Compose environment.

---

## 6. Static and Media Files

- **Static** (`/admin/` CSS/JS, DRF's browsable-API assets): the backend image runs
  `collectstatic --noinput` into a `staticfiles` named volume on container start;
  nginx mounts the same volume read-only and serves `/static/` directly from disk.
- **Media** (attachments): unchanged from every prior step. Lives on the `media`
  named volume, mounted only into the `backend` container, and is reachable from the
  outside world exclusively through the existing access-checked Django view. nginx
  has no configuration referencing `/media/` at all — this is a hard boundary, not an
  oversight.

---

## 7. Deploy Runbook (manual SSH)

Documented in full in the README at Step 6; summarized here for the plan record:

1. SSH into the EC2 instance.
2. First time only: create `/opt/ticket-system/.env` from `.env.example` +
   `frontend/.env.example` with real production values (§4); `git clone` the repo.
3. Each deploy: `git pull`, then
   `docker compose -f docker-compose.prod.yml build && docker compose -f docker-compose.prod.yml up -d`.
4. The backend entrypoint runs `manage.py migrate` and `manage.py collectstatic --noinput`
   automatically before Gunicorn starts — no separate manual step.
5. Verify: hit `http://<EC2_PUBLIC_IP>/` in a browser, submit a test ticket, confirm
   the email arrives via Gmail SMTP, confirm the admin dashboard loads and the
   tracking link works.

---

## 8. Files to Create

```
/
├── docker-compose.prod.yml
├── .env.example                  # extended with production-only notes, no new keys
├── nginx/
│   └── nginx.conf                # single upstream (frontend) + /static/ location
├── backend/
│   ├── Dockerfile                # multi-stage, Gunicorn entrypoint
│   └── docker-entrypoint.sh      # migrate → collectstatic → exec gunicorn
└── frontend/
    └── Dockerfile                # multi-stage, Next.js standalone output
```

---

## 9. Verification

Step 5 is not complete until:

1. `docker compose -f docker-compose.prod.yml up -d` brings up all four containers
   healthy (`db` healthcheck passing; `backend` and `frontend` responding).
2. The full customer journey (submit → Gmail SMTP email → tracking link → status view) and
   the full admin journey (login → manage → respond → resend/revoke) work through
   the public EC2 IP, mirroring the Step 4 Playwright journey but against the
   containerized stack.
3. `docker compose -f docker-compose.prod.yml logs backend` shows no raw or hashed
   token in any line (same check as Step 2 §13 / Step 4 §5, re-run here).
4. Restarting the stack (`down` then `up -d`) does not lose ticket data, attachments,
   or logs — proving the volumes are durable across container recreation.
5. `DJANGO_DEBUG=False` confirmed live (a deliberately broken request shows the
   generic `server_error` envelope, never a Django debug traceback page).
6. Static admin assets and the DRF browsable API render with CSS applied, proving
   the nginx `/static/` path works.

---

## 10. Out of Scope for Step 5

A custom domain and HTTPS/TLS termination (deferred per Decision 1 — no application
code changes required to add nginx TLS or swap to Caddy later); CI/CD automation of
the build/deploy steps; AWS Secrets Manager/Parameter Store; database backup/restore
tooling; multi-instance or managed-RDS scaling (`ARCHITECTURE.md` already rules out
RDS); the optional analytics dashboard.

---

## 11. Git Branch

```
feature/docker-deployment       (Step 5 — matches ARCHITECTURE.md §8)
```
