# Saldora — Supported user workflows

This document is a click-by-click reference for everything an agency owner or bookkeeper can do in the Saldora product today. It is intended for two readers: the agency owner who has been issued a login and wants a no-nonsense desk reference, and the bookkeeper opening the app for the first time. A product manager can also use it to write release notes — every section corresponds to a real route or endpoint that ships today.

This is **not** a roadmap (see `../product/IMPLEMENTATION_GUIDE.md`) nor an architecture doc (see `../dev/architecture.md`). Where a workflow touches a surface that is still under construction (KEP, cenovnik, popis after M20), the doc says so and points to `../product/M20_accountant_meeting_agenda.md` rather than guessing at clicks.

---

## 0. Conventions used in this document

- UI labels appear in Serbian Latin script, matching what the product shows on screen — e.g. `Pregled portfelja`, `Klijenti`, `Hronologija`, `Izveštaji`, `Pravila`, `Dodaj klijenta`. The doc body itself is in English.
- Numbered steps map one-to-one to clicks. If a step requires typing, the field name is given in Serbian Latin and the expected content is described in English.
- Each workflow opens with **Prerequisites** (what must already be true before step 1), followed by **Steps**, then a one-paragraph **Behind the scenes** describing what the server does, then a **Status** badge, and where the workflow replaces a paper or Excel process, a **Time saved vs Excel** estimate.
- Status badges:
  - **Shipped** — the entire workflow works in production today.
  - **Partial** — the workflow runs end-to-end but a downstream step (e.g. column structure of a generated form) is still pre-meeting and may change.
  - **Coming** — placeholder or unbuilt; documented here only because it appears in navigation today, with a pointer to where the spec is being decided.
- Route paths use the same shape the product uses internally — `/{orgSlug}/klijenti/{clientId}` — so developers reading this document can find the corresponding page file under `apps/web/src/app/(app)/[orgSlug]/`.
- If a step depends on server-side state (e.g. *your organization must be activated by an admin first*), the prerequisite is called out before the step list.
- "Admin" inside the product means an organization administrator (the agency owner). "Saldora admin" means a Saldora-side operator who runs `scripts/admin_orgs.py`.

---

## 1. Account workflows

### 1.1 — Sign up and wait for approval

**Prerequisites:** none.

**Steps:**
1. Visit `saldora.rs`.
2. Click `Započnite besplatno` (or `Registrujte se` from the login screen).
3. On the registration form, fill in `Ime`, `Prezime`, `E-mail adresa`, and `Lozinka`. Re-type the password under `Potvrdite lozinku`.
4. Check `Prihvatam politiku privatnosti`. Optionally check the analytics or marketing consents — neither is required to proceed.
5. Click `Kreirajte nalog`. The form validates the password length, that the two passwords match, and that the email is not already registered.
6. On success you advance to the `Podesite vašu organizaciju` step. Choose `Kreiraj` (the default) and fill in `Naziv organizacije` (e.g. *Knjigovodstvena agencija X d.o.o.*) and `PIB` (a 9-digit Serbian tax ID — leading zero is rejected, checksum is validated).
7. Click `Kreiraj organizaciju`. You are signed in and redirected to `/awaiting-approval`.
8. On the awaiting-approval screen, you can click `Proveri status` at any time. The page does not auto-poll; the button re-checks `subscription_status` and, the moment it flips to `active` or `trial`, you are redirected to `/{orgSlug}/klijenti`.

**Behind the scenes:** A user row plus an organization row are created in one transaction; the organization is created with `subscription_status = 'pending'`. The admin notification goes to `settings.admin_email`. A Saldora admin runs `scripts/admin_orgs.py` (see workflow 9.1), picks the org, and flips it to `active` or `trial` with a plan tier. The next time the registered user clicks `Proveri status`, the auth context sees the new status and routes them into the app.

**Status:** Shipped.

**Time saved vs Excel:** n/a — this is account creation.

### 1.2 — Log in

**Prerequisites:** account created and the organization is `active` or `trial` (otherwise login succeeds but you are redirected to `/awaiting-approval`).

**Steps:**
1. Visit `saldora.rs` and click `Prijavite se`, or go directly to `/login`.
2. Enter `E-mail adresa` and `Lozinka`.
3. Click `Prijavite se`.
4. On success you land on `/{orgSlug}/klijenti` (the portfolio).

**Behind the scenes:** Submits to `POST /api/v1/auth/login`, receives a JWT, stores it client-side, and seeds the auth context with the active organization, role, and feature flags. After 5 failed attempts the account is locked for 15 minutes.

**Status:** Shipped.

### 1.3 — Forgot password / reset

**Prerequisites:** none beyond having an email associated with an account.

**Steps:**
1. From `/login`, click `Zaboravili ste lozinku?`.
2. Enter your `E-mail adresa` on `/password-reset` and click `Pošaljite link`.
3. The screen always shows the same message (`Ako nalog sa tom e-mail adresom postoji…`) — this is deliberate so the form cannot be used to enumerate accounts.
4. Open the email in your inbox and click the reset link. You land on `/password-reset/confirm`.
5. Enter `Nova lozinka` (minimum 8 characters), confirm it, and click `Resetuj lozinku`.
6. The success state shows `Lozinka resetovana` and links back to `/login`.

**Behind the scenes:** `POST /api/v1/auth/password-reset` issues a single-use token bound to the user; `POST /api/v1/auth/password-reset/confirm` consumes the token and hashes the new password. Tokens expire after 24 hours.

**Status:** Shipped.

### 1.4 — Log out

**Prerequisites:** signed in.

**Steps:**
1. Open the user menu in the sidebar (avatar bottom-left on desktop, hamburger on mobile).
2. Click `Odjavi se`.
3. You are redirected to `/login`.

**Behind the scenes:** Clears the JWT from client storage and resets the auth context. There is no server-side session to invalidate.

**Status:** Shipped.

### 1.5 — Verify email address

**Prerequisites:** registered but the verification email link was never opened.

**Steps:**
1. From any signed-in page a banner reading `Vaša email adresa nije potvrđena…` appears.
2. Click `Pošalji ponovo` to receive a fresh verification email, or open the original one.
3. Click the link in the email. You land on `/verify-email`, which checks the token and shows one of three outcomes (`uspešno potvrđena`, `nevažeći ili istekao`, or `već potvrđena`).
4. Click `Idite na kontrolnu tablu` to continue.

**Behind the scenes:** Tokens are single-use and time-limited. Re-sending invalidates any prior token. Unverified users can still use the app — the banner is informational, not a gate, except for actions that explicitly require a verified email (none today).

**Status:** Shipped.

---

## 2. Agency setup workflows

### 2.1 — Invite a bookkeeper to the agency

**Prerequisites:** signed in as an admin or manager of the organization.

