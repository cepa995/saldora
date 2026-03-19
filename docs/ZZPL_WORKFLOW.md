# ZZPL Compliance — Application Workflow

How each ZZPL feature works in practice, from the user's perspective.

## 1. Consent Management

**When:** During registration and in account settings.

**How it works:**
- When a user signs up, they see checkboxes for consent types:
  - **Osnovna obrada** (basic_processing) — always required, pre-checked and disabled. You can't use the app without it.
  - **Analitika** (analytics) — optional. Allows us to track usage patterns for improving the product.
  - **Marketing** (marketing) — optional. Allows promotional emails and product announcements.
- Checking a box calls `POST /api/v1/compliance/consent` with the consent type.
- In account settings, users can toggle analytics/marketing on or off at any time.
- Revoking calls `POST /api/v1/compliance/consent/revoke`. Basic processing cannot be revoked (returns 422).
- Every grant/revoke creates a new immutable row in `consent_records` — full audit trail.

**Why it matters:** If the Poverenik (Serbian data protection authority) asks "when did user X consent to marketing?", we can show the exact timestamp, IP address, and consent text version.

**API endpoints:**
- `POST /api/v1/compliance/consent` — grant consent
- `POST /api/v1/compliance/consent/revoke` — revoke consent
- `GET /api/v1/compliance/consent` — current status for all types
- `GET /api/v1/compliance/consent/history` — full audit trail (admin only)

---

## 2. Right to Erasure (ZZPL Article 30)

**When:** A user wants to delete their account.

**How it works:**
1. User goes to account settings and clicks "Obriši nalog" (Delete account).
2. This calls `POST /api/v1/compliance/deletion-requests` creating a **pending** request.
3. An admin reviews the request in the dashboard.
4. When processing (`POST /deletion-requests/{id}/process`), the system:
   - **Anonymizes** the user profile: name → "Obrisani Korisnik", email → `deleted_xxx@anonymized.local`
   - **Retains** invoices (10-year requirement per Zakon o računovodstvu) and audit logs (7 years)
   - Records exactly what was kept and why in `retained_categories`
5. Alternatively, admin can **reject** with a reason (e.g., active contracts pending).

**The catch:** Serbian accounting law (Zakon o računovodstvu) requires 10-year invoice retention. So we can't fully delete everything — we anonymize the person but keep the financial records. The `retained_categories` field documents this with the legal basis in Serbian.

**API endpoints:**
- `POST /api/v1/compliance/deletion-requests` — submit request
- `GET /api/v1/compliance/deletion-requests` — list all (admin)
- `GET /api/v1/compliance/deletion-requests/{id}` — detail (admin)
- `POST /api/v1/compliance/deletion-requests/{id}/process` — complete or reject (admin)

---

## 3. Data Processing Agreements (DPA)

**When:** When the organization shares personal data with third-party processors (OCR services, email providers, payment processors).

**How it works:**
1. Admin creates a DPA record with title, version, and effective dates.
2. When both parties agree, admin signs it via `POST /dpa/{id}/sign`.
3. Signing sets status from `draft` → `active` and records who signed and when.
4. DPAs can expire (`effective_until` date) or be terminated.

**In practice:** This is mostly a compliance checkbox for enterprise sales. Small businesses won't use it. It's important for agencies processing invoices on behalf of multiple clients — they need a DPA with each client per ZZPL.

**API endpoints:**
- `POST /api/v1/compliance/dpa` — create DPA
- `GET /api/v1/compliance/dpa` — list DPAs (admin)
- `GET /api/v1/compliance/dpa/{id}` — detail (admin)
- `POST /api/v1/compliance/dpa/{id}/sign` — sign and activate (admin)

---

## 4. Breach Notification

**When:** If there's a data breach (unauthorized access, data leak, etc.).

**How it works:**
1. Admin enters incident details: date, description, affected data types, measures taken, recommendations.
2. `POST /breach-notification/preview` renders a formal Serbian-language notification.
3. The notification references ZZPL Article 52 and the 72-hour reporting deadline to the Poverenik.
4. Admin reviews the preview, then manually sends it to affected users and files with the authority.

**Why it's preview-only:** Breach response requires human judgment — you need to verify the scope, coordinate with legal, and decide who to notify. Auto-sending would be reckless.

**API endpoint:**
- `POST /api/v1/compliance/breach-notification/preview` — render notification (admin)

---

## 5. Privacy Policy

**When:** Always visible. Linked from footer, registration page, and account settings.

**How it works:**
- `GET /api/v1/compliance/privacy-policy` returns the current policy in Serbian.
- No authentication required — public endpoint.
- Includes all ZZPL-required sections:
  - Rukovalac podataka (data controller)
  - Svrha obrade (processing purpose)
  - Pravni osnov (legal basis)
  - Kategorije podataka (data categories)
  - Čuvanje podataka (retention periods)
  - Prava lica (data subject rights with ZZPL article references)
  - Kontakt Poverenika (supervisory authority contact)

**API endpoint:**
- `GET /api/v1/compliance/privacy-policy` — public, no auth

---

## Frontend Integration Points

| Feature | Page | UI Element |
|---------|------|-----------|
| Consent (registration) | `/registracija` | Checkboxes for analytics + marketing consent |
| Consent (settings) | `/podesavanja/privatnost` | Toggle switches for each consent type |
| Privacy policy | `/politika-privatnosti` | Full policy text from API |
| Delete account | `/podesavanja/nalog` | "Obriši nalog" button → confirmation modal |
| Deletion requests | `/admin/zzpl` | Table of pending requests with approve/reject |
| DPA management | `/admin/zzpl/ugovori` | DPA list with create/sign actions |
| Breach notification | `/admin/zzpl/incident` | Form → preview → manual send |

---

## Legal References

- **ZZPL** — Zakon o zaštiti podataka o ličnosti (Sl. glasnik RS, br. 87/2018)
- **Zakon o računovodstvu** — 10-year document retention requirement
- **Član 26 ZZPL** — Right of access
- **Član 29 ZZPL** — Right to rectification
- **Član 30 ZZPL** — Right to erasure
- **Član 31 ZZPL** — Right to restriction of processing
- **Član 36 ZZPL** — Right to data portability
- **Član 52 ZZPL** — Breach notification obligation (72 hours)
- **Poverenik** — https://www.poverenik.rs
