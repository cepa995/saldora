# Saldora: Strategic Positioning and UX Redesign

## Executive Summary

Saldora is an intelligence layer for Serbian accounting agencies that receive paper invoices at scale. The target is narrower than previously scoped: **agencies whose clients are hospitality businesses** — restaurants, cafes, bars, fast food, catering — because that is the segment where paper invoices with many line items still dominate and where SEF (eFaktura) is years away from covering what the accountant actually receives daily.

For everyone else, SEF is already or soon will be the delivery channel. Competing with SEF's coverage for VAT-paying B2B invoices is a losing battle. Competing on the edge SEF does not cover — paper invoices, receipts from open markets, supplier deliveries from small producers, beverage distributor invoices with dozens of SKUs — is a defensible wedge with a clear buyer and a specific workflow.

The differentiator is twofold: OCR that extracts line items from real paper invoices accurately, and generation of legally-required Serbian hospitality forms (kalkulacije, šank lista, cenovnik, KEP, popis) directly from the extracted line-item data. MiniMax, Pantheon, and other incumbents handle the general ledger for these businesses but do not handle the upstream paper-to-digital pipeline, and the legal-forms layer is painful enough that most agencies generate them by hand in Excel.

Saldora does not replace MiniMax. Saldora owns the pipeline from paper invoice in, to fully-classified legally-correct data out, and hands that data to MiniMax for the general ledger and financial reporting.

---

## Part One: Why Hospitality, Why Paper

### What SEF does and does not cover

Serbian B2B e-invoicing via SEF has been mandatory for VAT payers since January 2023. Amendments effective April 2026 extend it to internal invoices, reverse-charge self-invoices, retail with corporate cardholders, and electronic delivery notes.

What SEF does not cover, and probably will not soon:
- Invoices from **paušalci** (flat-rate entrepreneurs) to VAT payers — paušalci are outside the VAT system and have no SEF obligation
- Small producers, farms, and open-market suppliers — many operate cash-only or paper-only
- **Fiscal receipts** for small purchases
- Invoices from sole proprietors who have not adopted SEF even when technically required (enforcement is thin)
- Cross-border invoices from non-Serbian suppliers
- Delivery notes from distributors that still arrive on paper

A hospitality business receives all of the above in volume. A single restaurant typically gets twenty to forty invoices a month, many with ten to fifty line items each (beverages, dry goods, produce, meat, cleaning supplies, equipment maintenance). The accountant handling that restaurant on behalf of an agency spends hours manually typing line items into accounting software or Excel, then generates several legally-required forms from that data, also often in Excel.

### The hospitality-specific legal burden

Every hospitality business in Serbia is legally required to maintain specific records beyond the standard general-ledger entries that apply to all businesses:

- **Kalkulacije** (calculations): a per-product document showing cost price → markup → VAT → sale price. Required whenever a new product is added to the menu or a supplier price changes.
- **Šank lista** (bar list): periodic inventory of beverages and consumables at the bar, showing received goods, sold goods, and closing stock.
- **Cenovnik** (price list): the current menu / price list, which must match what is charged and must be publicly displayed.
- **Knjiga evidencije prometa (KEP)**: the trade records book — a ledger recording all goods received and all sales.
- **Popis** (inventory count): periodic physical inventory with valuation at period end.

All of these can be generated from structured data that the OCR already produces: line items from incoming invoices plus product identities plus per-client markup rules. Today, agencies generate them by hand. This is the wedge.

### Why the buyer is the agency, not the restaurant

Small hospitality businesses do not shop for accounting software — their agency does the accounting. Selling direct to restaurants is slow, low-ARPU, and support-intensive. Selling to agencies that handle thirty or forty restaurants each is a standard B2B motion with a clear buyer, a clear decision process, and clear revenue per deal.

The agency's incentive is simple: time. A competent agency bookkeeper spends most of the month on invoice data entry for hospitality clients. Every hour saved on paper-invoice data entry is an hour that can bill out to another client. A tool that cuts that time in half is a straightforward ROI conversation.

---

## Part Two: What Stays, What Changes

### Load-bearing foundations that remain

The OCR pipeline (dots.ocr primary, easyocr fallback), the Anthropic-based field extraction with confidence scoring, the line-item extraction and normalization, the product catalog with pg_trgm fuzzy matching, the client management data model, the MiniMax integration, the NBS exchange-rate service, the Paddle billing integration, the rules engine, the AccountingIntent layer, the audit log, the export template system, the archive exports, the ZZPL compliance flows — all of this continues to work as built. None of it was misaligned with hospitality agencies; if anything the hospitality case is more line-item-heavy than the generic case, so the pipeline gets better signal from richer data.

The product catalog in particular is a load-bearing foundation for the legal forms. Every line item the OCR extracts normalizes to a product identity via pg_trgm. Every product that a hospitality client sells needs a kalkulacija. The path from extracted line item → product identity → kalkulacija is the core value chain.

### Paušalci: dropped