**Steps:**
1. Open `/{orgSlug}/settings`.
2. Click the `Tim` tab.
3. Under `Pozovite člana`, enter the bookkeeper's `E-mail adresa`.
4. Pick a role from `Uloga`. The choices are:
   - `Administrator` — full access including team and billing.
   - `Menadžer` — can manage clients, invoices, rules, and reports; cannot change billing.
   - `Operater` — can upload, review, and verify invoices.
   - `Posmatrač` — read-only.
5. Click `Pošalji pozivnicu`. A toast confirms `Pozivnica je poslata`.
6. The pending invitation appears under `Poslate pozivnice`. The bookkeeper receives an email with a one-time link.
7. The invited bookkeeper clicks the email link, lands on `/invite/{token}`, sees `Pozvani ste da se pridružite organizaciji {orgName} kao {role}`, signs in (or registers if new), and clicks `Prihvati pozivnicu`.

**Behind the scenes:** `POST /api/v1/invitations` issues a token bound to email + role + organization. The token is single-use; clicking `Otkaži` next to a pending invite revokes it via `DELETE /api/v1/invitations/{id}`. The acceptance flow at `POST /api/v1/invitations/accept/{token}` creates the membership row and links the user to the organization.

**Status:** Shipped.

**Time saved vs Excel:** Replaces ad-hoc password-sharing or per-machine config; roughly 15 minutes per new hire onboarded.

### 2.2 — Approve a join request

**Prerequisites:** an external user has clicked `Pridruži se` during registration and searched for your organization. You are the admin of that organization.

**Steps:**
1. Open `/{orgSlug}/settings` → `Tim` tab.
2. Scroll to `Zahtevi za pridruživanje`. A badge in the sidebar shows the pending count.
3. For each request, read the optional message the user wrote, then click `Odobri` or `Odbij`.
4. The approved member appears under `Članovi tima` with the default role of `Operater`. You can change the role from the same screen.

**Behind the scenes:** `POST /api/v1/join-requests/{id}/approve` creates the membership and emails the requester. Rejection emails the requester without exposing why.

**Status:** Shipped.

### 2.3 — Update organization details

**Prerequisites:** signed in as admin.

**Steps:**
1. Open `/{orgSlug}/settings` → `Organizacija` tab.
2. Edit any of: `Naziv kompanije`, `PIB`, `E-mail za fakturisanje`. The `URL identifikator` (slug) is read-only and the `Plan` row is informational only — see workflow 8 for plan changes.
3. To update the logo, drag-and-drop or click `Otpremi logo` (PNG or JPG, max 2 MB). To remove it, click `Ukloni logo`.
4. Click `Sačuvaj organizaciju`. A toast confirms `Podešavanja organizacije su sačuvana`.

**Behind the scenes:** `PATCH /api/v1/organizations/current` writes the fields. Logo upload is multipart to `POST /api/v1/organizations/current/logo` and the resulting URL is stored on the org row and shown in the sidebar after refresh.

**Status:** Shipped.

### 2.4 — Manage team member roles and removal

**Prerequisites:** signed in as admin.

**Steps:**
1. Open `/{orgSlug}/settings` → `Tim` tab.
2. In the `Članovi tima` list, change the dropdown next to a member to a different `Uloga`. A toast confirms `Uloga je promenjena`.
3. To remove a member entirely, click `Ukloni` next to their row. A confirmation dialog asks `Da li ste sigurni da želite da uklonite ovog člana?`. Click confirm. A toast confirms `Član je uklonjen`.

**Behind the scenes:** `PATCH /api/v1/team/members/{user_id}` updates the role; `DELETE /api/v1/team/members/{user_id}` revokes membership. The removed user retains their account but loses access to this organization on next request.

**Status:** Shipped.

### 2.5 — Configure MiniMax connection

**Prerequisites:** signed in as admin. Your MiniMax account must already have API access enabled (the agency may need to contact MiniMax support to obtain Client ID and Client Secret).

**Steps:**
1. Open `/{orgSlug}/settings` → `Integracije` tab.
2. Find the `MiniMax integracija` card. Click `Podesi`.
3. Read the `Kako povezati MiniMax?` checklist:
   - Contact `support@minimax.rs` and request API access for your organization.
   - MiniMax issues a Client ID and Client Secret (these are app-level credentials).
   - In MiniMax: go to `Moj profil → Podešavanja → API` and create an API username and password.
   - In MiniMax: under `Organizacija → Opšti podaci`, copy the Organization ID number shown next to the organization name.
4. Fill in `Client ID`, `Client Secret`, `Korisničko ime`, `Lozinka`, `MiniMax Organization ID`. Use the show/hide toggles next to secrets if you need to verify what you typed.
5. Click `Sačuvaj`. A toast confirms `Konfiguracija je sačuvana`.
6. Click `Testiraj vezu`. On success the toast reads `Uspešno povezano sa MiniMax`. On failure the toast surfaces the underlying error in Serbian (added in the most recent source-of-truth pass) — typical errors include invalid credentials, mistyped Organization ID, or network reachability.
7. Once the test passes, the integration shows `Povezano` and the `Pošalji u MiniMax` action becomes available in the export dialog (workflow 6.4).

**Behind the scenes:** `PUT /api/v1/export/minimax/config` encrypts and stores the credentials per organization. `POST /api/v1/export/minimax/test-connection` exchanges the credentials for a session token and probes one read-only endpoint. The error message returned by MiniMax is mapped to a Serbian hint where we recognize the underlying cause.

**Status:** Shipped.

**Time saved vs Excel:** n/a — this is configuration.

---

## 3. Client management workflows

### 3.1 — Add a hospitality client to the portfolio (M20-prep classification)

**Prerequisites:** signed in as admin or manager.

**Steps:**
1. Open `/{orgSlug}/klijenti`. This is also `Pregled portfelja` — there is one combined route today.
2. Click `Dodaj klijenta` (top-right; on mobile, the short label `Dodaj`).
3. In the modal, fill in `Naziv` and `PIB` — both required. PIB must be unique across the agency; a duplicate is rejected with `Klijent sa ovim PIB-om već postoji`.
4. Optionally fill in `Matični broj (MB)`, `Adresa`, `Grad`, `Poštanski broj`, `Email`, `Telefon`.
5. Scroll to the `Klasifikacija (ugostiteljski klijent)` section. Pick `Pravna forma`:
   - `DOO (privredno društvo)` — the `Sistem knjigovodstva` dropdown becomes disabled and a hint reads `DOO po zakonu vodi dvojno knjigovodstvo`.
   - `Preduzetnik` — the `Sistem knjigovodstva` dropdown stays enabled. Pick `Dvojno knjigovodstvo` or `Prosto knjigovodstvo`.
   - `Paušalac` — the `Sistem knjigovodstva` dropdown is disabled and a hint reads `Paušalci su van obima Saldore`.
   - `Drugo` — bookkeeping dropdown stays enabled.
