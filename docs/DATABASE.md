# Database Design — RBDC Exercise 3 Ticket Management System

**Status:** Step 1 design complete and approved. Not yet implemented.
**Scope:** Schema, relationships, constraints, indexes. Endpoints, serializers, and
permissions are Step 2.
**Precedence:** `docs/RBDC_Ex_3.pdf` > `CLAUDE.md` > `docs/ARCHITECTURE.md` > this document.

---

## 1. Purpose

This schema backs the Step 0 architecture: three trust planes, hashed multi-token
customer access, a structured (non-JSON-only) ticket history, and attachments served
through access checks rather than a public path.

The brief requires `Client`, `Ticket`, and `Response`, and asks for "a schema that
ensures data integrity and supports queries for ticket history and client lookups" —
so constraints and indexes are part of the deliverable, not polish.

**Clients are never Django users.** No password, no login row. That is the entire
point of the brief's identification model.

---

## 2. Approved Decisions

Settled during Step 1 planning:

| # | Decision |
|---|---|
| 1 | `Ticket` has a **required `subject`** (max 200) alongside `description`, so the admin list and notification emails are readable without truncating body text. A documented widening beyond the brief's literal field list. |
| 2 | The reporter's name **snapshots onto each Ticket** as `reporter_name`. `Client` is an email identity only, so a returning customer typing their name differently never rewrites an older ticket. |
| 3 | `Response.is_internal` — admin-only notes. Makes the customer/admin boundary explicit and directly testable. |
| 4 | **Django's default `auth.User`**; admin access is `is_staff`. No custom user model — customers are not users, and `is_staff` covers the whole requirement. |
| 5 | `Ticket.reference` — a public display code, `TKT-XXXXXXXX` (8 random base32 chars, unique). **Display only, never authentication.** Exists so a sequential PK is never shown and ticket volume never leaks. |
| 6 | **Three statuses only** — `OPEN`, `IN_PROGRESS`, `RESOLVED`. No `CLOSED`; the brief names exactly these three. |
| 7 | `Ticket.resolved_at` denormalized — set on transition into `RESOLVED`, cleared on reopen. Derivable from history, but makes average-resolution-time queries trivial for the optional analytics feature. |
| 8 | History model named **`TicketEvent`**, with structured `old_value`/`new_value` columns so status and priority changes record uniformly. |
| 9 | Customer-visible event filtering by **code whitelist**, not a database column — one constant, one source of truth. |
| 10 | **Database-level `CheckConstraint`s** for status/priority values, resolution consistency, and token expiry — not just Django validators. Directly serves the brief's data-integrity requirement. |
| 11 | **Single Django app, `tickets`**, holding all six models. Cohesive at this size, avoids circular imports. |
| 12 | **No `factory_boy`** — plain pytest fixtures, to avoid dependency creep. |

---

## 3. Models

### Client
| Field | Type | Notes |
|---|---|---|
| `id` | BigAuto | |
| `email` | EmailField | **unique**, normalized to lowercase on save |
| `created_at` | DateTime | auto |

Thin by design — identity only. Enables the brief's "client lookups": every ticket
ever filed from one address.

### Ticket
| Field | Type | Notes |
|---|---|---|
| `id` | BigAuto | internal only, never exposed as identity |
| `reference` | Char(16) | **unique**, `TKT-XXXXXXXX`, display only |
| `client` | FK → Client | `PROTECT` — never orphan tickets |
| `reporter_name` | Char(150) | as submitted |
| `subject` | Char(200) | required |
| `description` | Text | required |
| `status` | Char(20) | choices, default `OPEN` |
| `priority` | Char(10) | choices, default `MEDIUM` |
| `created_at` / `updated_at` | DateTime | auto |
| `resolved_at` | DateTime | nullable |

### TicketAccessToken
Implements Step 0 Decision 1 — multiple live tokens per ticket, because a hash cannot
be reversed to rebuild a tracking link for a later notification email.

| Field | Type | Notes |
|---|---|---|
| `ticket` | FK → Ticket | `CASCADE`, `related_name="access_tokens"` |
| `token_hash` | Char(64) | **unique**, SHA-256 hex — the customer-plane lookup key |
| `issued_for` | Char(20) | `initial` / `status_update` / `resend` — debugging aid |
| `created_at` | DateTime | auto |
| `expires_at` | DateTime | created + 90 days |
| `revoked_at` | DateTime | nullable |
| `last_used_at` | DateTime | nullable |

Exposes `is_valid` — not revoked, not expired. The raw token exists only in memory at
creation, long enough to build the email link. `__str__` and `__repr__` must never
include the hash or anything token-derived.

### Response
| Field | Type | Notes |
|---|---|---|
| `ticket` | FK → Ticket | `CASCADE`, `related_name="responses"` |
| `author` | FK → auth.User | `SET_NULL`, nullable — keep the response if staff is deleted |
| `message` | Text | required |
| `is_internal` | Boolean | default `False` |
| `created_at` / `updated_at` | DateTime | auto |

Customer plane filters `is_internal=False`. Admin plane sees all.

### TicketEvent
| Field | Type | Notes |
|---|---|---|
| `ticket` | FK → Ticket | `CASCADE`, `related_name="events"` |
| `event_type` | Char(30) | see below |
| `actor` | FK → auth.User | `SET_NULL`, nullable |
| `actor_type` | Char(10) | `system` / `customer` / `admin` — meaningful when actor is null |
| `old_value` / `new_value` | Char(50) | nullable; used by status and priority changes |
| `note` | Char(255) | nullable |
| `metadata` | JSON | nullable, small extras only |
| `created_at` | DateTime | auto |