The paušal module that was partially built (M14.1 through M14.8, some merged to main and subsequently reverted, some closed without merging) is dropped. Paušalci outside the agency's own hospitality portfolio are not the target. MiniMax's dedicated paušal app handles that segment well enough; competing there is a multi-year battle against entrenched software and a market we cannot win.

This does mean the `direction` field on invoices, `client_type` on clients, the `customers` table, the `invoice_counters` table, the paušal-specific routers, and the KPO ledger are all gone from the codebase. The strategy doc that referenced them (M14–M18 in the old implementation plan) is superseded by this document.

### Legal forms: the new center

What was previously a vague "reports / intelligence" offering gets sharpened into a concrete set of legally-required Serbian hospitality forms. The exact set and the exact column structure per form will be determined by sitting with a real accountant who handles restaurants, not by interpreting the law from the outside. Until that meeting happens, the scope of the forms work remains deliberately unspecified.

What is already certain:
- The forms are client-scoped, not agency-scoped — every form is about one specific hospitality business.
- The data to populate them comes from the existing OCR + product catalog.
- They live in a Reports / Izveštaji section within each client's workspace, not as a global sidebar entry.

### Client-first UI: the structural change

The current app is feature-indexed: the sidebar has `Fakture`, `Klijenti`, `Izveštaji`, `Pravila`, etc. Every one of these is a global list that you have to filter by client. An accountant handling thirty restaurants spends their day filtering global lists thirty times over, switching context every few minutes between feature pages for the same client.

The new structure inverts this. The primary axis is the client. An accountant picks a restaurant, lands on that restaurant's workspace, and everything about that restaurant — invoices, reports, rules, timeline of events — lives in tabs within that workspace. When they are done with that restaurant, they move to the next one.

Agency-level operations (archiving, rule templates, product catalog, settings, billing) stay outside the per-client workspace because they legitimately are not about one specific client. The sidebar after the redesign has two sections: client workspace (the main surface) and agency operations (utilities).

---

## Part Three: The Client-First UI

### Three surfaces

**Portfolio view (`/pregled`)** — agency-wide home. A grid of all the agency's clients, each showing health indicators: how many invoices are pending review, how many are blocked, how many forms are overdue, when they were last worked on. Click a client → open that client's workspace.

**Client workspace (`/klijenti/{id}`)** — the single-page surface for one client. Header with the client's name, PIB, activity details. Tabs below: Timeline (default), Fakture, Izveštaji, Pravila, and others as they are added. Every tab is pre-scoped to this one client; no filter UI is needed for client selection.

**Timeline** (inside client workspace) — a chronological event feed showing everything that has happened for this client during the current period. Invoice uploaded, invoice verified, AccountingIntent classified, rule fired, export to MiniMax completed, form generated. Each event shows its type, timestamp, and a one-line description, clickable for detail. Filterable by event type.

### Coexistence versus replacement

Because Saldora has not yet deployed to paying customers, there is no user population to protect during the transition. The redesign will ship as a replacement in a single branch, not as a parallel surface that coexists with the old UI indefinitely. Old feature pages are reachable from within the new shell during development only — as a safety net to ensure no feature is lost by accident — and removed before the branch merges.

The net effect: one day the app looks the way it does now; the next day it looks client-first. No long migration, no dual sidebars, no "new way" vs "old way" choice for the user.

### Tab structure within the client workspace

At merge time, `/klijenti/{id}` has these tabs:

- **Timeline** (default) — all events for this client, current period
- **Fakture** — invoices for this client, with the existing list's filters and detail view
- **Izveštaji** — the reports page, pre-filtered to this client (content to be expanded post-accountant-meeting into hospitality forms)
- **Pravila** — rules scoped to this client, plus a create-rule CTA that pre-fills the client filter

As new capabilities arrive, new tabs get added. The structure is extensible: a tab is a routable section within the client workspace.

### Sidebar structure after merge

```
— Client workspace —
🏠 Pregled portfelja          (portfolio view — default home)
👥 Klijenti                   (flat list, quick jump to a client workspace)

— Agency operations —
⚙️ Pravila                    (global view — edit org-wide rules, browse client-scoped)
📦 Arhiviranje                (period archives for tax inspection)
📁 Katalog proizvoda          (product identities, shared across clients)

— Utilities —
📊 Dashboard                  (global stats, kept for now)
🔧 Podešavanja
👤 Team
💳 Billing
```

No top-level `Fakture` or `Izveštaji` entries — both are client-scoped and live inside the per-client workspace.

### Event log: the mechanism behind the timeline

The timeline renders entries from a new `client_events` append-only table. Events are written whenever something happens that touches a client: an invoice arrives, a verification completes, a rule fires, a form is generated. Backfilling existing data at deploy time populates timelines for clients with prior activity.

Event types at launch:
- `invoice_uploaded`
- `invoice_verified`
- `invoice_exported`
- `accounting_intent_classified`
- `rule_fired`
- `client_assigned`