6. Optionally add free-text `Napomene`.
7. Click `Sačuvaj`. A toast confirms `Klijent je uspešno kreiran`.
8. After save, the new client appears as a card in the portfolio grid. Click it (anywhere on the card) to open `/{orgSlug}/klijenti/{clientId}`.
9. On the workspace header the classification chips appear next to PIB — for example *DOO* and *Dvojno*. The `Izveštaji` tab now shows the `Obavezni obrasci` card derived from this classification.

**Behind the scenes:** `POST /api/v1/clients` writes `legal_form` and `bookkeeping_system` to the `clients` table. The obligation card later calls `GET /api/v1/clients/{id}/obligations`, which evaluates `app/services/hospitality_forms.py` — a data-driven matrix that returns which of `kalkulacija`, `kep`, `cenovnik`, `popis`, `dpu`, `pk1` are obligatory for this client and what each form's build status is. The frontend never re-derives this; it consumes whatever the matrix returns. Classification is also used by auto-assignment: an uploaded invoice whose buyer PIB matches this client is linked automatically.

**Status:** Shipped. Note that the *forms* themselves are partial — see section 10.

**Time saved vs Excel:** Replaces a manually-maintained client roster in a spreadsheet plus a paper note of each client's legal form. About 5 minutes per onboarded client; the real savings come downstream once the obligation forms are filled in.

### 3.2 — Edit a client

**Prerequisites:** signed in as admin or manager.

**Steps:**
1. From `/{orgSlug}/klijenti`, hover a card (or tap on mobile) and click the pencil icon. Alternatively, open the client workspace and click `Izmeni` in the header.
2. The same modal as in workflow 3.1 opens, pre-filled.
3. Change any fields. The classification rules (DOO disables bookkeeping, etc.) apply on every edit.
4. Click `Sačuvaj`. A toast confirms `Klijent je uspešno izmenjen`.
5. The obligation matrix re-renders if the classification changed.

**Behind the scenes:** `PATCH /api/v1/clients/{id}`. Changing classification does not retroactively re-tag previously uploaded invoices; auto-assignment runs at upload time.

**Status:** Shipped.

### 3.3 — Deactivate or reactivate a client

**Prerequisites:** signed in as admin or manager.

**Steps:**
1. Open `/{orgSlug}/klijenti/{clientId}`.
2. Click the kebab (three vertical dots) icon in the header next to `Izmeni`.
3. Click `Neaktivan` (if currently active) or `Aktivan` (if currently inactive).
4. A toast confirms the change. An inactive client retains all data and invoices but no longer appears in default-filtered lists; the badge `Neaktivan` shows next to the client name.

**Behind the scenes:** `POST /api/v1/clients/{id}/toggle-active`. Toggle is reversible and does not cascade — invoices, rules, and events remain intact.

**Status:** Shipped.

### 3.4 — Delete a client (cascade rules)

**Prerequisites:** signed in as admin or manager.

**Steps:**
1. From `/{orgSlug}/klijenti`, hover a card and click the trash icon.
2. A confirmation dialog reads `Trajno brisanje klijenta — Da li ste sigurni da želite da trajno izbrišete ovog klijenta? Fakture će ostati, ali neće biti povezane sa klijentom. Ova akcija je nepovratna.`
3. Click `Izbriši`.

**Behind the scenes:** `DELETE /api/v1/clients/{id}` removes the client row but leaves invoices in place with `client_id = NULL`. This is by design — the underlying invoice documents are legally retained for 10 years under Zakon o računovodstvu, even after the client relationship ends.

**Status:** Shipped.

### 3.5 — Open the portfolio at a glance

**Prerequisites:** signed in.

**Steps:**
1. Open `/{orgSlug}/klijenti`. The route is also `/{orgSlug}/` (the org root) which redirects here.
2. The header shows the total client count and, if any are flagged, a count like `3 zahteva pažnju`.
3. Use the `MonthPicker` in the header to choose the reporting period (default: current month). All cards re-render to reflect that month's counts.
4. Use the search box (`Pretraži po nazivu ili PIB-u`) to narrow by name or PIB substring.
5. Use the filter pills `Sve` / `Zahteva pažnju` / `U redu` to filter by health.
6. Each card shows: avatar, name, PIB, a status chip if anything is blocked or past-due or pending, `Fakture` count, `Ukupan iznos` (RSD), and a 6-month sparkline of invoice counts. The card is sorted by severity then alphabetically.
7. Click any card to open the workspace at `/{orgSlug}/klijenti/{clientId}`.

**Behind the scenes:** `GET /api/v1/portfolio?period={YYYY-MM}` returns per-client roll-ups: invoice count, total amount, pending review count, blocked count, past-due count, last activity timestamp, and a 6-month monthly series. Severity is computed client-side as `blocked × 10 + past_due × 5 + pending`.

**Status:** Shipped.

**Time saved vs Excel:** Replaces a manual monthly status sheet. About 20-30 minutes per month for a 10-client agency.

---

## 4. Invoice workflows (the daily driver)

### 4.1 — Upload one invoice

**Prerequisites:** signed in. Your plan must not be over its monthly invoice cap (the upload UI will surface an upgrade modal if it is).

**Steps:**
1. Open `/{orgSlug}/upload`.
2. Either drag-and-drop the invoice file onto the drop zone, click the zone to open a file picker, or on mobile tap `Fotografišite fakturu` to use the device camera.
3. Supported formats: PDF, JPEG, PNG, TIFF, BMP, WEBP. Maximum 20 MB per file. Rejected files show `Nepodržan format fajla` or `Fajl je prevelik`.
4. After selection, a card appears showing the filename and file size. Click `Obradi fakturu`.
5. A `PipelineStepper` advances through `Otpremanje` → `Na čekanju` → `OCR obrada` → `Pregled`. Live status comes from polling the invoice status endpoint.
6. When the stepper reaches `Pregled`, click `Pregledaj` to jump to `/{orgSlug}/invoices/{id}` for verification (workflow 4.3). You can also click `Učitaj nove fakture` to upload more without leaving the page.

**Behind the scenes:** `POST /api/v1/invoices/upload` accepts multipart, writes the file to R2 storage at `organizations/{org_id}/invoices/{invoice_id}/original.{ext}`, creates an invoice row in `processing` state, and dispatches a Celery OCR task via `send_task()`. The worker runs dots.ocr for layout and text extraction, then Claude Haiku to produce a structured JSON, then `line_items_sync` materializes line items into `invoice_line_items`. Auto-assignment then runs: for a hospitality invoice we match on `buyer.pib` against the client roster (the agency client is the buyer); for the fallback we match on `seller.pib`. If a match is found the invoice's `client_id` is set and a `client_assigned` event is emitted.

**Status:** Shipped.

**Time saved vs Excel:** Replaces manual data entry of header, line items, and VAT breakdown. Roughly 5-7 minutes saved per invoice.

