# Saldora — Architecture & Reasoning

This document explains *why* Saldora is built the way it is — the
architectural decisions, the trade-offs, the things we deliberately
chose not to do. It is decision-oriented, not how-to-oriented; read it
as an ADR compilation that fits in one sitting.

It is **not**:

- A setup guide — that is [`DEVELOPER_GUIDE.md`](./DEVELOPER_GUIDE.md).
- A formal requirements spec — that is [`product/SRS.md`](../product/SRS.md).
- An end-user manual — that lives at [`user-experience/workflows.md`](../user-experience/workflows.md).
- A milestone roadmap — that is [`product/IMPLEMENTATION_GUIDE.md`](../product/IMPLEMENTATION_GUIDE.md).

Cross-link to those instead of duplicating them.

Target reader: a senior engineer (or curious investor / advisor) who has
thirty minutes and wants to know what we built, why, and what we
deliberately left out.

---

## 1. Product context in one paragraph

Saldora is an AI-powered invoice-processing pipeline for Serbian
accounting agencies whose clients are **hospitality businesses** —
restaurants, cafes, bars, fast food, catering. The wedge is the segment
where SEF (eFaktura) does not and will not reach soon: paper invoices
from beverage distributors, small producers, open-market suppliers, and
paušalci who fall outside the VAT system. A hospitality client receives
twenty to forty such invoices a month, many with dozens of line items
each, and the agency typing those into MiniMax (the dominant Serbian
ledger product for this segment) loses tens of hours every month.
Saldora reads those invoices with a vision-language model, normalises
their line items against a product catalog, classifies the accounting
intent, and hands a clean structured payload to MiniMax. The agency
keeps MiniMax for the books; Saldora owns the pipeline into it. The
forward-looking differentiator on top of that pipeline is the
**hospitality legal-forms layer** (kalkulacija, šank lista, KEP,
cenovnik, popis) generated automatically from the same extracted line-
item data — see §6 and §9 and the strategy doc cross-linked in §14.

---

## 2. Topology at a glance

Saldora runs on a **single Hetzner CX32 VPS** in Falkenstein, fronted by
Cloudflare for DNS / SSL / DDoS, with the only off-host workload being
the GPU-bound OCR step on Modal. Operational specifics — environment
files, deploy commands, scheduled tasks, restore drills — live in
[`DEPLOYMENT.md`](./DEPLOYMENT.md).

```
                          ┌────────────────────────┐
                          │      Cloudflare         │
                          │  DNS · SSL · CDN · WAF  │
                          └───────────┬────────────┘
                                      │  HTTPS (Flexible SSL)
                                      ▼
                          ┌────────────────────────┐
                          │ Hetzner CX32 — Germany │
                          │  (single VPS, Docker)  │
                          └───────────┬────────────┘
                                      │  HTTP :80
                                      ▼
                          ┌────────────────────────┐
                          │ saldora-caddy (reverse │
                          │ proxy + X-Forwarded-   │
                          │ Proto rewrite)         │
                          └────┬───────────────┬───┘
            saldora.rs ────────┘               └──────── api.saldora.rs
                       │                                          │
                       ▼                                          ▼
            ┌─────────────────┐                       ┌─────────────────────┐
            │  saldora-web    │                       │     saldora-api     │
            │ Next.js 16 :3000│                       │  FastAPI :8000      │
            └─────────────────┘                       └──────────┬──────────┘
                                                                 │
                          ┌──────────────────────────────────────┼──────────────────────────┐
                          ▼                                      ▼                          ▼
                ┌─────────────────┐                  ┌─────────────────┐         ┌────────────────────┐
                │ saldora-postgres│                  │  saldora-redis  │         │ saldora-ocr-worker │
                │  PostgreSQL 16  │                  │   (cache 0 ·    │         │  + saldora-celery- │
                │     :5432       │                  │  broker 1 ·     │         │  beat (scheduler)  │
                └─────────────────┘                  │  results 2)     │         └─────────┬──────────┘
                                                     └─────────────────┘                   │ HTTPS
                                                                                           ▼
                                                                                ┌─────────────────────┐
                                                                                │   Modal.com — A10G  │
                                                                                │  dots.ocr (vLLM,    │
                                                                                │  scale-to-zero)     │
                                                                                └─────────────────────┘

  Storage:  Cloudflare R2 (prod)  /  MinIO (dev) — same boto3 client, different endpoint.
  External: Anthropic Claude Haiku · Resend · NBS · MiniMax (per-org).
```

Compose file: `infra/docker/docker-compose.prod.yml`.
Caddy config: `infra/docker/Caddyfile`.
Modal app: `infra/modal/dots_ocr.py`.

Why this shape rather than the obvious alternatives gets unpacked in §3.

---

## 3. The four big architectural decisions

### 3.1 — Single VPS, not Kubernetes

| | |
|---|---|
| **What we chose** | One Hetzner CX32 (€8/mo) running Docker Compose. Caddy + Next.js + FastAPI + PostgreSQL + Redis + Celery worker + Celery beat as seven containers on one host. |
| **What we rejected** | Managed Kubernetes (GKE / EKS / Hetzner Cloud Kubernetes), Fly.io machines, Railway-style PaaS, multi-VPS with a load balancer. |
| **Why** | Saldora at launch serves Serbian accounting agencies with thirty-to-fifty hospitality clients each. The realistic ceiling for the next year is ~100 agencies — three to five thousand monthly invoices peak. A single CX32 carries that comfortably with PostgreSQL and Redis colocated. Kubernetes adds operator hours measured in days per quarter; we have neither the load nor the team to justify it. The cost gap is also instructive: €115/month all-in (VPS + Modal + Anthropic + R2 + Resend) versus the ~€400/month floor that managed Kubernetes plus a managed Postgres would impose. That delta is two months of agency revenue. |
| **When we'd revisit** | (a) Postgres CPU exceeds 50% of one VCPU for sustained periods, (b) a single agency tops 1,000 invoices/day so OCR concurrency outgrows one Celery worker, or (c) we land an enterprise contract that contractually requires multi-AZ. The first migration step is splitting Postgres onto its own VPS, not adopting Kubernetes. |

