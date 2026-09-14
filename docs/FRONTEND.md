# Frontend Design — RBDC Exercise 3 Ticket Management System

**Status:** Step 3 design complete and approved. Not yet implemented.
**Scope:** Visual system, routes, components, flows, states, accessibility, API
integration, testing, implementation order.
**Precedence:** `docs/RBDC_Ex_3.pdf` > `CLAUDE.md` > `docs/ARCHITECTURE.md` >
`docs/DATABASE.md` > `docs/BACKEND.md` > this document.

**Approved mockups** (the visual source of truth for implementation):
- Incident filing + receipt — https://claude.ai/code/artifact/30ad62dd-e4ef-4661-881b-5f7a35335720
- Ticket record + recovery states — https://claude.ai/code/artifact/91bbd7f4-d9cf-41d5-b617-e44640e00a6f
- Admin queue + workspace — https://claude.ai/code/artifact/8754030e-cde9-4f6d-8ab1-72b6c8fe5f54

---

## 1. Purpose and design problem

Build the three frontend areas the brief requires — Incident Reporting, Ticket Status,
and a restricted Admin Dashboard — on Next.js 14 against the shipped Step 2 API.

Two audiences in opposite states share one identity:

- **The customer** is having a bad day, has no account, and receives nothing back but
  an email. Because Backend Decision 1 keeps the tracking link out of the submit
  response, the confirmation screen carries the entire trust burden.
- **The admin** scans volume and must never accidentally publish an internal note to
  a customer.

The approved direction is **Dispatch** — an editorial *record* identity. The ticket is
a filed document with a reference; the timeline is a ledger. The metaphor matches what
the product actually does, which is what makes an emailed link feel permanent.

---

## 2. Approved visual system

### 2.1 Principles
- **Ledger, not cards.** Structure comes from rules and label/value dockets. No
  rounded corners, no shadows, no card grids.
- **Underlined fields, not boxes.** Form inputs read as a filled-in document.
- **Colour is semantic only.** Never decorative, and status is never carried by colour
  alone — always mark plus label.
- **Typographic transitions.** Status changes render as `Open → In progress` with the
  old value struck through, not as coloured pills.
- Sharp corners throughout. Do not turn this into a rounded-card SaaS dashboard.

### 2.2 Tokens

| Token | Light | Dark |
|---|---|---|
| `--page` | `#FAF8F4` | `#1F1D1A` |
| `--surface` | `#FFFDF9` | `#272420` |
| `--raised` | `#FFFFFF` | `#2F2B26` |
| `--sunk` | `#F1EDE5` | `#1A1816` |
| `--ink` | `#14110E` | `#F2EDE5` |
| `--muted` | `#645D52` | `#B3AA9D` |
| `--faint` | `#8A8276` | `#938A7E` |
| `--rule` | `rgb(20 17 14 / 0.13)` | `rgb(242 237 229 / 0.12)` |
| `--rule-strong` | `rgb(20 17 14 / 0.28)` | `rgb(242 237 229 / 0.26)` |
| `--oxide` (High, error, accent) | `#A1382B` | `#E4917A` |
| `--ochre` (In progress, internal) | `#8F6118` | `#E0B36B` |
| `--moss` (Resolved, success) | `#3F5F3A` | `#93B989` |
| `--internal-bg` (internal-note tint) | `rgb(143 97 24 / 0.07)` | `rgb(224 179 107 / 0.11)` |
| `--sel-bg` (selected queue row) | `rgb(161 56 43 / 0.06)` | `rgb(228 145 122 / 0.10)` |

Surface roles: `--page` is the ground; `--surface` carries rails, top bars and the
composer; `--raised` carries inputs and selects; `--sunk` carries control strips and
wells. Both themes use all four — depth is structural, not decorative.

Theme CSS must follow the three-state pattern: full palette on bare `:root`, then
`@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { … } }`, then
`:root[data-theme="dark"] { … }`.

### 2.3 Typography

**Poppins throughout** — one family, customer and admin. Hierarchy comes from size,
weight and letter-spacing, never from mixing families. Weights: 300, 400, 500, 600, 700.