### 4.2 — Upload a batch (up to 50)

**Prerequisites:** signed in. The selected files together must not exceed the per-batch ceiling and the org's monthly cap.

**Steps:**
1. Open `/{orgSlug}/upload`.
2. Select up to 50 files in the file picker, or drag a folder/multi-selection into the drop zone. The card list shows each file with its size.
3. If any file fails validation (too large, unsupported format), it shows an inline error and is excluded from the submission. Click `Ukloni fajl` to remove others before submitting.
4. Click `Obradi fakture (N)`.
5. Each file gets its own stepper card. Files queue independently and process in parallel up to the worker pool size; the dashboard banner `N faktura u redu za obradu` shows the live queue with an estimated wait `Procenjeno vreme čekanja: ~N min`.
6. As each file finishes, the card switches to `Pregledaj`. You can verify them in any order or come back later — they are all visible in `/{orgSlug}/invoices` once complete.

**Behind the scenes:** Each file is a separate `POST /api/v1/invoices/upload`. The batch ceiling (50) is enforced client-side; the server enforces the per-organization monthly cap and returns a `plan_error` payload if exceeded — the UI then shows the `UpgradeModal`.

**Status:** Shipped.

**Time saved vs Excel:** For a daily 20-invoice agency, this collapses 1.5-2 hours of manual entry into a 1-minute upload plus on-demand review.

### 4.3 — Review and verify an extracted invoice

**Prerequisites:** the invoice must be in status `Pregled` (i.e. OCR + extraction complete). Verified or processing invoices cannot be edited.

**Steps:**
1. Open `/{orgSlug}/invoices/{id}` (from the dashboard, the invoices list, the portfolio workspace, or the upload pipeline).
2. The page shows the document on the left with `Uvećaj`, `Umanji`, `Prilagodi`, and `Rotiraj` controls, and the extracted fields on the right grouped into `Podaci o fakturi`, `Prodavac`, `Kupac`, `Iznosi`, `Stavke`, and (if applicable) `Plaćanje`.
3. Each field carries a `ConfidenceBadge` — `Pouzdano` (green), `Proveriti` (amber), or `Nepouzdano` (red).
4. Click any field to edit inline. Common changes: fix a misread PIB (validates the 9-digit checksum), correct an invoice number, change the `Datum fakture` or `Datum dospeća`, add a line item via `Dodaj stavku`.
5. The `Pregled PDV-a po stopama` panel auto-totals per VAT rate. If the math does not match (line item totals vs header total), a yellow `Razlika od X` warning appears next to the computed total. Adjust line items until it reads `Matematika se poklapa`.
6. If the invoice is in a foreign currency, the `RSD ekvivalent` line shows the NBS middle rate for the invoice date.
7. Optionally assign the invoice to a `Klijent` from the dropdown. If auto-assignment already matched, the client is pre-filled.
8. Click `Verifikuj`. A toast confirms `Faktura je uspešno verifikovana` and the status badge changes to `Verifikovano`.
9. If required fields are missing the verify button is disabled with the tooltip `Nedostaju obavezna polja za verifikaciju`.

**Behind the scenes:** `PATCH /api/v1/invoices/{id}` saves field changes. `POST /api/v1/invoices/{id}/verify` flips the status to `verified` and pins the data as the official record — verified invoices are what flow into KPR/KIR books, exports, and reports. Once verified, the invoice surface is read-only by default. `GET /api/v1/invoices/{id}/accounting-intent` populates the suggested konto/PDV treatment panel where the agency can approve or override the AI's classification.

**Status:** Shipped.

**Time saved vs Excel:** Replaces transcribing 15-25 fields per invoice. About 4-6 minutes per invoice in steady state.

### 4.4 — Reject or re-upload an invoice

**Prerequisites:** signed in. The invoice must not have been exported (deletion of exported invoices is blocked by audit policy).

**Steps:**
1. Open `/{orgSlug}/invoices/{id}` (or select the invoice in the list).
2. Click `Više akcija` → `Izbriši fakturu`.
3. Confirm in the dialog `Da li ste sigurni da želite da izbrišete ovu fakturu?`.
4. A toast confirms `Faktura je uspešno izbrisana`.
5. To re-upload a corrected scan, return to `/{orgSlug}/upload` and upload the corrected file as a fresh invoice (workflow 4.1).

**Behind the scenes:** `DELETE /api/v1/invoices/{id}` performs a soft delete (the row is marked deleted; the audit trail row is retained). The original file on R2 is retained for retention compliance.

**Status:** Shipped.

### 4.5 — Search and filter the invoice list

**Prerequisites:** signed in.

**Steps:**
1. Open `/{orgSlug}/invoices`.
2. Use the search box `Pretražite po broju fakture, prodavcu ili kupcu...`.
3. Filter by status using the chips `Sve` / `Obrada` / `Pregled` / `Verifikovano` / `Izvezeno` / `Greška`.
4. Filter by date using `Datum od` and `Datum do`.
5. Click any column header to sort ascending or descending — `Status`, `Broj fakture`, `Datum`, `Prodavac`, `Kupac`, `Iznos`, `Pouzdanost`.
6. Select multiple rows with the checkbox in the leftmost column, then use the batch actions bar at the top: `Verifikuj`, `Izbriši`, `Izvezi`, `Označi kao plaćeno`.

**Behind the scenes:** `GET /api/v1/invoices` accepts `search`, `status`, `date_from`, `date_to`, `sort_by`, `sort_dir`, pagination params, and a `client_id` filter used by the workspace tab.

**Status:** Shipped.

### 4.6 — Record a payment against an invoice

**Prerequisites:** invoice is verified and not fully paid.

**Steps:**
1. Open `/{orgSlug}/invoices/{id}`.
2. Scroll to `Plaćanje`. The current `Status plaćanja` shows `Neplaćeno`, `Delimično plaćeno`, or `Plaćeno`.
3. Click `Evidentiraj uplatu`.
4. Enter `Iznos uplate` and `Datum uplate`. Optionally enter `Napomena (referenca, izvod...)` — usually the bank statement reference.
5. Click `Sačuvaj`. A toast confirms `Uplata uspešno evidentirana`.
6. The `Preostalo` field updates; when it reaches zero the status flips to `Plaćeno`.

**Behind the scenes:** A payment row is appended to the invoice. The system rejects payments that would over-pay (`Iznos ne može biti veći od preostalog duga`).

**Status:** Shipped.

**Time saved vs Excel:** Replaces a separate aging spreadsheet. The savings show up in the `Otvorene stavke` and `Analiza dospeća` reports — workflow 6.1.

---

## 5. Per-client workflows (M19 client-first UI)

### 5.1 — Open the portfolio

See workflow 3.5. The portfolio at `/{orgSlug}/klijenti` doubles as `Pregled portfelja`; there is no separate `/pregled` route in the current build.