The trade-off we accept: every reboot is downtime. We mitigate with Cloudflare's serve-stale, the daily-04:00 R2 backup (§11), and the fact that Saldora is a B2B back-office tool — agencies care about a thirty-minute outage at noon less than a consumer SaaS would.

### 3.2 — Modal for OCR GPU, not in-cluster vLLM

| | |
|---|---|
| **What we chose** | Run `dots.ocr` (rednote-hilab) on Modal, behind an OpenAI-compatible vLLM server on an A10G GPU. Modal scales the container to zero when idle and spins it back up on the next request. Defined in `infra/modal/dots_ocr.py`. |
| **What we rejected** | A GPU-enabled VPS (€200+/mo always-on), Hetzner GPU Cloud, Replicate, Banana, hosting vLLM on a self-managed Lambda Labs instance, Cloud Run with NVIDIA L4 (we briefly tried — see the deleted `CLOUD_RUN_OCR_SETUP.md`). |
| **Why** | Hospitality agencies invoice in bursts — most uploads happen the first week of the month when prior-month documents land on the accountant's desk. An always-on GPU is idle 80% of the time. Modal's scale-to-zero plus ~2-minute cold start matches that profile: the agency uploads a batch of fifty invoices, the first one takes 2 minutes, the next forty-nine take seconds. Cost: ~$60/month for our projected 10K invoices. An always-on A10G runs €200+. The cold start hits exactly the right user: someone who just dropped a stack of paper on their desk and is going to make coffee anyway. |
| **When we'd revisit** | If a single agency moves to real-time receipt processing (POS-tied), the cold-start penalty becomes intolerable. Solution then is a warm-pool of one container (Modal supports it) or migrating to a dedicated GPU. We do not move to in-cluster vLLM — running a GPU on Hetzner doubles operator burden for no gain. |

### 3.3 — Manual invoicing, not card-on-file

| | |
|---|---|
| **What we chose** | The agency receives a Saldora invoice from us out-of-band (email PDF or paper) and pays it via bank transfer. We mark the org `active` (or `trial`, on first month) via `scripts/admin_orgs.py` and extend the subscription period by however much they paid for. No card collection, no online checkout, no recurring auto-renewal. |
| **What we rejected** | Stripe (unavailable for Serbian merchants), Paddle / LemonSqueezy / other Merchant-of-Record SaaS (operationally heavy for a manual-invoice-driven funnel where we want to talk to every customer anyway), a self-hosted card-present integration via a Serbian PSP (regulatory and PCI scope we will not absorb at this stage). |
| **Why** | The buyer is a small, named, slow-cycle audience — Serbian accounting agencies. Acquisition is sales-led, not self-service. Every prospect goes through a manual conversation, a DPA signature, and a first-period invoice before they upload anything; bolting an automated card-collection step onto that flow would add a tax/PCI/legal surface for no gain. Paying by bank transfer is also what these agencies' own customers do, so it's the channel they trust. We get a clean back-office: no chargebacks, no failed-card retry loops, no MoR fee skimming 5% off every renewal. |
| **When we'd revisit** | When (a) inbound signups outpace our ability to talk to every one, and (b) Stripe (or an equivalent) opens for Serbian merchants. Until both are true, the manual invoice + script-driven renewal stays the model. The data model already anticipates this: `Organization.subscription_status` ∈ {`pending`, `trial`, `active`, `canceled`, `expired`} is exactly what a future automated billing integration would write to — but today it's a human flipping it via the CLI. |

### 3.4 — Manual approval gate, not card-on-file

| | |
|---|---|
| **What we chose** | New organisations land in `subscription_status="pending"`. An admin reviews the registration and flips them to `active` or `trial` via `scripts/admin_orgs.py`. Only then can the org use the app. |
| **What we rejected** | Self-service trial with card collection at signup, automatic 14-day trial without card, captcha-only signup. |
| **Why** | Three reasons. First, the buyer is a small set of agencies, not a self-service consumer funnel — we want to talk to every one of them before they upload a single invoice. Second, every invoice processed through OCR has a real per-token cost; uncontrolled trials let abusers run up an Anthropic + Modal bill. Third, the ZZPL Data Processing Agreement (§12) is a signature-required step we want completed before the agency uploads anything sensitive. The approval gate is enforced in `apps/api/app/dependencies.py::require_role` — every mutational endpoint blocks orgs whose `subscription_status` is not in `{"active", "trial"}` (`APPROVED_SUBSCRIPTION_STATUSES`). |
| **When we'd revisit** | When we have a public pricing page, an automated billing rail (whatever that turns out to be — see §3.3), and the team bandwidth to handle dozens of self-service signups per week without a bottleneck. None of those exist today. |

---

## 4. Multi-tenancy model

**One `organization_id` partitions everything.** Every row in every
tenant-scoped table — `invoices`, `clients`, `client_events`,
`automation_rules`, `audit_logs`, `usage_records`, `api_keys`,
`product_catalog` — carries `organization_id`. Every list / read
endpoint filters by the JWT's `organization_id` claim. There is no
shared "global" data plane apart from `exchange_rates` (NBS daily rates,
which are the same for every tenant by definition) and ZZPL legal-text
records.

**One Saldora organisation = one accounting agency.** The agency's own
clients — the restaurants, cafes, bars they do the books for — live in
the **`clients`** table (`apps/api/app/models/client.py`). This is the
inversion newcomers find counterintuitive: in Saldora, "client" never
means "the agency themselves"; it always means "the restaurant whose
invoices the agency processes." This naming follows how Serbian
accounting agencies talk about their own business.