**Event types:** `CREATED`, `STATUS_CHANGED`, `PRIORITY_CHANGED`, `RESPONSE_ADDED`,
`ATTACHMENT_ADDED`, `TOKEN_ISSUED`, `TOKEN_REVOKED`, `EMAIL_SENT`, `EMAIL_FAILED`.

**Customer-visible subset:** `CREATED`, `STATUS_CHANGED`, `RESPONSE_ADDED`. The rest
are operational.

`metadata` is a convenience column beside the structured fields — it is *not* the
history mechanism, per CLAUDE.md — and **must never hold a raw or hashed token**.

### Attachment
| Field | Type | Notes |
|---|---|---|
| `ticket` | FK → Ticket | `CASCADE`, `related_name="attachments"` |
| `file` | FileField | randomized path, never guessable |
| `original_filename` | Char(255) | preserved for display, sanitized on serve |
| `content_type` | Char(100) | recorded at upload |
| `size_bytes` | PositiveBigInt | recorded at upload |
| `created_at` | DateTime | auto |

Multiple per ticket — the brief says "attachments". Upload path
`attachments/<random>/<random>-<safe-name>`, so the volume is not enumerable even if
it were ever misconfigured as static. Type and size *limits* are enforced in Step 2;
Step 1 guarantees only the columns to record and verify them.

---

## 4. Relationships

```
Client 1──* Ticket
Ticket 1──* TicketAccessToken
Ticket 1──* Response
Ticket 1──* TicketEvent
Ticket 1──* Attachment

auth.User(is_staff) 1──* Response     (author, SET_NULL)
auth.User(is_staff) 1──* TicketEvent  (actor,  SET_NULL)
```

**Deletion policy:** `Client → Ticket` is `PROTECT`; every Ticket child is `CASCADE`;
every staff reference is `SET_NULL` so audit rows survive staff removal.

---

## 5. Constraints

- `Client.email` unique; lowercase normalization in `save()`.
- `Ticket.reference` unique.
- `TicketAccessToken.token_hash` unique.
- Check: `status` in the three allowed values.
- Check: `priority` in the three allowed values.
- Check: `resolved_at IS NOT NULL` **iff** `status = 'RESOLVED'`.
- Check: `expires_at > created_at` on tokens.
- Check: `size_bytes > 0` on attachments.

---

## 6. Indexes

Each index is justified by a query the application actually runs.

| Index | Serves |
|---|---|
| `token_hash` (unique) | every customer-plane request — the hot path |
| `Client.email` (unique) | get-or-create on submission; client lookup |
| `Ticket.reference` (unique) | reference lookup from emails |
| `Ticket (status, -created_at)` | admin dashboard default listing |
| `Ticket.priority` | admin filtering |
| `TicketEvent (ticket, created_at)` | history timeline |
| `Response (ticket, created_at)` | conversation thread |
| Foreign keys | indexed automatically by Django |

Deliberately **not** indexed: `Ticket.created_at` alone (covered by the composite) and
`TicketEvent.event_type` (low cardinality, always queried alongside `ticket`).

---

## 7. Files to Create

```
backend/
├── manage.py
├── requirements.txt              # django, djangorestframework, psycopg, pytest-django, coverage
├── config/settings.py            # env-driven, single file (Step 0 decision)
└── tickets/
    ├── models.py                 # the six models
    ├── constants.py              # status/priority/event-type choices, customer-visible whitelist
    ├── migrations/0001_initial.py
    ├── admin.py                  # Django admin registration for manual QA
    ├── management/commands/seed_demo.py
    └── tests/
        ├── conftest.py
        ├── test_client.py
        ├── test_ticket.py
        ├── test_access_token.py
        ├── test_response.py
        ├── test_event.py
        └── test_attachment.py
```

PostgreSQL and the `logs/` + `media/` volumes come up via a minimal
`docker-compose.yml` so Step 1 runs against real PostgreSQL, not SQLite — check
constraints and unique-index behaviour must be verified on the actual target engine.
The full Compose setup remains Step 5.

---

## 8. Verification

Step 1 is not complete until all of the following pass:

1. `docker compose up -d db` then `python manage.py migrate` — clean apply.
2. `python manage.py makemigrations --check --dry-run` — exits 0, no model drift.
3. `pytest` green, covering:
   - email normalization and uniqueness collision
   - token hashing round-trip; `is_valid` false when expired, false when revoked
   - two live tokens on one ticket both validate (Step 0 Decision 1, tested)
   - status and priority check constraints reject bad values at the database level
   - the `resolved_at` constraint rejects inconsistent combinations
   - `PROTECT` blocks deleting a Client with tickets; `CASCADE` clears children
   - `SET_NULL` keeps a Response after its author is deleted
4. `coverage report` on `tickets/models.py` — baseline recorded toward the 70% target.
5. `psql \d+` inspection confirming indexes and constraints exist as designed.
6. Grep check: no test output or `__str__` implementation exposing a raw token.

---

## 9. Out of Scope for Step 1

Endpoints, serializers, permissions, throttling, the email layer, attachment
type/size enforcement, and whether the optional analytics dashboard is built at all.