### 5.2 — Open one client's workspace

**Prerequisites:** signed in. The client must exist (active or inactive).

**Steps:**
1. From `/{orgSlug}/klijenti`, click anywhere on a client card.
2. You land on `/{orgSlug}/klijenti/{clientId}` with the `Hronologija` tab selected by default. The URL can also be entered directly or shared with a teammate; the `tab` query parameter (`?tab=fakture`, `?tab=izvestaji`, `?tab=pravila`) selects a tab.
3. The page header shows:
   - The client avatar and name. An `Neaktivan` chip appears if applicable.
   - Metadata chips: `PIB`, `MB` (if set), `Grad` (if set), `Email` (if set), and the two hospitality classification chips with a violet tone — e.g. `Pravna forma DOO`, `Sistem knjigovodstva Dvojno`.
   - `Izmeni` and kebab (toggle active/inactive) buttons for admin/manager users.
4. Below the header sits the three-tile health strip: `Fakture`, `Na pregledu`, `Blokirano`. Tiles turn amber/rose when their counts are non-zero.
5. The tab bar reads `Hronologija` / `Fakture` / `Izveštaji` / `Pravila`.

**Behind the scenes:** `GET /api/v1/clients/{id}` for the header data, `GET /api/v1/clients/{id}/workspace-stats` for the tile counts. Both are fetched in parallel on load.

**Status:** Shipped.

### 5.3 — Review the event timeline

**Prerequisites:** workspace open on `Hronologija`.

**Steps:**
1. The tab lists every event that has occurred for this client, newest first: invoice uploads, verifications, exports, manual client assignments, and auto-assignments by PIB.
2. Each event row reads in plain Serbian, e.g. `Učitana faktura {filename}`, `Verifikovana faktura {invoiceNumber}`, `Faktura {invoiceNumber} izvezena (MiniMax XML)`, `Faktura {invoiceNumber} automatski dodeljena po PIB-u`.
3. Click a row that references an invoice to jump to `/{orgSlug}/invoices/{id}`.
4. If there are no events in the selected period the panel shows `Nema događaja u izabranom periodu`.

**Behind the scenes:** `GET /api/v1/clients/{id}/events` returns a chronological list of client-scoped audit-log events.

**Status:** Shipped.

**Time saved vs Excel:** This is the "what happened with X this week" answer that previously required cross-referencing email, Slack, and the invoice spreadsheet. Roughly 10-15 minutes per ad-hoc client question.

### 5.4 — Fakture tab — invoice list scoped to one client

**Prerequisites:** workspace open on `Fakture`.

**Steps:**
1. The tab embeds the same invoice list as `/{orgSlug}/invoices` (same columns, same filters), pre-filtered to this client.
2. The tab subtitle reads `Sve fakture vezane za ovog klijenta — primljene i izdate.`
3. Click `Otvori punu stranicu` to escape to the full invoices route with the client filter pre-applied.
4. All the actions from workflow 4.5 (search, filter, batch verify/delete/export, sort, payment) work here.

**Behind the scenes:** Same `GET /api/v1/invoices` endpoint with `client_id` pre-set.

**Status:** Shipped.

### 5.5 — Izveštaji tab — reports plus the obligations matrix

**Prerequisites:** workspace open on `Izveštaji`. The full obligations card requires `Pravna forma` and `Sistem knjigovodstva` to be set (workflow 3.1 or 3.2).

**Steps:**
1. The `Obavezni obrasci za ovog klijenta` card appears at the top of the tab. Each row lists a form (e.g. `Kalkulacija prodajne cene`, `KEP — Knjiga evidencije prometa`, `Cenovnik`, `Popis`, `DPU — Šank lista`, `PK-1 — Pomoćna knjiga`) with a short description and a status badge.
2. The status badges read one of:
   - `Dostupno` — the form is fully shipped.
   - `Dostupno (pre-sastanak)` — the form is generated but the column structure is the pre-meeting simplified draft.
   - `Posle sastanka` — the form is unbuilt; the spec is being decided at the M20 accountant meeting.
   - `Nije obavezno` — the obligation matrix says this client does not owe this form.
   - `Nepoznato` — classification is incomplete; the card invites you to set `Pravna forma` and `Sistem knjigovodstva`.
3. Click `Otvori` on a row whose form is shipped or available pre-meeting to jump into the corresponding report.
4. Below the card, the group pills read `Opšti` / `Nabavka i prodaja` / `Upravljanje`. Click a pill to switch report families.
5. Inside `Opšti`: `Primljena roba` (received goods grouped by description), `Po dobavljačima` (spending by supplier), `Mesečni pregled` (monthly breakdown), `Poređenje cena` (price comparison across suppliers), `Troškovi` (expense summary by month).
6. Inside `Nabavka i prodaja`: `Kalkulacija` (calculation of selling price — pre-meeting columns), `RUC` (margin analysis), `Po kategorijama` (spending by category), `Dnevna evidencija` (DPU / šank lista — pre-meeting columns).
7. Inside `Upravljanje`: `Katalog` (product catalog).
8. Each report has its own filter row (`Datum od`, `Datum do`, supplier PIB filter where relevant, free-text item search). Click `Generiši` to run, `Preuzmi CSV` to export.

**Behind the scenes:** `GET /api/v1/clients/{id}/obligations` returns the matrix from `app.services.hospitality_forms.required_forms`. Each report has its own endpoint under `/api/v1/reports/*` and accepts a `client_id` query parameter that scopes the rollup to one client.

**Status:** Partial. The card itself is shipped; the *contents* of the kalkulacija and DPU reports follow simplified pre-meeting column structures. KEP, cenovnik, popis, and PK-1 are not yet generated — see section 10.

**Time saved vs Excel:** The pre-meeting reports already replace 1-2 hours per client per month of manual rollup work. The post-meeting forms will eliminate another 4-8 hours per hospitality client per month once specified.

### 5.6 — Pravila tab — per-client rules versus global rules

**Prerequisites:** workspace open on `Pravila`. The agency must have at least one rule in the library (workflow 7.1) to attach.

**Steps:**
1. The tab shows two sections: rules scoped to this client (top) and read-only global rules that also apply (below).
2. Click `Dodaj pravilo` to open a chooser of existing rules from the agency's rule library. Tick rules to attach to this client and confirm.
3. Each attached rule shows its priority, condition summary, action summary, and recent execution count. Click a rule to open it in the global rules page for editing.
4. Click the unlink icon next to a per-client rule to detach it from this client (the rule still exists globally).
5. Global rules in the lower section cannot be edited from here — they apply across the agency. Click `Otvori punu stranicu` to manage them.

**Behind the scenes:** `GET /api/v1/clients/{id}/rules` returns the attached rules. `POST /api/v1/clients/{id}/rules` and `DELETE /api/v1/clients/{id}/rules/{ruleId}` manage the attachment.