| Role | Size | Weight | Tracking |
|---|---|---|---|
| Display / page title | `clamp(36px, 7vw, 52px)` | 600 | `-0.025em` |
| Section title (subject) | `clamp(31px, 5.8vw, 43px)` | 600 | `-0.025em` |
| Customer body | 17px / 1.65 | 300 | — |
| Admin body | 15–16px / 1.5 | 300–400 | — |
| Helper text | 14.5px | 300 | — |
| Uppercase label / eyebrow | 12–12.5px | 600 | `0.11–0.16em` |
| **Ticket reference** | 15–19px | **600** | **`0.07–0.08em`** |

Ticket references stay distinctive through weight and tracking — **no second font
family**. Use `font-variant-numeric: tabular-nums` wherever digits align in columns.

Admin screens may be denser than customer screens, but body text must not drop below
~15px, and helper text not below ~13px.

### 2.4 Motion
150–250ms ease-out. Staggered 40ms fade-up on section entry. The submit **seal** is
the single larger gesture. `prefers-reduced-motion: reduce` must disable the seal
animation and the in-progress status pulse.

---

## 3. Routes

### Customer
| Route | Purpose | Rendering |
|---|---|---|
| `/` | Report an incident — the form *is* the landing page | Client (form state) |
| `/submitted/[reference]` | Filed receipt | Server |
| `/track/[token]` | Ticket record + ledger | **Server Component** |
| `/track/link` | Request a new tracking link | Client |

### Admin
| Route | Purpose | Rendering |
|---|---|---|
| `/admin/login` | Session login | Client |
| `/admin` | Queue — filters, search, sort, pagination | Client |
| `/admin/tickets/[reference]` | Ticket workspace | Client |

`/track/[token]` is a Server Component deliberately: no loading flash, and the token
never enters the client bundle.

**Navigation is asymmetric by design.** The customer side has only a wordmark and a
"Track a ticket" link — a nav bar in front of someone in distress is noise. The admin
side gets a persistent top bar plus a filter rail.

---

## 4. Responsive behaviour

| Breakpoint | Customer | Admin |
|---|---|---|
| ≥1141px | Single 700px document column | Three panes: 244px rail · 320px queue · detail |
| 781–1140px | Same | Rail + detail; the middle queue column is hidden |
| ≤780px | Single column, stacked name/email | Fully stacked; rail becomes a top block; queue rows drop the category and status columns |
| ≤470px | Docket and ledger rows collapse to one column | — |

Recovery screens (`/track/link` and the three token states) use a narrower 580px
column than the 700px record column.

Side gutter of at least 16px at every width, set once on the wrapper. Document column
caps at 700px so running text stays near 65 characters. No horizontal body scroll at
375px.

---

## 5. Reusable components

| Component | Notes |
|---|---|
| `StatusBadge` | Dot + label. Never colour alone. |
| `PriorityMark` | `▲` High / `■` Medium / `–` Low, plus label. |
| `CategoryTag` | Plain text, `--muted`. |
| `ReferenceCode` | Weight 600, `0.07em` tracking; copy-to-clipboard variant. |
| `StatusTransition` | Renders `old → new` with the old value struck through. |
| `TimelineEntry` | Variants: `event`, `response`, `internal-note`, `attachment`. |
| `CategorySelect` | Underlined select, custom chevron, the seven approved values. |
| `DropZone` | Client-side validation of count, size and type before upload. |
| `FormField` | Label, underlined control, error slot wired via `aria-describedby`. |
| `Composer` | Public / internal modes — see §7. |
| `FilterRail` | Status, priority, category facets with counts. |
| `Toast`, `EmptyState`, `SkeletonRow`, `ThemeToggle` | |

---

## 6. Customer flow

1. **`/`** — name, email, subject, **category (required select)**, description,
   optional attachments. Constraints stated up front: 5 files, 5 MB each, allowed
   types. Client-side validation for a valid email and non-empty required fields
   before submitting.
2. **Submit** — `multipart/form-data`. On `201`, the sheet seals (stamp settles) and
   routes to the receipt.
3. **`/submitted/[reference]`** — large "Filed.", reference in weight-600 tracked
   type with a copy button, the email address echoed back verbatim, three
   what-happens-next steps, and a visible route to request a new link. **No tracking
   link is shown** — that is Decision 1, and the copy must make it read as deliberate.