Additional event types arrive as new capabilities ship: `form_generated`, `period_closed`, etc. The data model is stable; new types are just new rows.

---

## Part Four: Deferred Until the Accountant Meeting

These are known-known gaps in scope that cannot be built well without first-hand agency input:

- **Hospitality legal forms** — kalkulacije, šank lista, cenovnik, KEP, popis. Exact required columns, formulas, audit-trail requirements, and paper-format conventions will be drafted from the meeting notes, not inferred.
- **Close checklist** — the task spine that drives each period to completion. Without knowing what a complete hospitality-client month actually involves, any checklist we build now is guesswork.
- **Period entity with close/lock semantics** — ties directly to the checklist and to popis. Deferred until the checklist is real.
- **Product sale price / markup** — prerequisite data for kalkulacije. The schema change is trivial; the UI to manage it depends on how accountants actually work with markups.
- **Fiscal receipt integration** — may or may not be needed for KEP depending on how the agency receives daily sales data. Scope unknown until the meeting.

What the meeting needs to produce, in order of priority:
1. The exact set of forms an agency is legally required to produce for a hospitality client, and how often.
2. For each form, the exact columns / fields / formulas required by law.
3. The source data for each form (purchase-side only, or does it need sales data too?).
4. The monthly close workflow, step by step, as the accountant actually performs it today.

---

## Part Five: What We Do Not Build

A few things that were previously under consideration and are now explicitly out of scope:

- **Client portal** — end clients submitting documents directly. Dropped. Hospitality owners are not sophisticated portal users; the agency will continue to receive documents by email, WhatsApp, and paper. Saldora does not touch that channel.
- **Proactive compliance watchdog** — scheduled rule evaluation producing alerts. The rules engine continues to exist and fires on events; a scheduled watchdog layer would be paušal-era thinking and does not serve hospitality.
- **Foreign invoice reverse-charge module as a standalone feature** — the existing NBS conversion and AccountingIntent handle foreign invoices adequately for a hospitality context (which rarely involves complex reverse-charge scenarios). Revisit if hospitality agencies report it as a pain.
- **Bank reconciliation, payment tracking, general-ledger operations** — permanently out of scope. MiniMax handles these. Saldora is the pipeline, not the books.

---

## Part Six: Sales Positioning

The pitch to an agency owner handling hospitality clients:

> You spend thirty to fifty hours a month typing paper invoices from your restaurant and cafe clients. You then generate kalkulacije, šank liste, and KEP entries by hand in Excel for each of those clients. MiniMax does not help with either. Saldora's OCR reads the paper invoices with line-item accuracy, our product catalog normalizes names across suppliers and spellings, and we generate the legally-required hospitality forms directly from that data. You keep MiniMax for the general ledger. We give you back the thirty hours.

Narrow, concrete, quantified. The buyer knows exactly what they are getting because the pain is specific and the incumbents are named. The sale does not require displacing a system of record.

---

## Part Seven: Guiding Principles

**Serve agencies with hospitality portfolios, not end clients and not general B2B.** Every product decision tests against this. If a feature is equally useful for a non-hospitality client, it is additive; if it is only useful for non-hospitality, it is out of scope.

**OCR + legal forms is the wedge.** Not OCR alone; not intelligence-layer-for-everything. The two together, tied to hospitality.

**MiniMax is the books; Saldora is the pipeline.** Every flow ends with a handoff to MiniMax. We do not do general-ledger postings.

**Product catalog is a first-class entity.** Every line item maps to a product. Forms and reports derive from products. Treat the catalog as a core data asset, not an auxiliary lookup.

**Client-first, not feature-first.** The UI reflects how agency staff work: pick a client, do everything for that client, move on. Features are tabs within the client workspace, not top-level destinations.

**Agency-level operations stay outside the per-client workspace.** Rules at org scope, archiving, product catalog, billing — these are the agency running itself, not one client.

**Legal forms are generated once, derived from structured data.** No manual Excel. If we cannot derive it, we cannot ship it; if we can derive it, it ships automatically.

**Ship replacements, not parallels.** Without a live user base we do not need coexistence. One branch, one cutover.

**Wait for the accountant meeting before specifying forms.** No legal form gets built from a reading of the law; every form gets built from watching an accountant do it by hand.

---

## Closing

The path is narrower than before and that is its strength. One buyer (accounting agencies with hospitality portfolios). One wedge (OCR on paper invoices with many line items). One differentiator (legally-required hospitality forms generated from the extracted data). One positioning (pipeline into MiniMax, not a replacement for it).

The client-first UI redesign is the immediate structural work because it is additive regardless of what the accountant meeting reveals about forms. The forms themselves wait for the meeting, because the cost of specifying them wrong is higher than the cost of waiting.

Everything that has been built and stays built continues to work as-is. Everything that was paušalci-specific is gone. Everything about hospitality forms is deliberately unwritten until we watch someone do it.

That is the product worth building now.