**Status:** Shipped (attachment side). Rule authoring lives under workflow 7.

---

## 6. Reports and exports

### 6.1 — Run a report

**Prerequisites:** signed in. To use the agency-wide flavor visit the report routes directly; to use the client-scoped flavor open a client workspace → `Izveštaji`.

**Steps:**
1. From the `Izveštaji` tab of any client workspace (workflow 5.5), or from the standalone reports landing inside the agency-wide view, pick a group and a report.
2. Fill the filters that apply to that report — date range, supplier PIB, item search, category.
3. Click `Generiši`.
4. Results render in a table with totals at the bottom. Empty results show `Nema podataka za prikaz`.
5. Click `Preuzmi CSV` to export the table as a CSV.

**Behind the scenes:** Each report calls its own GET endpoint under `/api/v1/reports/` (e.g. `/received-goods`, `/spending-by-supplier`, `/monthly-breakdown`, `/price-comparison`, `/expense-summary`, `/kalkulacija`, `/ruc`, `/dpu`, `/spending-by-category`). All accept an optional `client_id` for scoping.

**Status:** Shipped (general reports). Kalkulacija and DPU are shipped but under pre-meeting column structures.

**Time saved vs Excel:** 1-2 hours per report per month per client, depending on report complexity.

### 6.2 — Export invoices (XLSX, CSV, JSON)

**Prerequisites:** signed in. Select at least one verified invoice (verified invoices export cleanly; unverified ones can be force-exported with a warning).

**Steps:**
1. From `/{orgSlug}/invoices`, select invoices with the row checkboxes.
2. Click `Izvezi` in the batch action bar. The `Izvezi fakture` dialog opens.
3. Pick a `Format`: `Excel (XLSX)`, `CSV`, or `JSON`.
4. Pick a `Šablon izvoza`: `Podrazumevani (sva polja)` or any custom template the agency has created under `/{orgSlug}/templates` (workflow 6.7).
5. For CSV, pick a `Razdvajač`: `Tačka-zarez (;)`, `Zarez (,)`, or `Tab`.
6. Toggle `Uključi stavke` to include line items as nested rows (XLSX) or a separate sheet (JSON).
7. If any selected invoice is blocked from export, the dialog lists `Izvoz blokiran za sledeće fakture` and offers `Izvezi svejedno` with a warning `Podaci mogu biti nepotpuni. Nastavite na sopstvenu odgovornost.`.
8. Click `Preuzmi`. The file downloads through the browser.

**Behind the scenes:** `POST /api/v1/export` (and template-specific routes) renders the selected invoices server-side and streams the file back. Each export emits an audit log event with the actor, invoice IDs, format, and template.

**Status:** Shipped.

**Time saved vs Excel:** Replaces manual data entry into the bookkeeper's accounting software. 30 seconds per invoice saved on average.

### 6.3 — Export to MiniMax (XML)

**Prerequisites:** at least one verified invoice selected. MiniMax XML import in the destination system is configured separately by the bookkeeper.

**Steps:**
1. From `/{orgSlug}/invoices`, select invoices.
2. Click `Izvezi`. In the dialog, pick `MiniMax XML` as the format.
3. Click `Preuzmi`. A `.xml` file downloads in the MiniMax-expected schema.
4. Inside MiniMax, run the import-from-XML routine pointed at the downloaded file.

**Behind the scenes:** Same endpoint as workflow 6.2, with `format=minimax_xml`. The XML is namespaced and field-mapped against the MiniMax import schema.

**Status:** Shipped.

### 6.4 — Push to MiniMax (REST API)

**Prerequisites:** the MiniMax integration is configured and the test connection has succeeded (workflow 2.5). The plan tier must include the `MiniMax direktan uvoz` feature.

**Steps:**
1. From `/{orgSlug}/invoices`, select invoices.
2. Click `Izvezi`. In the dialog, the `Direktan uvoz u MiniMax` panel becomes available.
3. Optionally check `Automatski kreiraj kupce u MiniMax-u ako ne postoje` — if the buyer is missing in MiniMax, Saldora creates the customer card before pushing the invoice.
4. Click `Pošalji u MiniMax`. A toast shows progress: `Slanje...`.
5. The result panel `Rezultati slanja u MiniMax` lists each invoice with success or per-invoice error. The summary reads either `N faktura uspešno poslato u MiniMax` or `N uspešno, M sa greškom`.

**Behind the scenes:** Each invoice is pushed via the MiniMax REST API using the org's stored credentials. Failures are logged with the underlying MiniMax error and surfaced per-invoice; Saldora does not retry automatically.

**Status:** Shipped.

**Time saved vs Excel:** Replaces a per-invoice XLSX-import-then-fix step inside MiniMax. About 1-2 minutes per invoice.

### 6.5 — Generate an audit export for tax inspection

**Prerequisites:** signed in as admin. This view is admin-only — non-admins see `Samo administratori mogu pristupiti ovoj stranici`.

**Steps:**
1. Open `/{orgSlug}/arhiviranje` and scroll to `Izvoz za poresku inspekciju`.
2. Read the `Revizijski paket za poresku inspekciju` info panel. The archive may include up to four file types: `Registar faktura (CSV)`, `PDV pregled (XLSX)`, `Revizijski trag (CSV)`, and `Originalni dokumenti (PDF)`.
3. Pick `Datum od` and `Datum do`. The preview line `N faktura u izabranom periodu` updates as you change dates.
4. Choose which sub-archives to include:
   - `Registar faktura (CSV)` — always included.
   - `PDV pregled (XLSX)` — VAT summary grouped by rate.
   - `Revizijski trag (CSV)` — full action history. Strongly recommended for tax inspection.
   - `Originalni dokumenti (PDF)` — adds the original scans. Significantly increases archive size.
5. Optionally enter a `Razlog/referenca` such as `Poreska kontrola br. 123/2025` to identify this export in the history list.
6. Click `Generiši izvoz`. The job runs in the background; the row appears in `Istorija izvoza` with status `U obradi`, then `Spremno` when finished.
7. Click `Preuzmi` next to a ready row. The download link is valid for 30 days from generation (`Važi do {date}`).

**Behind the scenes:** `POST /api/v1/archive/generate` queues a Celery job that streams the selected pieces into a ZIP on R2. The job emits an audit-log event noting the actor, the requested date range, and the included sub-archives. The history list is `GET /api/v1/archive/history`.

**Status:** Shipped.

**Time saved vs Excel:** Replaces a multi-day scramble through email, file shares, and printouts before a tax inspection. Typical agency saves a full working day per inspection.

### 6.6 — Monthly automated archive

**Prerequisites:** signed in as admin. The org has a billing email set under `Podešavanja → Organizacija`.

