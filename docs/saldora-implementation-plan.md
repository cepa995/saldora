# Saldora Implementation Plan

Companion to [`saldora-strategy-and-ux-redesign.md`](./saldora-strategy-and-ux-redesign.md). This document sequences the strategic repositioning into concrete milestones and issues.

---

## Status

- **M14 (Paušal Module)** — **dropped**, closed. Paušalci are not the target market.
- **M15 (Foreign Invoice Reverse-Charge)** — **deferred** indefinitely. Revisit only if hospitality agencies report it as a pain.
- **M16 (Client Portal)** — **dropped**. End clients are not the buyer; agency remains the sole user class.
- **M17 (Client-First UI Redesign)** — **active**. Renumbered / renamed below to reflect hospitality thesis.
- **M18 (Compliance Watchdog)** — **dropped**.

---

## Active milestone

### M19 — Client-First UI

Reorganise the app around the client axis. Introduces the portfolio view, per-client workspace, timeline event log, and re-homes existing client-scoped features as tabs within the workspace. Agency-level operations remain as sidebar utilities.

**Shipping model:** single feature branch that fully replaces the existing feature-indexed UI at merge time. No live coexistence. Existing feature pages are reachable from within the new shell during development only, as a completeness-check safety net; they are removed before the branch merges.

**Scope of issues** (each independently mergeable to the feature branch):

- **19.1 — Event log data model and backfill.** New `client_events` table (append-only). Event emitters wired into the existing write sites: invoice upload, verify, export, accounting-intent classification, rule execution, client assignment. Backfill script populates historical events from existing tables (audit log, correction log, invoices) so timelines are not empty at deploy time. `GET /api/v1/clients/{id}/events?period=YYYY-MM` endpoint.

- **19.2 — Client workspace shell.** New route `/klijenti/{id}` with the header (name, PIB, activity details, month navigation). Tabs below as an extensible structure. Default tab is Timeline; the rest render placeholders that link to the existing feature pages until each is migrated. No sidebar changes yet — this is accessible only via deep link for now.

- **19.3 — Timeline view.** The default tab inside the client workspace. Renders events from `GET /clients/{id}/events`, grouped by day. Event type icons and filters. Clicking an event opens the detail for the underlying entity (invoice, rule execution, etc.).

- **19.4 — Fakture tab.** Embed the existing invoice list component into the client workspace, pre-scoped to the current client. Remove the client-filter control from the embedded version; keep all other filters.

- **19.5 — Izveštaji tab.** Embed the existing reports page into the client workspace, pre-scoped to the current client. Note: the reports themselves are minimally useful today; new hospitality forms land here in a future milestone post-accountant-meeting.

- **19.6 — Pravila tab.** Tab inside the client workspace showing rules scoped to this client. "Create rule for this client" CTA pre-fills the client filter. The existing global `/pravila` page stays as an agency-level sidebar entry for org-wide rules.

- **19.7 — Portfolio view.** New route `/pregled` — the agency-wide home. Grid of clients with today's health indicators (invoices pending review, invoices blocked, activity recency). Each card clicks through to the client workspace. Designed so new indicator types plug in as data lights up.

- **19.8 — Sidebar replacement.** Restructure the sidebar into two sections: Client workspace (Pregled, Klijenti list), Agency operations (Pravila, Arhiviranje, Katalog proizvoda, Dashboard). Remove top-level `Fakture` and `Izveštaji` entries. Update `i18n` accordingly.

- **19.9 — Client list page redesign.** Existing `/klijenti` becomes a quick-jump list — rows link to `/klijenti/{id}`. Keeps existing CRUD operations. No major visual change beyond a prominent "Otvori radnu tablu" affordance per row.

- **19.10 — End-to-end verification and old-page cleanup.** Run the pre-written end-to-end test plan against the feature branch (upload invoice, verify, edit line items, export to MiniMax, create client, assign invoice, every existing report, every existing rule operation, archiving, etc.). Remove the safety-net links to old feature pages. Delete / redirect any now-orphan routes.

- **19.11 — Milestone tests.** Integration tests for the new event log, portfolio endpoint, client workspace tab routing, and the timeline API. End-to-end smoke test for the primary flow (upload → verify → timeline event visible).

---

## Deferred milestones

### M20 — Hospitality Legal Forms (post-accountant-meeting)

Placeholder. Scope specified after the agency meeting produces a requirements document for the forms (kalkulacije, šank lista, cenovnik, KEP, popis). At minimum:

- Data model additions (e.g., product markup per client).
- Form generators (one per legal form).
- Tab additions within the Izveštaji surface of the client workspace.
- Export templates (PDF at minimum; Excel likely also).

No issues created until the meeting output exists.

### M21 — Close Checklist and Period Semantics (post-M20)

Placeholder. The checklist content is determined by the hospitality workflow surfaced in the accountant meeting and the forms work in M20. Period entity with close/lock semantics lands here.

### Out-of-milestone ongoing work

- **SEF ingestion as a data source** — pulling SEF'd invoices into the pipeline for agency visibility. Independently useful; can slot in whenever.
- **Public Serbian tax calendar widget** — marketing / SEO, lightweight.
- **Rule template marketplace** — extends existing rules engine.
- **Pricing page update** — reflects the hospitality positioning once ready.

---

## Sequencing principles

1. **Client-first UI first.** The structural organisation is additive under any version of the forms story and unblocks every future client-scoped feature from living in a clean home.
2. **No forms work before the meeting.** The cost of building the wrong columns is higher than the cost of waiting.
3. **One branch, one cutover.** Saldora has no live users; coexistence is friction for the developer, not safety for the user.
4. **Every new feature lands inside the client workspace** unless it legitimately is agency-scoped. Resist the temptation to add new top-level sidebar entries.