4. **Email → `/track/[token]`** — status band (status word, mark, "since" timestamp),
   docket (reference, priority, category, filed by, filed), the report as filed,
   attachments, then the ledger of activity.
5. **Recovery** — `/track/link` takes an email and always returns the same
   confirmation message, matching the API's non-enumerating `202`.

---

## 7. Admin flow

1. **`/admin/login`** — username and password. A failed login shows "Those
   credentials weren't recognised"; never reveal which field was wrong.
2. **`/admin`** — queue of dense rows: priority mark · **reference** · subject ·
   category · status · age. Age reads relatively ("4h", "2d"). Filter rail with counts;
   search; sort by created/priority/status; pagination.
   - **Selected row** uses four simultaneous cues: tinted ground, 3px `--oxide` left
     edge, bolded subject, and an `--oxide` reference.
3. **`/admin/tickets/[reference]`** — header leads with the reference above the
   subject, then reporter, client email and filed date. Control strip with status,
   priority and category selects (optimistic, rolling back on failure). Resend-link and
   revoke-links actions; revoke is behind a confirm dialog. Full history including
   operational events, with internal notes tinted `--ochre` and tagged.

### The composer — safety-critical

Both modes carry a **persistent banner**, so the active mode is never ambiguous:

| | Public | Internal |
|---|---|---|
| Banner | "Visible to the customer — {name} will be emailed a link to read it." | "Visible to staff only — the customer will not see this." |
| Container | `--surface`, neutral border | `--ochre` border, `--internal-bg` tint |
| Tab underline / button | `--ink` | `--ochre` |
| Button label | **Send reply** | **Add internal note** |
| Footer | "A fresh tracking link is included in every reply email." | "Kept on the ticket for the support team. No email is sent." |

A toggle alone is not sufficient protection against publishing an internal note.

---

## 8. States

### Error envelope
Every failure returns `{"error": {"code", "message", "details"}}`. Map it centrally in
`lib/api.ts`:

| Code | HTTP | UI |
|---|---|---|
| `validation_error` | 400 | Inline field errors driven by `details` |
| `invalid_token` | 404 | "We couldn't find this report." + request-new-link |
| `expired_token` | 410 | "This link has expired." + request-new-link |
| `revoked_token` | 410 | "This link has been replaced." + request-new-link |
| `permission_denied` | 403 | Redirect to `/admin/login` |
| `throttled` | 429 | "You've filed several reports recently" + retry guidance |
| `server_error` | 500 | Generic message; never a stack trace |

**Customer-facing screens must never show HTTP status codes or API error codes.**
Recovery states are distinguished by plain language, not by `invalid_token` and
friends.

### Loading
Skeleton rows in the admin queue and workspace. `/track/[token]` is server-rendered
and therefore has no loading state. Buttons enter a pending state on submit.

### Empty
Designed empty states for an unfiltered empty queue, a filtered-to-nothing queue
(offering "clear all filters"), a ticket with no attachments, and a ticket with no
activity beyond filing.

---

## 9. Accessibility

- Status and priority never carried by colour alone — always mark plus text label.
- Visible focus ring on every interactive element: `2px solid var(--oxide)`, `2px` offset.
- Form errors wired with `aria-describedby`; the invalid control gets `aria-invalid`.
- The category select is a real `<select>`; the composer mode switch is a labelled
  button group with `aria-pressed`.
- Every control has a stable `id`; icon-only buttons carry `aria-label`.
- `prefers-reduced-motion: reduce` disables the seal animation and status pulse.
- Contrast verified in **both** themes for `--muted` and `--faint` on their surfaces.
- Full keyboard pass through submission and the admin composer.

---

## 10. API integration

All calls go through `lib/api.ts`, which parses the error envelope into a typed result.

### Contract (as shipped)