**Steps:**
1. Open `/{orgSlug}/arhiviranje`. The top card `Automatski mesečni izvoz` describes the schedule and the contents.
2. Toggle `Automatski izvoz aktivan` to enable or disable.
3. Toggle `Uključi originalna PDF dokumenta` to include the full document PDFs in the monthly archive.
4. The `Email za dostavu` row shows where the archive will be sent. To change it, follow the hint `Promenite u Podešavanja → Organizacija`.
5. Saldora runs the export at 03:00 on the 1st of each month and emails the resulting ZIP. Each delivery appears in `Istorija dostave` with status `Dostavljeno`, `Neuspešno`, or `Preskočeno`.
6. To test the schedule on demand, scroll to `Izvezi odmah`, pick a period, and click `Izvezi`. A toast confirms `Arhiva se generiše u pozadini...`.

**Behind the scenes:** A scheduled Celery beat task runs on the 1st of each month, iterates every active organization, and calls the same generator as workflow 6.5 with the configured sub-archives. The email goes through SendGrid.

**Status:** Shipped.

**Time saved vs Excel:** Eliminates the monthly closeout-and-archive ritual. About 1-2 hours per month per organization.

### 6.7 — Manage export templates

**Prerequisites:** signed in as admin or manager.

**Steps:**
1. Open `/{orgSlug}/templates`.
2. To create a new template, click `Novi šablon`.
3. Fill in `Naziv šablona` (e.g. *Mesečni izveštaj za MiniMax*) and an optional `Opis`.
4. In `Polja za izvoz`, drag fields from `Dostupna polja` into `Odabrana polja`. Reorder with the up/down chevrons. Optionally set a `Prilagođeni naziv kolone` for any field to rename it in the output.
5. In `Podržani formati`, tick which formats this template is valid for (XLSX, CSV, JSON).
6. Click `Kreiraj šablon`. The template appears in the list and is now selectable in the export dialog (workflow 6.2).
7. Click `Izmeni` on any custom template to update it, or `Izbriši` to remove it. System templates have a `Sistemski` badge and are read-only.

**Behind the scenes:** `POST/PATCH/DELETE /api/v1/export/templates`. Custom templates are scoped to the organization.

**Status:** Shipped.

### 6.8 — Generate KPR / KIR books for a PDV period

**Prerequisites:** the invoices for the period are verified. Unverified invoices do not appear in books.

**Steps:**
1. Open `/{orgSlug}/pdv-knjige`.
2. Choose `Tip knjige`: `KPR - Primljeni računi` (received invoices) or `KIR - Izdati računi` (issued invoices).
3. Choose `Mesec` and `Godina`.
4. Choose `Format`: XLSX (recommended), CSV, or PDF.
5. Optionally narrow to one `Klijent`; the default is `Svi klijenti`.
6. Click `Generiši`. The book downloads. The total row at the bottom maps directly to PP-PDV form fields — the bookkeeper transcribes the totals into the tax return.

**Behind the scenes:** `GET /api/v1/reports/pdv-books` aggregates verified invoices in the period, splits by VAT rate, and returns either a formatted XLSX or a CSV/PDF rendering.

**Status:** Shipped.

**Time saved vs Excel:** Replaces a per-period rebuild of KPR/KIR from raw invoice data. About 2-4 hours per period.

---

## 7. Rules workflows

### 7.1 — Create a global rule

**Prerequisites:** signed in as admin or manager.

**Steps:**
1. Open `/{orgSlug}/rules`.
2. Click `Novo pravilo`, or `Koristi šablon` to pick from the gallery of pre-built rules.
3. Fill in `Naziv pravila`, an optional `Opis`, and a `Prioritet` (lower number = higher priority).
4. Pick a `Tip pravila`: `Konto` (assign a konto), `PDV tretman` (set VAT treatment), `Auto-odobri` (auto-verify when matched), `Pregled` (flag for review), `Tip dokumenta` (override extracted document type), or `Polje` (set a custom field).
5. Build conditions: pick `SVE uslovi` or `BILO KOJI`, then click `Dodaj uslov`. Each condition has a field (grouped by `Prodavac`, `Kupac`, `Iznosi`, `Stavke`, `Dokument`, `Sistem`), an operator (`jednako`, `sadrži`, `regex`, `veće od`, `između`, `u listi`, `nije postavljeno`, etc.), and a value.
6. Build actions: click `Dodaj akciju`. Each action depends on the rule type — e.g. for `Konto`, fill `Strana` (`Duguje` or `Potražuje`), `Broj konta`, `Opis konta`.
7. Click `Kreiraj pravilo`. The rule appears in the list with an `Aktivno` toggle.

**Behind the scenes:** `POST /api/v1/rules` writes the rule. The rule engine evaluates active rules in priority order on every invoice verification.

**Status:** Shipped.

**Time saved vs Excel:** A 5-minute rule replaces a recurring per-invoice decision. Compounding payoff over months.

### 7.2 — Scope an existing rule to a client

See workflow 5.6. Rules are authored globally and then attached per client via the client workspace `Pravila` tab.

### 7.3 — View rule execution history

**Prerequisites:** the rule has fired at least once.

**Steps:**
1. Open `/{orgSlug}/rules`.
2. Click the `Istorija` icon next to any rule.
3. The history view lists each execution: `Izvršeno` timestamp, `Trajanje` (milliseconds), the linked `Faktura`, `Uslovi` that matched, and `Primenjene akcije`.
4. Click any row to jump to the invoice that triggered the rule.

**Behind the scenes:** `GET /api/v1/rules/{id}/executions` returns the execution log.

**Status:** Shipped.

### 7.4 — Toggle a rule on or off

**Prerequisites:** the rule exists.

**Steps:**
1. Open `/{orgSlug}/rules`.
2. Click the `Aktivno` toggle on the rule's card. The status flips to `Neaktivno` immediately.
3. From this moment on the rule stops firing. **Past effects are not reversed** — if the rule already wrote a konto onto an invoice, that konto remains. To undo, edit the invoice or apply a corrective rule.

**Behind the scenes:** `PATCH /api/v1/rules/{id}` with `is_active=false`. The rule remains in the catalog and can be re-enabled at any time.

**Status:** Shipped.

---

## 8. Subscription and billing workflows

### 8.1 — View current plan and invoice quota

**Prerequisites:** signed in as admin. The page is admin-only.

**Steps:**
1. Open `/{orgSlug}/billing`.
2. The `Trenutni plan` card shows the plan name (`Starter`, `Pro`, `Agency`, or `Besplatni`) and status (`Aktivna`, `Kašnjenje u plaćanju`, `Otkazana`, `Pauzirana`).
3. The `Potrošnja ovog meseca` card shows `N od M faktura` and a percentage bar. Unlimited tiers show `N faktura (neograničeno)`.
4. Below, the `Dostupni planovi` grid lists every plan with features and overage rate. The current plan has a `Vaš plan` badge.

**Behind the scenes:** `GET /api/v1/billing/subscription` and `GET /api/v1/billing/usage`.

