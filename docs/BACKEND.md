# Backend Design — RBDC Exercise 3 Ticket Management System

**Status:** Step 2 design complete and approved. Not yet implemented.
**Scope:** API surface, service layer, authentication, validation, email, logging,
and Postman coverage. Frontend work is Step 3.
**Precedence:** `docs/RBDC_Ex_3.pdf` > `CLAUDE.md` > `docs/ARCHITECTURE.md` >
`docs/DATABASE.md` > this document.

---

## 1. Purpose

Turn the Step 1 schema into the API described in `ARCHITECTURE.md` §2: three trust
planes, token-based customer access, session-authenticated admin management, email
notification, and protected attachment serving.

Step 2 is complete only when every endpoint has been exercised through Postman,
**before** any frontend integration begins.

---

## 2. Approved Decisions

| # | Decision | Rationale |
|---|---|---|
| 1 | **The submit response returns `reference` only — never the tracking link.** The link arrives by email. | The email *is* the feature the brief is built on. One delivery path means no "works in dev, untested in prod" gap. Mailpit keeps it testable. |
| 2 | **Self-service resend endpoint.** `POST /api/tickets/resend-link/`, constant response regardless of whether the address is known, throttled 3/hour. | Solves the lost-email dead end created by Decision 1. Falls out of the multi-token design at no conceptual cost. The constant response prevents email enumeration. |
| 3 | **Attachments: 5 files per ticket, 5 MB each.** Allowed: `png jpg jpeg gif webp pdf txt log csv`. Validate extension + declared content-type. | Covers real incident evidence — screenshots and logs. **SVG is excluded** as a scriptable XSS vector; archives excluded. No magic-byte sniffing, so no `python-magic` system dependency. |
| 4 | **Distinguish token failures:** `404 invalid_token`, `410 expired_token`, `410 revoked_token`. | Lets the UI say "this link expired — request a new one" and point at Decision 2. Against 256-bit tokens an attacker never holds one to test, so there is no meaningful existence leak. |

Decisions 1 and 2 are a pair. Decision 1 is only acceptable because Decision 2 ships
alongside it.

---

## 3. Settings and Environment

Step 1 creates `config/settings.py` with apps and database. Step 2 extends it with:
DRF configuration, SMTP email, the two file log handlers, throttle scopes,
`MEDIA_ROOT`, and `FRONTEND_BASE_URL`.

New keys for `.env.example`:

```
FRONTEND_BASE_URL=http://localhost:3000     # used to build tracking links
TICKET_TOKEN_TTL_DAYS=90
ATTACHMENT_MAX_BYTES=5242880
ATTACHMENT_MAX_COUNT=5
```

> **Coordination:** `config/settings.py` and `.env.example` are created by the Step 1
> session. Let Step 1 finish them before Step 2 implementation begins, so two
> sessions do not edit the same files.

---

## 4. API Surface

### 4.1 Public plane — anonymous, throttled

**`POST /api/tickets/`** — `multipart/form-data`

Request: `reporter_name`, `email`, `subject`, `category`, `description`,
`attachments[]` (optional)

`category` is **required**. `OTHER` is the escape hatch, so a required field never
blocks a submission. The seven allowed values are enumerated in `docs/DATABASE.md`
§2 Decision 13 — that table is the source of truth.

Response `201`:
```json
{ "reference": "TKT-A7K2M9P4", "subject": "...", "category": "BUG",
  "status": "OPEN", "priority": "MEDIUM", "created_at": "..." }
```

No token, no link — by Decision 1.

Behaviour: normalize email → `get_or_create` Client → create Ticket → validate and
store attachments → record `CREATED` (and `ATTACHMENT_ADDED` per file) → issue a token
with `issued_for="initial"` → send the creation email.

**`POST /api/tickets/resend-link/`**

Request: `{"email": "..."}`

Response `202`, always identical whether or not the address is known:
```json
{ "message": "If that address has tickets, a tracking link has been sent." }
```

Issues a fresh token (`issued_for="resend"`) for each of the client's non-expired
tickets and emails them.

### 4.2 Customer plane — opaque token in URL, read-only

**`GET /api/track/<token>/`** — one composite response, so a page load costs one
token resolution:

```json
{ "reference": "...", "subject": "...", "description": "...",
  "reporter_name": "...", "category": "BUG", "category_display": "Something is broken",
  "status": "IN_PROGRESS", "priority": "HIGH",
  "created_at": "...", "resolved_at": null,
  "responses":   [ { "message": "...", "created_at": "..." } ],
  "events":      [ { "event_type": "STATUS_CHANGED", "old_value": "OPEN",
                     "new_value": "IN_PROGRESS", "created_at": "..." } ],
  "attachments": [ { "id": 1, "original_filename": "screenshot.png",
                     "size_bytes": 20481, "content_type": "image/png" } ] }
```

Filtering is mandatory, not optional:
- `responses` → `is_internal=False` only
- `events` → whitelist only (`CREATED`, `STATUS_CHANGED`, `RESPONSE_ADDED`)
- Response `author` is **not** exposed to customers

**`GET /api/track/<token>/attachments/<id>/`** — download, 404 if the attachment does
not belong to the token's ticket.

### 4.3 Admin plane — Django session + CSRF

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/admin/auth/login/` | Session login |
| `POST` | `/api/admin/auth/logout/` | End session |
| `GET` | `/api/admin/auth/me/` | Current user; `@ensure_csrf_cookie` so the SPA receives `csrftoken` on boot |
| `GET` | `/api/admin/tickets/` | List — filter `status`, `priority`, `category`; `search`; `ordering`; paginated |
| `GET` | `/api/admin/tickets/<reference>/` | Detail — **all** responses including internal, **all** events |
| `PATCH` | `/api/admin/tickets/<reference>/` | Update `status`, `priority`, and/or `category` |
| `POST` | `/api/admin/tickets/<reference>/responses/` | Add response (`message`, `is_internal`) |
| `POST` | `/api/admin/tickets/<reference>/resend-link/` | Mint a new token and email it |
| `POST` | `/api/admin/tickets/<reference>/revoke-links/` | Revoke all active tokens |
| `GET` | `/api/admin/tickets/<reference>/attachments/<id>/` | Download |

Admin routes key on `reference`, never the primary key — sequential IDs are never
exposed anywhere in the system.

Permission on every admin route: authenticated **and** `is_staff`.

---

## 5. Service Layer

Views stay thin. All business logic lives in `tickets/services/`.

| Module | Responsibility |
|---|---|
| `tokens.py` | `issue_token(ticket, issued_for) → (raw, obj)`; `resolve_token(raw)`; `revoke_active_tokens(ticket)` |
| `events.py` | `record(ticket, event_type, actor=None, actor_type=..., old=None, new=None, note=None, metadata=None)` — the single writer of history |
| `emails.py` | `send_ticket_created`, `send_status_changed`, `send_response_added`, `send_link_resend` |
| `tickets.py` | `create_ticket(...)`, `update_ticket(...)` — orchestrates model write + event + email |
| `attachments.py` | Validation and storage |

**History is recorded by explicit service calls, never Django signals.** Signals hide
control flow and make "why did this event appear?" hard to answer in a test. Because
every state change routes through `services/tickets.py`, history cannot be silently
forgotten.

**Every email that needs a link mints its own fresh token.** This is where the Step 0
multi-token decision pays off.

**Email sending is wrapped.** A failure logs via `logger.exception()` and records an
`EMAIL_FAILED` event, but never fails the request — per CLAUDE.md.

`resolve_token` is the single entry point for the customer plane: hash the presented
value, look up by `token_hash`, check validity, update `last_used_at`, return the
ticket. It must never log, return, or embed the raw token.

---

## 6. Error Envelope

One DRF exception handler, one shape everywhere:

```json
{ "error": { "code": "validation_error", "message": "...", "details": {} } }
```

| Code | HTTP | When |
|---|---|---|
| `validation_error` | 400 | Field validation failed; `details` carries per-field messages |
| `invalid_token` | 404 | No token matches the presented value |
| `expired_token` | 410 | Token found, past `expires_at` |
| `revoked_token` | 410 | Token found, `revoked_at` set |
| `not_found` | 404 | Ticket or attachment not found |
| `permission_denied` | 403 | Not authenticated, or not `is_staff` |
| `throttled` | 429 | Rate limit exceeded |
| `server_error` | 500 | Unhandled — generic message only |

Stack traces never cross the API boundary.

---

## 7. Throttling

| Scope | Rate | Purpose |
|---|---|---|
| `ticket_create` | 5/hour/IP | Spam submissions |
| `token_lookup` | 120/hour/IP | Generous for refreshes, blunts scanning |
| `resend_link` | 3/hour/IP | Limits email-enumeration attempts |

Admin routes use DRF's default authenticated rate.

---

## 8. Logging

Mapped to the CLAUDE.md event list. Log lines reference `ticket.reference` or the
internal ID — **never a token, raw or hashed**.

| Level | Events |
|---|---|
| `info` | Ticket created; status changed; priority changed; category changed; response added; token issued; token revoked; email sent |
| `warning` | Attachment rejected (type/size/count); token lookup failed; throttle exceeded |
| `error` | Email send failed |
| `exception` | Any unhandled exception reaching the DRF handler |

---

## 9. Attachment Handling

- Max 5 per ticket, 5 MB each (env-configurable).
- Allowed extensions: `png jpg jpeg gif webp pdf txt log csv`.
- Validate extension **and** declared content-type; reject on mismatch.
- Store at `attachments/<random>/<random>-<safe-name>` — never a guessable path.
- Serve **only** through the access-checked view, with:
  - `Content-Disposition: attachment`
  - `X-Content-Type-Options: nosniff`

Forced download plus `nosniff` is the real mitigation against a malicious upload —
more so than type validation, which is why magic-byte sniffing does not earn its
dependency here.

---

## 10. Proposed Defaults

- **No `django-filter`.** DRF's `SearchFilter` / `OrderingFilter` plus explicit
  queryset filtering covers status, priority, and search.
- Pagination: `PageNumberPagination`, 20 per page.
- Analytics endpoints are **out of scope** for Step 2 — optional feature, only after
  all mandatory work is complete.

---

## 11. Files to Create

```
backend/
├── config/
│   ├── settings.py               # extended: DRF, email, logging, throttles, media
│   └── urls.py                   # /api/ roots for the three planes
└── tickets/
    ├── serializers.py
    ├── permissions.py            # IsStaffUser
    ├── throttles.py              # the three scopes
    ├── exceptions.py             # handler + error envelope
    ├── services/
    │   ├── tokens.py
    │   ├── events.py
    │   ├── emails.py
    │   ├── tickets.py
    │   └── attachments.py
    ├── templates/email/           # creation, status change, response added, resend
    ├── views/
    │   ├── public.py
    │   ├── customer.py
    │   └── admin.py
    └── tests/
        ├── test_public_api.py
        ├── test_customer_api.py
        ├── test_admin_api.py
        └── test_services.py