**Per-org S3 prefixes.** Documents are keyed as
`organizations/{organization_id}/invoices/{invoice_id}/original.{ext}`
in R2. The org-prefix matters for three reasons: (a) auditability — you
can list every document a single org owns with one prefix scan, (b) per-
org key rotation in the future (a single agency can be rotated to a new
encryption key without touching others), and (c) blast-radius
containment if a credential leaks. Bucket lifecycle policies and any
future tiered-storage rules attach naturally to the prefix.

**JWT contents.** The access token carries `sub` (user id), `type`
(`access` vs `refresh`), `jti` (for blacklisting on logout),
`organization_id`, `org_slug`, `role`, and `subscription_status`. The
`org_slug` is what drives the `/[orgSlug]/...` URL structure in the
frontend; the `subscription_status` is the auth-gate input (§3.4). The
refresh-token flow re-reads org status from the DB on every refresh
(`apps/api/app/routers/auth.py`) so an admin's approval flip lands in
the user's session within one hour without forcing a logout.

**No row-level security in Postgres.** We considered RLS and explicitly
chose application-layer enforcement instead. Reasoning: every read path
already goes through `require_role(...)` which loads the user, the org,
and the subscription state in one place; adding RLS doubles the trust
surface without halving the bug surface. We revisit this if we ever
allow direct read-only Postgres access to a customer (e.g. an
agency-side BI tool) — which we don't today.

---

## 5. Invoice processing pipeline

The end-to-end happy path, status transitions on the invoice row:

```
  ─── synchronous (HTTP request) ────────────┐  ─── asynchronous (Celery worker) ──────────────┐
                                              │                                                  │
  User → POST /api/v1/invoices/upload         │   Worker picks up "process_invoice" task         │
        │                                     │         │                                        │
        ├─▶ R2: PUT original.{ext}            │         ├─▶ R2: GET original.{ext}               │
        ├─▶ DB:  INSERT invoices              │         ├─▶ Modal: dots.ocr → markdown + layout  │
        │       status = processing           │         ├─▶ Anthropic: Haiku → structured JSON   │
        ├─▶ Redis: send_task(process_invoice) │         ├─▶ NBS: foreign currency → RSD          │
        └─▶ 202 Accepted { invoice_id }       │         ├─▶ DB:  UPDATE invoices                 │
                                              │         │       seller/buyer/line_items = ...    │
                                              │         │       confidence_score = ...           │
                                              │         │       status = review                  │
                                              │         └─▶ DB:  INSERT invoice_line_items[...]  │
                                              │              (denormalised projection — §6)      │
                                              │                                                  │
                                              ─── back to user, manual review ──────────────────┐
                                              │                                                  │
  User → GET /api/v1/invoices/{id} (poll)     │                                                  │
        │                                     │                                                  │
        └─▶ Side-by-side view, edit fields    │   On verify click:                               │
                                              │         │                                        │
  User → POST /api/v1/invoices/{id}/verify    │         ├─▶ AccountingIntent classifier          │
                                              │         │       (doc-type / VAT / konta)         │
                                              │         ├─▶ Rules engine: per-org + per-client   │
                                              │         │       (audit row per firing)           │
                                              │         └─▶ DB:  status = verified               │
                                              │                                                  │
  User → POST /api/v1/exports/minimax/{id}    │                                                  │
        │                                     │   In the export task:                            │
        └─▶ Returns export id                 │         ├─▶ MiniMax REST API (per-org creds)     │
                                              │         └─▶ DB:  status = exported               │
                                              │                                                  │
```

Status transitions, in order:

```
  processing  ──▶  review  ──▶  verified  ──▶  exported
        │            │
        │            └─▶  error                  (OCR failure, human re-uploads)
        └─▶  error                               (storage / queue failure)
```

**Why dots.ocr (a vision-language model), not EasyOCR / Tesseract.**
Serbian invoices mix Cyrillic and Latin in the same field; line-item
columns are tabular with inconsistent spacing; supplier letterheads
override default fonts; and many invoices are photos taken with a phone
under fluorescent lighting in a cramped agency office. Classical OCR
engines (Tesseract, EasyOCR, PaddleOCR) handle clean documents in one
script and one orientation, and degrade sharply on real Serbian paper.
`dots.ocr` is a VLM trained specifically for document parsing with
multilingual coverage including Cyrillic; on our internal test set it
produces line-item-level recall an order of magnitude higher than
EasyOCR for the same documents. The model is too large for a CPU; that
is why we accept the Modal cold-start (§3.2).

**Why we still run Claude Haiku after dots.ocr.** dots.ocr returns
markdown-flavoured text — accurate but unstructured. Downstream
consumers (the verification UI, the rules engine, the AccountingIntent
classifier, the MiniMax exporter, the future hospitality-forms
generator) all need a stable JSON contract: seller, buyer, dates,
amounts, per-line {description, quantity, unit_price, tax_rate, total},
tax_groups, currency, plus a `field_confidence` map. Claude Haiku
converts the markdown to that contract reliably and cheaply (~$0.0045
per invoice) and, in the same prompt, performs a first-pass
classification of accounting intent (document type, transaction type,
VAT treatment). Running a second smaller pipeline to do the JSON
formatting and then a third for classification would be slower, more
brittle, and not noticeably cheaper.

