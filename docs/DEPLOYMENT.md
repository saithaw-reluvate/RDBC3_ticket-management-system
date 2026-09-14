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
through AWS SES instead of Mailpit.

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
| 8 | **Production email: AWS SES SMTP, same `django.core.mail.backends.smtp.EmailBackend` code path.** | No code change — only new env var *values* (SES SMTP endpoint/port/IAM-generated username-password, `EMAIL_USE_TLS=True`). Per `ARCHITECTURE.md` Decision 4, approved fallback if SES sandbox blocks the deadline is Gmail SMTP with an app password — same env vars, different values. |
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
Mailpit is NOT present in production — SES SMTP replaces it entirely.
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
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | The EC2 instance's public IP |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `http://localhost:3000` | `http://<EC2_PUBLIC_IP>` |
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` | dev defaults | Real values, generated once, stored only in the EC2 `.env` |
| `POSTGRES_HOST` | `localhost` | `db` (the Compose service name) |
| `POSTGRES_PORT` | `5432` | `5432` |
| `EMAIL_HOST` | `localhost` (Mailpit) | SES SMTP endpoint, e.g. `email-smtp.<region>.amazonaws.com` |
| `EMAIL_PORT` | `1025` | `587` |
| `EMAIL_HOST_USER` | empty | SES SMTP IAM-generated username |
| `EMAIL_HOST_PASSWORD` | empty | SES SMTP IAM-generated password |
| `EMAIL_USE_TLS` | `False` | `True` |
| `DEFAULT_FROM_EMAIL` | `support@example.com` | A real address verified in SES (required while SES is sandboxed) |
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

### AWS SES setup (informational, not a code/settings change)

SES itself is provisioned outside the repo: verify the sending domain or address,
request production access to leave the sandbox (or use the already-approved Gmail
SMTP fallback if that request doesn't clear in time), and generate SMTP-specific IAM
credentials (these are distinct from AWS access keys — SES issues a separate
username/password pair for SMTP AUTH). Only the resulting SMTP endpoint, port,
username, and password land in the EC2 `.env`; nothing else in the stack talks to any
AWS API.

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
   the email arrives via SES (or the Gmail fallback), confirm the admin dashboard
   loads and the tracking link works.

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
2. The full customer journey (submit → SES email → tracking link → status view) and
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