| Method | Path | Notes |
|---|---|---|
| `POST` | `/api/tickets/` | multipart: `reporter_name`, `email`, `subject`, `category`, `description`, repeated `attachments`. → `201 {reference, subject, category, status, priority, created_at}` |
| `POST` | `/api/tickets/resend-link/` | `{email}` → `202 {message}` — identical for known and unknown addresses |
| `GET` | `/api/track/<token>/` | composite: `reference, subject, description, reporter_name, category, category_display, status, priority, created_at, resolved_at, responses[], events[], attachments[]` |
| `GET` | `/api/track/<token>/attachments/<id>/` | file download |
| `POST` | `/api/admin/auth/login/` | `{username, password}` |
| `POST` | `/api/admin/auth/logout/` | |
| `GET` | `/api/admin/auth/me/` | call on admin boot to obtain the `csrftoken` cookie |
| `GET` | `/api/admin/tickets/` | `?status=&priority=&category=&search=&ordering=&page=` |
| `GET` | `/api/admin/tickets/<reference>/` | full detail incl. internal responses and all events |
| `PATCH` | `/api/admin/tickets/<reference>/` | `{status?, priority?, category?}` — at least one required |
| `POST` | `/api/admin/tickets/<reference>/responses/` | `{message, is_internal}` |
| `POST` | `/api/admin/tickets/<reference>/resend-link/` | |
| `POST` | `/api/admin/tickets/<reference>/revoke-links/` | |
| `GET` | `/api/admin/tickets/<reference>/attachments/<id>/` | file download |

Search covers `reference`, `subject`, `reporter_name`, `client__email`.
Ordering covers `created_at`, `priority`, `status`.

### Rules
- **Customer responses carry no author** — the customer serializer returns only
  `message` and `created_at`. Never invent or display an author on the customer side.
- **Customer events are pre-filtered** by the backend to `CREATED`, `STATUS_CHANGED`,
  `RESPONSE_ADDED`. Render whatever arrives; do not re-filter or assume more.
- **CSRF:** send `X-CSRFToken` from the `csrftoken` cookie on every unsafe admin request.
- **`GET /api/admin/auth/me/` returns `403` when logged out** — that is the normal
  signed-out state, not an error to surface. It sets the `csrftoken` cookie either
  way (`ensure_csrf_cookie`), so call it before rendering the login form.
- **Server-side fetches must target the internal origin** (`http://backend:8000`). The
  Next.js `/api/*` rewrite applies only in the browser.
- **Throttles to expect:** submit 5/hour, token lookup 120/hour, resend 3/hour.
- `Referrer-Policy: no-referrer` on `/track/[token]`, since the token is in the URL.

---

## 11. Testing

Jest + React Testing Library, written alongside each component per CLAUDE.md.

- `CategorySelect` — required, renders exactly the seven approved values
- `DropZone` — rejects over-count, oversized, and disallowed types before upload
- `FormField` — renders `details` errors and wires `aria-describedby`
- `TimelineEntry` — all four variants, including the internal-note treatment
- `Composer` — mode switch changes banner, button label and footer copy
- `StatusTransition` / `StatusBadge` / `PriorityMark` — label present, not colour-only
- `lib/api.ts` — each error code maps to the right UI state; no HTTP or API codes leak
  into customer-facing copy

Full end-to-end Playwright flows are Step 4.

---

## 12. Implementation order

1. Scaffold `frontend/`, Tailwind + token layer, Poppins, theme handling, `lib/api.ts`
2. Shared components (§5)
3. `/` report form — including the category select and dropzone validation
4. `/submitted/[reference]` receipt
5. `/track/[token]` record (Server Component)
6. `/track/link` + the three recovery states
7. `/admin/login`
8. `/admin` queue — filters, search, sort, pagination
9. `/admin/tickets/[reference]` workspace — controls, history, composer
10. Responsive and accessibility pass at 375 / 768 / 1280, both themes, reduced motion

```
frontend/
├── app/
│   ├── layout.tsx, globals.css
│   ├── page.tsx
│   ├── submitted/[reference]/page.tsx
│   ├── track/[token]/page.tsx
│   ├── track/link/page.tsx
│   └── admin/{login,tickets/[reference]}/page.tsx
├── components/
├── lib/{api.ts,csrf.ts,format.ts}
├── next.config.js          # /api/* rewrite
├── tailwind.config.ts
└── __tests__/
```

Branches: `feature/frontend-customer`, `feature/frontend-admin`.

---

## 13. Out of scope

Playwright end-to-end flows (Step 4), Docker packaging (Step 5), coverage reporting
and the README (Step 6), and the optional analytics dashboard.