**Why we do not preprocess images for the VLM.** Empirically — and this
contradicts the standard advice for classical OCR — deskewing,
binarising, and contrast-stretching *degrades* VLM accuracy. The model
was trained on real photographs and learns to compensate for skew /
lighting in ways that preprocessing throws away. We send the original
upload (resized only to fit the model's max edge) to Modal. Cropping
and rotation hints are not used.

**No automated OCR fallback.** If dots.ocr fails or returns garbage,
the invoice lands in `status="error"` and the human verifier sees it
in the review queue. We deliberately did not wire an EasyOCR fallback,
even though the early architecture diagram included one. The reasoning:
the failure modes of EasyOCR on Serbian invoices are silent — it
returns plausible-looking text that is in fact wrong, which is worse
than a clear "OCR failed, please review manually" status. A human
verifier looking at a flagged document beats a worse-automated-guess in
both accuracy and trust.

**No model retraining loop.** Every invoice the user corrects writes to
`correction_log` (`apps/api/app/models/correction_log.py`), but those
corrections are *not* used to fine-tune dots.ocr or Claude. ZZPL
compliance (§12) and the operational cost of running a fine-tuning
pipeline outweigh any accuracy gain, especially when the upstream model
improves on its own release schedule.

References in code:

- `workers/ocr_worker/tasks.py` — Celery `process_invoice` task.
- `infra/modal/dots_ocr.py` — Modal deployment, vLLM server.
- `apps/api/app/services/accounting_intent.py` — 5-step intent pipeline (SRS §4.10).
- `apps/api/app/services/line_item_sync.py` — denormalises JSON line items to `invoice_line_items`.

---

## 6. Data model decisions

**`invoices.seller`, `.buyer`, `.line_items`, `.tax_groups` as JSON
columns.** Invoice formats vary too widely to normalise pre-emptively —
the seller block on a beverage-distributor invoice has different fields
than on a small-producer cash receipt. Forcing a normalised
`invoice_parties` table would either lose data (we drop unrecognised
fields) or explode into a thirty-column table with most columns NULL.
JSON wins here. The trade-off: SQL aggregation across line items
becomes painful. We address that with a *separate* denormalised table
(next bullet) rather than by normalising `invoices` itself.

**`invoice_line_items` as a normalised companion table.** Defined in
`apps/api/app/models/line_item.py`. Populated automatically after OCR
completes and on every user edit to the invoice. The JSON column in
`invoices` remains the source of truth; `invoice_line_items` is a
read-optimised projection. We took this two-table approach because
reports — line-item-by-supplier, top-products-by-spend, šank lista
inputs — need pure SQL with `GROUP BY product_id`, and trying to do
that against a JSON column with PostgreSQL's `jsonb_array_elements`
wedges the planner on bigger tenants. The cost is the sync logic in
`apps/api/app/services/line_item_sync.py`, which is a hundred lines and
fully covered by tests.

**`client_events` append-only.** Defined in
`apps/api/app/models/client_event.py`. Every mutation that touches a
specific client (invoice uploaded, invoice verified, rule fired,
accounting-intent classified, export completed, form generated) writes
exactly one row. Rows are never updated and never deleted by
application logic. The Timeline tab of the client workspace (§10)
renders rows from this table for the current client and period. The
append-only constraint is doctrinal: emitters live inside the
transaction of the business operation they describe
(`apps/api/app/services/events.py::emit` does not commit; the caller's
session does), so events are atomically consistent with the operation
itself, and there is never a "we did the thing but forgot to log it" or
vice versa. Idempotency at the emitter level (same operation never
fires twice) means we did not need a dedupe layer on read.

**`rule_client_associations` as a join table.** Defined in
`apps/api/app/models/rule_client_association.py`. An automation rule
with zero associations is **global** to the org. An automation rule
with one or more associations is **scoped** to those specific clients.
Putting the scoping in a join table rather than a `client_ids` JSON
column on `automation_rules` lets us index lookups efficiently
(`WHERE rule_id = ? AND client_id = ?` becomes an index seek) and
enforces foreign-key integrity. The trade-off is one extra table and
one extra read in the rules-engine fast path — both worth it for the
multi-client-scoping case M19 introduced.

**`Organization.subscription_status` as the auth gate.** One column,
four meaningful values: `pending` (waiting for admin approval), `trial`
(approved, no payment yet), `active` (approved, paying), `canceled`
(was paying, stopped), `expired` (trial ran out without conversion). A
`NULL` is treated as `pending`. The `require_role(...)` dependency
(§7) reads this column on every request and 403s with a structured
`subscription_pending_approval` body when it is not in
`{"active", "trial"}` (`APPROVED_SUBSCRIPTION_STATUSES`). The frontend
catches that code and routes the user to `/awaiting-approval` (§10).

**`Client.legal_form` + `Client.bookkeeping_system` (the M20 prep).**
Added in migration `0018_add_client_hospitality_classification.py`.
`legal_form` is one of `"DOO" | "preduzetnik" | "paušalac" | "drugo"`;
`bookkeeping_system` is `"dvojno" | "prosto"`. Both nullable because
legacy clients land unclassified and the agency fills the values in at
first review. These two columns drive the **hospitality obligation
matrix** — given a client's `(legal_form, bookkeeping_system)`, the
service `apps/api/app/services/hospitality_forms.py::required_forms`
returns which legal forms (kalkulacija, KEP, cenovnik, popis, DPU,
PK-1) the agency must produce for that client. The matrix is encoded
as data (frozensets and a status dict), not a chain of `if`-statements,
so adding a future form is a one-line change. Frontend never re-derives
the matrix — it consumes
`GET /api/v1/clients/{id}/obligations`. See §13 for what is and isn't
shipped form-by-form.

**Why `Client.pib` is `VARCHAR(20)`, not `CHAR(9)`.** Serbian PIBs are
nine digits, but foreign entities can have longer tax IDs (Italian
P. IVA is 11, EU VAT IDs are up to 15 including the prefix). Hospitality
clients themselves are always Serbian and would fit in 9, but their
suppliers — which show up as the `buyer` block on outgoing invoices and
the `seller` block on incoming — are not. We use 20 everywhere to keep
the schema homogeneous.

---

## 7. Authentication & authorization

**Token pair: 1h access + 7d refresh.** Issued at login and on every
refresh. Both signed JWTs (HS256, secret in env). The access token
carries the claims listed in §4. The refresh token carries only `sub`,
`type=refresh`, `jti`. Refresh rotation: every refresh issues a new
access *and* a new refresh, and the old refresh is blacklisted by its
`jti`. The blacklist is a Redis set with TTL matching the original
token's expiry, so it self-cleans. Logout blacklists the current
access token's `jti` and the user's most recent refresh token's `jti`.

**Argon2id for password hashing.** Configured in
`apps/api/app/auth.py`. Argon2id rather than bcrypt because (a) it is
the OWASP 2024+ recommendation, (b) the memory-hardness defeats GPU
brute-force attacks more decisively than bcrypt's iteration count, and
(c) passlib supports it out of the box so the operational cost is zero.

**Role hierarchy: admin > manager > operator > viewer.** Defined as
`ROLE_HIERARCHY` in `apps/api/app/dependencies.py`. Levels 4 → 1. The
`require_role("manager")` dependency lets a user with `manager` or
`admin` through and 403s `operator` and `viewer`. This is intentionally
simpler than RBAC-with-permissions because the agency itself is small
(rarely more than ten users) and a flat hierarchy maps to how Serbian
accounting agencies are actually structured: owner (admin), senior
accountants (manager), bookkeepers (operator), interns (viewer).

**`require_role` does three checks in one place.** This is the critical
auth-flow line: every mutational endpoint in the app depends on
`require_role(...)`, which (1) verifies the user's role is at least
the minimum, (2) verifies the user belongs to an organisation
(`user.organization_id is not None`), and (3) verifies the
organisation's `subscription_status` is in
`APPROVED_SUBSCRIPTION_STATUSES`. Centralising these three gates in one
dependency is what lets us evolve the rules (e.g. add `ban` as a
status) without auditing every router.

**`require_verified_email` separately for sensitive flows.** Export,
billing changes, deletion requests, and ZZPL-consent endpoints layer
`require_verified_email` on top of `require_role`. We deliberately do
*not* gate ordinary read/upload behind email verification — bouncing
users at upload is worse UX than letting them try the product and
nudging email verification before they export. The split is documented
inside `apps/api/app/dependencies.py`.

**Approval flow end-to-end.** A new user does this:

1. `POST /api/v1/auth/register` — creates a user with no
   `organization_id`. A welcome email goes out (via Resend).
2. `POST /api/v1/organizations` — the user creates an org. The org
   lands in `subscription_status="pending"`. The user becomes the
   org's admin. An admin-notification email goes to the Saldora team's
   billing inbox.
3. The user logs in. The JWT carries
   `subscription_status="pending"`. The frontend's `postAuthRoute()`
   (`apps/web/src/lib/api/auth.ts`) sees that and routes them to
   `/awaiting-approval` (§10) instead of the app shell. Any direct hit
   on a mutational API endpoint returns the structured 403 described
   in §6.
4. A Saldora admin runs `scripts/admin_orgs.py` (CLI) to flip the org
   to `active` or `trial`. An activation email goes to the user.
5. The user lands on `/awaiting-approval` and polls
   `GET /api/v1/users/me` every 15s via
   `AuthContext.refreshUser()`. As soon as the status flips, the
   client routes them into the app.

Why polling and not server-sent events: we have no real-time channel
in the stack and adding one for a flow that fires once per signup is
unjustified.

**X-Forwarded-Proto rewriting in Caddy.** Production runs Cloudflare in
"Flexible SSL" mode: CF → Caddy is plain HTTP, Caddy → app is plain
HTTP. Without the `header_up X-Forwarded-Proto https` directive in
`infra/docker/Caddyfile`, FastAPI sees scheme=http and any 307
trailing-slash redirect on a `@router.get("/")` list endpoint builds a
`Location: http://api.saldora.rs/...` that the browser refuses to
follow (mixed-content block). The header override forces FastAPI's
`url_for` and trailing-slash redirect logic to emit `https://`. This
was a real outage in production once (`Fix HTTPS→HTTP redirect on
trailing-slash list endpoints (#213)`) and is the one piece of
proxy-aware glue that has to stay correct.

---

## 8. Background processing (Celery)

**Redis logical-DB split: db 0 cache / db 1 broker / db 2 results.**
`apps/api/app/config.py` keeps `redis_url` (cache) and
`celery_broker_url` / `celery_result_backend` distinct. The cache lives
on db 0 so that flushing the cache during a deploy never touches in-
flight Celery messages or results. The broker / result split is
Celery's recommended layout — it lets us monitor queue depth via
`LLEN` on db 1 without that count being polluted by result-bag keys.

**Why Celery, not arq / rq / Dramatiq.** Two reasons. First, Celery's
operational maturity — beat scheduling, retry/backoff semantics, dead-
letter handling, `task_acks_late` + `task_reject_on_worker_lost` for
worker-loss safety — is something we get for free and would have to
reimplement on the lighter alternatives. Second, the OCR worker imports
heavy ML deps (httpx for Modal, the PIL/image stack for resizing, the
Anthropic SDK), and Celery's pre-fork pool model amortises the import
cost across many tasks per worker process. Async-first frameworks like
arq don't help us here because the bottleneck is wall-clock GPU time,
not connection multiplexing.

**`send_task` from the API, not direct task imports.** The API never
imports `workers/ocr_worker/tasks.py`. Instead, the upload handler
calls `celery_client.send_task("ocr_worker.tasks.process_invoice",
args=[...], queue="ocr")` against the broker URL. This pattern keeps
the FastAPI image small and Python-deps-clean — the API doesn't need
torch, vLLM client libs, or the Modal SDK installed. The worker
imports those. The signature contract between API and worker is just
the task name and the JSON-serializable args.

**Test routing: `memory://` broker, no `task_always_eager`.** Test
fixtures route Celery to the in-process `memory://` transport so unit
tests run without Redis. We deliberately do **not** use
`task_always_eager = True` even though it is the obvious shortcut,
because eager mode hides serialization bugs (a task that passes a
SQLAlchemy session object works eagerly but blows up in production)
and skips the worker-state setup. The `memory://` broker gives us the
same realistic round-trip with zero infra dependency.

**Beat schedule.** Defined in `workers/ocr_worker/celery_app.py`:

| Task | Schedule (Europe/Belgrade) | Purpose |
|---|---|---|
| `fetch_nbs_exchange_rates` | Weekdays 08:30 | NBS EUR/USD/CHF/GBP → RSD daily middle rate |
| `aggregate_daily_usage` | Daily 02:00 | Roll invoice counts into `usage_records` for plan quotas |
| `enforce_data_retention` | Daily 03:00 | Honour ZZPL deletion requests once retention windows lapse |
| `backup_database` | Daily 04:00 | `pg_dump` → gzip → R2, with manifest + SHA-256 checksum |
| `run_monthly_archive_exports` | 1st of month 06:00 | Generate per-org month-archive ZIPs, email billing contact |

Why these hours, in this order: 02:00 / 03:00 / 04:00 sequencing
guarantees usage aggregation is done before retention deletes anything
(so deletions never undercount usage) and that retention runs before
backup (so the backup reflects the post-retention state and isn't
storing data we just decided to delete). 04:00 is also a low-traffic
window — Serbia is GMT+1/+2 and agencies start their day around 08:00.
08:30 for NBS rates is when the NBS publishes them; we hit the
endpoint at 08:30:00 and have rates available for the workday.

---

## 9. The accounting-intent layer

**Why it exists.** OCR + Claude Haiku give us fields — seller, buyer,
amounts, line items. The ledger needs *meaning*: what kind of document
is this (faktura vs avansni račun vs odobrenje vs storno), what kind of
transaction (purchase / sale / internal), how should the VAT be
treated (standard 20% / reduced 10% / 0% / reverse-charge / outside-
VAT), which konta (chart-of-accounts entries) does it suggest, and is
it low-confidence enough that a human needs to look at it before
export.

That classification work lives in
`apps/api/app/services/accounting_intent.py` and the corresponding row
in `apps/api/app/models/accounting_intent.py`. The pipeline is five
steps (matching SRS §4.10): document-type classification → transaction-
type classification → VAT-treatment determination → konto suggestion
→ confidence aggregation and review-flag emission. Each step's output
is stored so a verifier can see *which* step produced a given suggestion
and adjust if needed.

**Rules engine on top of intent.** Defined in
`apps/api/app/services/rules_engine.py`. Per-org automation: "if seller
PIB is X and total > Y RSD, set client = Z and konto = 5331."
Per-client scoping via `rule_client_associations` (§6). Priority-driven
evaluation — higher priority rules fire first; first-match-wins per
slot. Full execution audit: every rule firing writes a `client_event`
of type `rule_fired` with the rule id, the matched invoice id, and the
applied actions. Audit-trail completeness was a design requirement
from M11; we cannot ship "automatic classification" without a clear
breadcrumb for the auditor to follow back.

Why the intent layer is generic and the forms layer (§13) is
hospitality-specific: every invoice everywhere needs accounting intent
to be useful in any ledger. Kalkulacija and šank lista only matter for
hospitality clients. We keep intent as a foundation and the forms as a
hospitality-only feature on top.

---

## 10. Frontend architecture

**Next.js 16 App Router, strict TypeScript, Tailwind 4.** No Pages
Router. No JavaScript files. Tailwind's config is the v4
`@theme`-in-CSS form; no `tailwind.config.js`. Server Components
default; client components opt-in with `"use client"` only where they
need state or browser APIs.

**Route groups.**

- `(auth)/` — unauthenticated routes: login, register, password-reset
  flows, the email-verify landing page, the `/awaiting-approval`
  page, and the invite-acceptance page. No app shell, no sidebar.
- `(app)/[orgSlug]/...` — authenticated app shell. `orgSlug` is the
  active organisation; users with one org never see a chooser. Every
  child route is automatically scoped to that org.

**`/awaiting-approval` (the M19 follow-on).** Lives under `(auth)/`
even though the user is technically authenticated, because the user is
not allowed into the app shell yet. The page renders a friendly
"awaiting admin approval" message and polls `GET /users/me` every 15
seconds via `AuthContext.refreshUser()`. As soon as the response
returns `subscription_status: "active" | "trial"`, the client routes
the user into `/[orgSlug]/klijenti`.

**Client-first UI.** The historical layout was feature-indexed: top-
level `Fakture`, `Klijenti`, `Izveštaji`, `Pravila`, each a global list
filtered by client. The M19 redesign inverted that. Today:

- `/[orgSlug]/klijenti` is the **portfolio surface** — the agency-wide
  list of clients with health indicators (invoices pending review,
  blocked, last activity). It is the default landing page; the org
  root `/[orgSlug]/page.tsx` redirects to `/klijenti`.
- `/[orgSlug]/klijenti/[clientId]` is the **per-client workspace** —
  one client, one page, tabs below for Hronologija (timeline) /
  Fakture / Izveštaji / Pravila. Everything inside the tabs is pre-
  scoped to this client; no client-filter UI is shown because there is
  nothing to filter.
- Agency-level operations stay outside the workspace: Pravila (org-
  wide rules view), Arhiviranje (period archives), Katalog proizvoda,
  Dashboard, Settings, Team, Billing.

The `Hronologija` tab renders rows from
`GET /api/v1/clients/{id}/events` (§6). The `Izveštaji` tab is where
the future hospitality forms will land — the new `ObligationsCard`
(`apps/web/src/components/reports/ObligationsCard.tsx`) is the first
visible piece of that work and consumes the obligation matrix from
`hospitality_forms.required_forms` (§6, §13).

**`AuthContext` + `postAuthRoute()` as the routing decision point.**
After login, registration, or refresh, exactly one function decides
where the user goes: `postAuthRoute(user)`. It returns
`/awaiting-approval` if `subscription_status` is not approved, or
`/[orgSlug]/klijenti` if it is, or `/onboarding/create-organization` if
the user has no org yet. Centralising this means every place in the
code that authenticates a user uses the same logic — there is no
divergence between "what the login page does" and "what the register
page does."

**`next-intl` with three locales.** `en`, `sr-Latn`, `sr-Cyrl`. UI
strings live in `apps/web/messages/{en,sr-Latn,sr-Cyrl}.json`. Why
three rather than two: Latin is the product default and what we ship
to most agencies (Serbian Latin is the dominant business script);
Cyrillic is for agencies and users who prefer it (some older
accountants strongly do); English is for the marketing site, the admin
console, and foreign stakeholders / investors / advisors. We do *not*
support automatic translation between Latin and Cyrillic (e.g. via
transliteration) — the keys are translated independently because some
strings (proper nouns, legal-document names, software trademarks) do
not transliterate cleanly.

**Hot reload + on-demand refresh.** `AuthContext.refreshUser()`
fetches a fresh `/users/me`, replaces the in-memory user, and persists
nothing extra — the JWT cookie is the source of truth. The
`/awaiting-approval` poll, the post-billing-change refresh, and the
"role changed" admin-team-page refresh all use this same hook.

---

## 11. Storage & data lifecycle

**S3-compatible: Cloudflare R2 in production, MinIO in development.**
Same `boto3` client, same key shapes, different endpoint URL. We never
write provider-specific code. The `storage` service
(`apps/api/app/services/storage.py`) exposes `upload_invoice_file`,
`generate_presigned_url`, `delete_invoice_file`, `ensure_bucket_exists`,
and a sync `put_object`/`get_object` pair for the worker. All sync
boto3 — wrapped with `asyncio.to_thread(...)` from async callers.

**Key format: `organizations/{org_id}/invoices/{invoice_id}/original.{ext}`.**
The org prefix is load-bearing (§4). The `original.{ext}` filename
keeps room for future variants under the same invoice
(`thumbnail.jpg`, `preview.pdf`, `extracted.json` for cache) without
breaking the prefix-scan contract.

**Daily DB backup, 30-day retention, monthly archive emails.** Celery
beat fires `backup_database` daily at 04:00 (§8). It runs `pg_dump
--format=plain --no-owner --no-privileges` inside the Postgres
container, gzips the output, computes a SHA-256, and uploads
`backups/db/saldora_YYYY-MM-DD.zip` to R2 with a `manifest.json`
inside the zip carrying the checksum, the pg_dump command line, and
the row counts per major table for sanity checks. Lifecycle policy on
R2 deletes anything older than 30 days. On the 1st of every month, the
beat `run_monthly_archive_exports` task generates a per-org archive
ZIP (invoices, line items, exports, audit log, ZZPL events) and emails
a download link to the org's billing contact — this is the customer-
facing artefact that satisfies the long-tail retention obligation
(below).

**10-year retention obligation, handled by *not deleting* + archive
exports.** Serbia's Zakon o računovodstvu requires ten years of
retention on accounting source documents. We don't delete invoices
older than ten years; we just stop showing them in the main UI after
the customer cancels. The retention obligation legally rests on the
customer, not on Saldora. The monthly archive exports give the
customer everything they need to satisfy that obligation
*independently* of us — if Saldora disappeared tomorrow, the agency
still has every month's worth of structured data in their email. This
is a deliberate decoupling: we don't want to be a single point of
failure for our customers' legal compliance.

**Why R2 and not S3 / GCS.** R2 has zero egress fees, which matters
because we serve presigned URLs to the verification UI on every page
view. S3 + CloudFront would either rack up egress or require a more
complex caching layer. R2's API is S3-compatible to the point where
nothing in our boto3 code changes. EU region (default) keeps us
data-residency-safe for ZZPL (§12).

---

## 12. ZZPL compliance

**Zakon o zaštiti podataka o ličnosti (RS) is primary; GDPR is
reference.** Serbia is not in the EU. ZZPL is the law that binds us.
GDPR informs how we interpret ZZPL because (a) ZZPL was modelled on
GDPR, (b) some Serbian agencies have EU customers and need GDPR
compliance for those, and (c) when ZZPL is ambiguous, the safer
reading is the GDPR-aligned one.

**Data residency in EU/EEA or Serbia.** Hetzner Falkenstein is in
Germany (EU). R2 default region is EU. Modal's EU region carries the
OCR workload. Anthropic processes in the US — that crossing is
addressed by Anthropic's Standard Contractual Clauses, which we
counter-sign as part of our DPA. Resend is EU-headquartered and
processes in EU. We do not currently use a third-party payment processor — billing is manual (§3.3) so there is no payment-data crossing.

**`consent_records` table.** Defined in
`apps/api/app/models/consent_record.py`. Every time a user agrees to
the DPA, the privacy policy, or the cookies banner, we write a row
recording (user_id, consent_type, version_hash_of_doc_at_time_of_consent,
ip, user_agent, timestamp). This is the audit trail required for ZZPL
Article 16 (proof of consent).

**`deletion_requests` table.** Article 21 right-to-be-forgotten
requests are captured as rows with a state machine
(`requested → acknowledged → processed → completed`) and processed by
the daily `enforce_data_retention` Celery task. We do not honour a
deletion until any pending retention obligations (tax / accounting law
overrides ZZPL deletion for source documents) are clear; the audit
trail of that decision lives in the row's `processing_notes`.

**No model training on user data.** Strict invariant. Neither
dots.ocr nor Claude is trained or fine-tuned on customer invoices.
Anthropic's API call has training opt-out set; Modal's model weights
are frozen at deploy time and never updated based on customer input
(§5). This is the simplest and strongest customer-facing privacy
guarantee we can make: "your invoices are processed, not learned
from."

---

## 13. What we deliberately don't do (or do later)

- **SEF as a load-bearing channel.** Deferred indefinitely. The
  hospitality wedge is paper; SEF coverage of paper-equivalent
  invoices from paušalci, open-market producers, and small suppliers
  is years away. We will add SEF *ingestion* as a data source if and
  when agencies report it as a need (it's lightweight on top of the
  existing pipeline), but we are not building Saldora around SEF.

- **Paušal module.** Reverted M14. The paušalac segment is owned by
  MiniMax's dedicated paušal app and we cannot displace that
  incumbent. Saldora's hospitality clients are DOO and preduzetnik;
  they may have paušalac *suppliers* (which we handle as a supplier
  type in the OCR pipeline), but we do not market to or serve
  paušalci themselves. The `direction` field on invoices, the
  `client_type` field on clients, the `customers` table, the
  `invoice_counters` table, and the KPO ledger were all removed.

- **Client portal.** M16 in the old tracker. Dropped. End clients —
  the restaurants themselves — do not log in. Hospitality owners
  send documents by email, WhatsApp, or paper to their agency, who
  uploads them. Selling direct to restaurants is low-ARPU and
  support-intensive; we do not touch that channel.

- **Compliance watchdog.** M18 in the old tracker. Dropped.
  Scheduled rule evaluation with proactive alerts was paušal-era
  thinking. The rules engine still exists and fires on events; we
  just don't add a scheduled-watchdog layer on top.

- **Automatic OCR fallback (EasyOCR / Tesseract).** Deliberate
  non-feature, see §5. Manual review beats a silently-wrong
  automated guess.

- **Model retraining loop.** Deliberate non-feature, see §5 and
  §12.

- **Card-on-file billing.** Deferred until self-service makes sense
  (§3.4). Today, every new org is approved manually via
  `scripts/admin_orgs.py`.

- **Kubernetes / multi-VPS.** Deferred until we hit the triggers
  in §3.1.

- **Hospitality legal forms beyond the obligation matrix.** Partial.
  The matrix endpoint is live and the `ObligationsCard` is in the
  client workspace's Reports tab. Two forms have skeleton endpoints
  (`kalkulacija` and `DPU`) marked `pre_meeting` in
  `_BUILD_STATUS` (`apps/api/app/services/hospitality_forms.py`) —
  the column structures are best-guess drafts pending validation at
  the accountant meeting. Four forms (`kep`, `cenovnik`, `popis`,
  `pk1`) are marked `post_meeting` and have no implementation yet.
  The full forms milestone (M20) is staged for after the agency
  meeting produces concrete specs; see
  [`product/M20_accountant_meeting_agenda.md`](../product/M20_accountant_meeting_agenda.md).

- **Close checklist and period semantics.** M21, deferred until the
  forms work clarifies what a complete hospitality month actually
  contains.

- **Bank reconciliation, payment tracking, general-ledger postings.**
  Permanently out of scope. MiniMax handles these. Saldora is the
  pipeline into MiniMax, not a replacement for it.

- **Foreign-invoice reverse-charge as a standalone module.** The
  existing NBS conversion and AccountingIntent handle the
  hospitality-realistic foreign-invoice cases (incidental
  cross-border purchases). Standalone reverse-charge tooling is
  revisited only if hospitality agencies report it as a pain.

---

## 14. Sources of truth (cross-link map)

Each foundational doc owns exactly one slice of the story. When in
doubt, look here first.

| Doc | Owns |
|---|---|
| [`product/SRS.md`](../product/SRS.md) | Formal requirements (FR-numbered). §1 carries the hospitality thesis; §4.17 lists explicitly dropped features; §4.18-4.19 cover the client-first UI and the hospitality forms layer. Cite FR numbers in commit messages when implementing a specific requirement. |
| [`product/SRS_sr.md`](../product/SRS_sr.md) | Serbian Latin SRS. Same content; either is authoritative depending on the reader. |
| [`product/SRS_sr_simple.md`](../product/SRS_sr_simple.md) | Business-friendly Serbian version of the SRS. No code blocks; for sales / partner reading. |
| [`product/IMPLEMENTATION_GUIDE.md`](../product/IMPLEMENTATION_GUIDE.md) | Milestone breakdown M1 through M21. Banner at the top calls out dropped milestones (M14 paušal, M16 client portal, M18 watchdog). Post-pivot milestones table is the canonical forward-planning surface; M19 sequencing principles are at the bottom. |
| [`product/M20_accountant_meeting_agenda.md`](../product/M20_accountant_meeting_agenda.md) | Pre-meeting strawman for the agency meeting that unlocks M20. Read before scheduling that meeting. Delete after the meeting. |
| [`DEVELOPER_GUIDE.md`](./DEVELOPER_GUIDE.md) | Setup, local dev, conventions. The how-to-run-the-thing doc. Do not duplicate setup content into other docs. |
| [`DEPLOYMENT.md`](./DEPLOYMENT.md) | Production operations. SSH, container restart, log inspection, backup/restore, Modal deployment. The on-call runbook. |
| [`AUTOMATION_RULES.md`](./AUTOMATION_RULES.md) | How the rules engine works — condition operators, action types, scoping semantics. Pair this with `apps/api/app/services/rules_engine.py` when working on rules. |
| [`ML_PROJECT_ARCHITECTURE_GUIDE.md`](./ML_PROJECT_ARCHITECTURE_GUIDE.md) | ML pipeline internals — engines, fields, validation, types. |
| [`../user-experience/workflows.md`](../user-experience/workflows.md) | Click-by-click reference of every workflow currently supported in the app. The doc to send a new bookkeeper. |
| [`CLAUDE.md`](../../CLAUDE.md) | AI-assistant conventions for this repo. Issue workflow, commit style, code standards. The "how Claude should behave here" doc. |
| **This file (`dev/architecture.md`)** | The "why we built it this way" doc. Decisions, trade-offs, deliberate non-features. ADR compilation in one place. |

If you change architecture, update this file first and then update the
code. If you change setup, update `DEVELOPER_GUIDE.md`. If you change
ops, update `DEPLOYMENT.md`. If you change product direction, update
`product/SRS.md` and `product/IMPLEMENTATION_GUIDE.md`. If you find this file contradicting code, the code
is wrong or the doc is — and the answer to which is "whichever was
touched last has the authority, but argue it out in PR review before
merging the second one."