**Status:** Shipped (view side).

### 8.2 — Request a plan upgrade (currently manual)

**Prerequisites:** signed in as admin.

**Steps:**
1. Open `/{orgSlug}/billing`.
2. Find the desired plan in the `Dostupni planovi` grid and click `Nadogradi` or `Kontaktirajte nas`.
3. The dialog shows `Uskoro dostupno — Integracija sa platnim sistemom je u pripremi. Biće dostupna uskoro.` with a contact email.
4. Email the contact address with your org slug and target plan. A Saldora admin runs `scripts/admin_orgs.py` to flip the plan (workflow 9.1).

**Behind the scenes:** All activations are manual today — the agency receives a Saldora invoice, pays by bank transfer, and `scripts/admin_orgs.py` extends the subscription period. The UI is in place so it can switch from a contact-form CTA to a self-serve checkout if/when an automated billing rail is adopted.

**Status:** Partial (display is shipped; self-serve checkout is coming).

### 8.3 — Cancel a paid subscription

**Prerequisites:** signed in as admin. Plan is on a paid tier.

**Steps:**
1. Open `/{orgSlug}/billing`.
2. Click `Otkaži pretplatu`.
3. Confirm in the dialog `Da li ste sigurni da želite da otkažete pretplatu? Bićete prebačeni na besplatni plan.`.
4. A toast confirms `Pretplata je uspešno otkazana`.

**Behind the scenes:** Same caveat as 8.2 — cancellations are tracked in the database and applied at the next billing cycle by Saldora admin action via `scripts/admin_orgs.py`.

**Status:** Partial.

---

## 9. Admin (Saldora-side) workflows

These three workflows are run by the Saldora team, not by the agency. They are documented here so the agency knows what to expect after submitting a registration or upgrade request, and so engineers reading this doc can find the operational entry points.

### 9.1 — Approve a pending registration via `scripts/admin_orgs.py`

**Prerequisites:** SSH access to the production server or a local environment with database credentials.

**Steps:**
1. Run `python scripts/admin_orgs.py` in the API project root. The script is interactive.
2. Choose the environment (`local`, `staging`, or `prod`).
3. The script lists every organization with `id`, `name`, `slug`, `subscription_status`, and the registrant email. Pick the org by its number.
4. Choose a new `subscription_status` from `active`, `trial`, `pending`, or `canceled`. Optionally adjust the plan tier.
5. Confirm. The script writes the change and prints a one-line summary.
6. The agency owner clicks `Proveri status` on the `/awaiting-approval` page (workflow 1.1) and is redirected into the app.

**Behind the scenes:** Plain `UPDATE` statements against `organizations`. The script is designed to be safer than raw SQL — it shows the before/after and requires explicit confirmation.

**Status:** Shipped.

### 9.2 — Update the prod Alembic head after deploy

**Prerequisites:** SSH access to prod; the new code is already deployed.

**Steps:**
1. Follow `../dev/DEPLOYMENT.md` for the canonical SSH command sequence. The summary is: connect, cd into the API directory, run the Alembic upgrade command in the venv.
2. Verify with `alembic current` that the head matches the latest migration in the repo.

**Status:** Shipped (operational only; see DEPLOYMENT.md).

### 9.3 — Trigger a manual backup

**Prerequisites:** SSH access to prod.

**Steps:**
1. Follow `../dev/DEPLOYMENT.md`. A manual backup is required before destructive migrations or before pinning a known-good restore point.
2. The backup script writes a timestamped dump to the configured S3 bucket.

**Status:** Shipped (operational only).

---

## 10. What's coming (pointer, not roadmap)

The full M20 agenda lives in `../product/M20_accountant_meeting_agenda.md`. The short version is that the following surfaces are visible in today's product but are not yet feature-complete:

| Area | Today | What changes after the M20 meeting |
| --- | --- | --- |
| Kalkulacija report | Shipped pre-meeting with simplified columns. Lives under `Izveštaji → Nabavka i prodaja → Kalkulacija`. | The accountant validates each of the 13 prescribed columns; we refit the report and lock the column spec. |
| DPU (Šank lista) | Shipped pre-meeting with simplified columns. Lives under `Izveštaji → Nabavka i prodaja → Dnevna evidencija`. | The accountant validates each of the 9 prescribed columns and the daily-popis UX is decided (manual data entry, bar-count photo upload, or fiscal-POS sync). |
| KEP — Knjiga evidencije prometa | Not generated yet. The obligation row shows `Posle sastanka`. | The accountant walks through producing a KEP entry for a real client; we decide between a Z-report upload widget or a fiscal-POS ingestion path and ship the form generator. |
| Cenovnik | Not generated yet. Obligation row shows `Posle sastanka`. | Likely a thin generator — Word-like layout or POS export. Spec decided at the meeting. |
| Popis | Not generated yet. Obligation row shows `Posle sastanka`. | Decision pending on whether this is annual-only or recurring monthly; UX likely centers on a stock-count entry screen with valuation. |
| PK-1 — Pomoćna knjiga | Not generated yet. Obligation row shows `Posle sastanka`. | The link spec — kalkulacija columns 6+7 → PK-1 col 12; col 8 → PK-1 col 14; col 11 → PK-1 col 15; col 12 → PK-1 col 16 — is confirmed with the accountant and PK-1 is generated from existing data. |
| Self-serve checkout (automated billing) | Not wired up. The billing page shows a contact-us CTA. | A future Serbia-compatible billing rail is adopted (see `architecture.md` §3.3). |
| In-app support / chat | Not implemented. | Likely a Crisp or Intercom widget on every authenticated page. |
| Email ingestion (forward to Saldora) | Not implemented. | A per-org forwarding address (`{slug}@inbox.saldora.rs`) that auto-uploads attachments. |

If you are reading this and you are not the Saldora team: please do not plan around any row in this table — the M20 meeting outcomes will determine timing and shape.

---

## 11. Appendix: glossary references

This document deliberately does not repeat the glossary. For unfamiliar accounting terms — `kalkulacija`, `KEP`, `KPR`, `KIR`, `DPU`, `PK-1`, `popis`, `cenovnik`, `dvojno` vs `prosto knjigovodstvo`, `PIB`, `MB`, `paušalac`, `preduzetnik`, `DOO`, `PP-PDV`, `ZZPL`, `MiniMax` — see `../product/SRS.md §2` (Definitions) and `../product/SRS_sr_simple.md`. The legal-basis citations behind the obligation matrix live in `../product/SRS.md §4.19` and `../product/M20_accountant_meeting_agenda.md`.

For UI translations themselves, the canonical source is `apps/web/messages/sr-Latn.json`. Every label cited above resolves there.

For route-to-page mapping the canonical source is the directory tree under `apps/web/src/app/(app)/[orgSlug]/`. Every route mentioned above corresponds to a real `page.tsx` in that tree as of the current branch.