docs/postman/
├── ticket-system.postman_collection.json
└── ticket-system.postman_environment.json
```

---

## 12. Testing

Per-plane test modules plus service tests. The assertions that encode the trust
boundaries and must exist:

- Customer plane never returns a response with `is_internal=True`
- Customer plane never returns an operational event type
- A token for ticket A cannot read ticket B
- Expired tokens rejected; revoked tokens rejected; both distinctly from invalid
- Unauthenticated admin routes return `403`, never `404`-with-data
- Attachment download rejects an ID belonging to another ticket
- Oversized, over-count, and disallowed-type attachments all rejected
- Resend-link returns an identical response for known and unknown addresses
- **No raw token appears in any emitted log record**

### Postman

`docs/postman/`, folders per plane, environment capturing `reference` and a live
token. Must include edge cases, not just happy paths: invalid email, oversized
attachment, invalid/expired/revoked token, missing CSRF, unauthorized admin access,
and a throttle trip.

---

## 13. Verification

Step 2 is not complete until:

1. `pytest` green, with the §12 assertions present.
2. `coverage report` recorded, tracking toward the 70% target.
3. Full Postman collection run passes, edge cases included.
4. Mailpit shows every notification type, each containing a working tracking link.
5. A link from a Mailpit email opens the ticket successfully via the customer plane.
6. `grep` over `logs/` after a full run finds no token-like string.

---

## 14. Git Branches

```
feature/ticket-creation          # public submit + attachments
feature/client-identification    # token service, customer plane, resend
feature/admin-management         # admin auth, list/detail, updates, responses
```

---

## 15. Out of Scope for Step 2

Frontend pages and components, the analytics dashboard, Docker packaging of the
backend service, and AWS deployment.
