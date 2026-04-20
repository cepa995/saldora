# Saldora Implementation Plan

Companion to [`saldora-strategy-and-ux-redesign.md`](./saldora-strategy-and-ux-redesign.md). This document sequences the strategic repositioning into concrete milestones and issues.

---

## Strategic Adjustments

A few refinements to the suggestions made alongside this plan:

1. **Paušal module ships with full functionality from day one.** No read-only intermediate. Excel import is available as an optional convenience, not as the primary flow. Rationale: every agency organizes Excel differently, building a universal importer is harder than building the module properly.

2. **Pricing is tiered, not per-paušalac.** Example structure:
   - **Pro**: 1,500 invoices (OCR + AccountingIntent) + 20 paušalci clients — 14,999 RSD/mo
   - **Agency**: 3,000 invoices + unlimited paušalci — 24,999 RSD/mo
   - **Enterprise**: custom
   This is simpler for the buyer and avoids per-seat friction.

3. **No MiniMax partnership / certification.** Integration stays technical. Avoids bureaucratic drag.

4. **SEF integration as a data source** (vs. SEF being the threat). Ingest e-invoices directly from SEF API and run the full AccountingIntent pipeline on them. Turns SEF from competition into distribution.

5. **Public Serbian tax calendar as SEO / lead gen.** Free widget, builds reputation, maintained automatically.

6. **Rule template marketplace.** Public templates for rules engine — restaurants, IT services, retail. Network effect moat.

7. **Strip "OCR" from marketing.** All user-facing copy talks about intelligence, classification, compliance — not OCR.

8. **Agency-referral sales motion.** Pilot agencies earn commission for peer referrals. SMB go-to-market default.

---

## Sequenced Milestones

The sequencing is chosen so each milestone builds on the prior one, and each can ship independently with real customer value.

### M14 — Paušal module (the wedge)

The most concrete, most defensible, most underexploited pain point in Serbian accounting. Every agency has 20-50 paušalci clients tracked in Excel today.

**Scope:** client_type + direction data model, KPO ledger, revenue tracking, outgoing invoice issuance, PU rešenje OCR, paušal calendar, per-client and portfolio views.

**Issues:**
- 14.1 — Extend data model: `client_type` on clients, `direction` on invoices (+ migration)
- 14.2 — KPO ledger service and API (CRUD + auto-population from outgoing invoices)
- 14.3 — Revenue tracking and threshold alerts (6M RSD paušal status, 8M RSD PDV threshold)
- 14.4 — Outgoing invoice issuance (sequential numbering + PDF generation)
- 14.5 — PU rešenje OCR (extract monthly doprinosi + quarterly paušalni porez)
- 14.6 — Paušal tax calendar with QR payment codes
- 14.7 — Paušal client dashboard (frontend)
- 14.8 — Agency paušalci portfolio view (frontend)
- 14.9 — Optional Excel import for historical KPO data
- 14.10 — Paušal module tests

### M15 — Foreign invoice reverse-charge

Extends AccountingIntent with the accounting logic for foreign suppliers. High-value, currently manual work with high error rates.

**Issues:**
- 15.1 — Extend AccountingIntent classifier for foreign invoices
- 15.2 — Multi-language foreign VAT recognition (MwSt, IVA, TVA, BTW, etc.)
- 15.3 — Reverse-charge self-assessment service
- 15.4 — Internal PDV document generator (*interni obračun PDV*)
- 15.5 — JCI (customs declaration) matching to supplier invoice
- 15.6 — Withholding tax (*porez po odbitku*) per country + DTA rules
- 15.7 — Foreign invoice tests

### M16 — Client portal

The structural expansion that raises switching costs and improves data quality at source. Auth is the risky part — must be done carefully.

**Issues:**
- 16.1 — New user role `client_portal_user` with scoped data access
- 16.2 — Portal invitation flow (one-time token)
- 16.3 — Portal authentication and session separation from agency auth
- 16.4 — Mobile-first document submission (camera capture, drag-drop)
- 16.5 — End-client dashboard (own documents, status, KPO for paušalci)
- 16.6 — Self-service invoice issuance for paušalci in portal
- 16.7 — Portal notifications (in-app + email fallback)
- 16.8 — Security review of role boundaries and data scoping
- 16.9 — Portal tests

### M17 — Client-first UI redesign

Reorganizes the whole experience around the per-client workflow. Runs in parallel with the existing feature-indexed UI during transition.

**Issues:**
- 17.1 — Period entity with close/lock semantics (+ migration)
- 17.2 — Client view (single-page workspace)
- 17.3 — Timeline: event log data model + API
- 17.4 — Timeline: frontend with filtering by type/status
- 17.5 — Close checklist: per client-type templates
- 17.6 — Portfolio view (agency home)
- 17.7 — Dual-UI migration path (run old + new in parallel, gradual cutover)
- 17.8 — UI redesign tests

### M18 — Compliance watchdog

Extends the existing rules engine with scheduled evaluation. Smallest milestone because the foundation already exists.

**Issues:**
- 18.1 — Scheduled rule evaluation engine (daily cron)
- 18.2 — Built-in compliance rules (PDV deadlines, revenue limits, doprinosi)
- 18.3 — Ambient alerts in timeline and client header
- 18.4 — Portfolio-wide alert aggregation
- 18.5 — Law citations and auto-update on regulation changes
- 18.6 — Watchdog tests

---

## Suggested out-of-milestone work

These don't belong to any single milestone but are worth doing in parallel:

- **SEF ingestion** — could slot into M15 or be its own M19
- **Public tax calendar widget** — marketing/SEO, lightweight
- **Rule template marketplace** — extends existing rules engine, after M14 ships
- **Pricing page update** — reflects the new tiered plans, should ship with M14

---

## Sequencing principles

1. **Paušal first** because it's the most concrete pain with the smallest scope.
2. **Foreign invoices second** because it's a natural extension of AccountingIntent once paušal is proven.
3. **Portal third** because paušalci are the obvious first portal users — don't build the portal without paušal customers asking for it.
4. **UI redesign fourth** because redesigning containers before you have enough new features to fill them is building empty rooms.
5. **Watchdog fifth** because it's small, leverages existing infrastructure, and benefits most from having all the other features to monitor.
