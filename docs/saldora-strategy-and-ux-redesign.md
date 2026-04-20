# Saldora: Strategic Repositioning and UX Redesign

## Executive Summary

Saldora began as an OCR-first invoice processing platform for Serbian accounting agencies. The Serbian B2B invoicing landscape has changed structurally since Saldora's inception: the Sistem Elektronskih Faktura (SEF) has been mandatory for VAT payers since January 2023, and upcoming amendments effective April 2026 expand its scope further into internal invoices, retail transactions involving corporate cardholders, and electronic delivery notes (eOtpremnice). As more invoice volume moves into SEF, the value of OCR as a standalone wedge diminishes. Positioning Saldora as an "OCR for invoices" product in 2026 is a dying thesis.

The good news is that Saldora has already partially evolved past OCR-first. The AccountingIntent layer (document classification, transaction type detection, VAT treatment decisions, suggested konta, PDV book mapping) and the automation rules engine (office-specific rules for konta assignment, VAT treatment, auto-approval, and review flagging) are already implemented and form a genuine intelligence foundation. The work ahead is not to pivot away from what exists, but to complete the evolution: expand the intelligence, reorganize the experience around the agency's actual workflow, and commit unambiguously to the positioning that follows.

This document outlines a comprehensive strategic and product repositioning. The thesis in one line: **Saldora is the intelligence layer that enriches invoice and document data before it reaches MiniMax, covering the work MiniMax handles poorly or not at all**, with an intentionally narrow scope, purely additive features, and a UI architecture that presents a single coherent story per client.

Saldora does not replace MiniMax, Pantheon, or other incumbents. Saldora does not touch payments, bank reconciliation, or the general ledger. Saldora processes documents, applies accounting intelligence, monitors compliance, and hands cleanly structured data to MiniMax via the integration that is already built. Everything else belongs to the incumbents, and leaving that boundary clean is what makes Saldora a no-brainer add to an agency's existing stack.

---

## Part One: The Core Concern

### OCR as a shrinking wedge

Serbian B2B e-invoicing has been in force since January 2023 under a clearance model operated by the Ministry of Finance. The amendments published in Službeni glasnik 109/2025 and effective for tax periods starting after March 31, 2026, expand the system's scope substantially. Internal invoices, self-invoices for reverse-charge transactions, and retail sales to corporate cardholders must all flow through SEF. Electronic delivery notes become mandatory for B2G transactions from January 2026, with full B2B coverage by October 2027. Penalties for non-compliance range from 200,000 to 2,000,000 RSD.

The practical consequence for a product like Saldora is that the volume of PDF and paper invoices in the domestic VAT-payer ecosystem is shrinking every quarter, and will continue to shrink. Pure OCR for this segment has an expiration date that is sooner than most people assume.

### Why OCR quality is no longer a compelling sales pitch

Accounting agencies already know OCR exists and already know it works. The novelty that carried OCR-first products from 2020 to 2023 is gone. An agency evaluating Saldora in 2026 does not ask "how good is your OCR?" because they have options and they assume it works. They ask "why should I add another tool to my workflow?" OCR alone does not answer that question.

OCR therefore becomes supporting infrastructure inside Saldora, not the reason anyone buys Saldora. It remains essential for the edges of the market that SEF does not cover, but it cannot be the headline. The AccountingIntent layer and automation rules engine already reposition Saldora as an intelligence platform rather than an OCR tool; the remaining work is to make that repositioning visible, durable, and complete.

---

## Part Two: The Intelligence-Only Commitment

Before describing the gaps, one strategic decision needs to be stated explicitly because every downstream decision flows from it.

Saldora is intelligence-only. Saldora processes documents, classifies them, enriches them with accounting semantics, generates compliance alerts, and hands the enriched output to MiniMax (or to exports). Saldora does not handle bank reconciliation, payments, general ledger entries, or any of the operational workflow that belongs to accounting software. This boundary is deliberate and non-negotiable.

The reasoning is straightforward. Incumbents like MiniMax have decades of accumulated operational complexity (general ledger, reporting, payment flows, reconciliation, payroll). Competing on their territory is a ten-year battle against entrenched software agencies will never migrate away from. Saldora wins by staying narrowly on the side of the handoff that incumbents handle badly: document intake, intelligent classification, multi-client compliance oversight, and anything regulatory that spans a portfolio rather than a single company's books.

This commitment has two important implications. First, features like bank reconciliation, payment tracking, and direct financial operations are explicitly out of scope. They have been considered and consciously excluded, not forgotten. Second, MiniMax integration (which is already built as XML export plus REST API push with OAuth, customer management, and VAT rate mapping) is not a nice-to-have but the architectural centerpiece. Every workflow in Saldora ends with a handoff to MiniMax. Saldora's value is measured by how much better MiniMax's input becomes after Saldora has processed it.

---

## Part Three: The Additive Market Gaps

### The critical constraint: agencies do not replace, they add

Accounting agencies already run on MiniMax, Pantheon, Kalkulator, Softek, or similar. They are not evaluating Saldora as a replacement for these systems, and they will not migrate their books to a new platform for any reasonable price. What they are evaluating is whether to add Saldora alongside what they already have.

This raises the bar for Saldora significantly. Every feature must justify its existence on the grounds of doing something the existing stack does not do, or does so badly that the agency works around it in Excel, email, or the owner's head. Saldora must never duplicate functionality that MiniMax handles well. Double-entry bookkeeping, financial statements, general ledger review, payroll, bank reconciliation, and chart-of-accounts management are all out of scope.

The mental model is clean: **MiniMax is the books. Saldora is the pipeline into the books.** The pipeline spans document intake (whether from uploads, OCR, email ingestion, or fiscal receipts), categorization via the AccountingIntent layer, automation via the rules engine, compliance monitoring, and handoff via the MiniMax integration. Saldora owns the pipeline. MiniMax owns the books. The separation is deliberate and unambiguous.

### Gap one: Paušal handling for agencies

Paušalci (flat-rate entrepreneurs outside the VAT system) are handled poorly by existing accounting software because those tools are built around double-entry bookkeeping and VAT workflows. Every agency in Serbia has twenty to fifty paušalci in their portfolio, tracked today in Excel or on paper.

Paušalci have an inverse workflow compared to VAT-payer clients. They primarily issue invoices rather than receive them. Their compliance obligations are narrow but specific: maintain a KPO ledger (Knjiga o ostvarenom prometu) of issued invoices, track revenue against the 6,000,000 RSD paušalac status limit and 8,000,000 RSD PDV threshold, pay monthly doprinosi and quarterly paušalni porez based on activity code and municipality.

A paušal module inside Saldora handles all of this: an outgoing invoice generator with sequential numbering and PDF delivery, auto-population of the KPO ledger from issued invoices, visual revenue-limit monitoring with early warnings, OCR extraction of PU rešenje to pull monthly tax and contribution amounts, payment calendar with QR codes for bank app scanning, overdue alerts, and agency-facing dashboards showing all paušalci clients at once.

Critically, paušalci are a client type inside the single Saldora product, not a separate product. This is implemented as a `client_type` field on the existing clients table (`vat_payer | pausalac | foreign_entity | non_profit`) plus a `direction` field on invoices (`incoming | outgoing`) so that paušalci issuing invoices and occasionally receiving supplier invoices both flow through the same data model without fragmentation. The agency uses the same Saldora interface to handle their VAT payer clients and their paušalci clients; what changes is which features the per-client workspace emphasizes. This architectural decision preserves a single buyer, a single subscription, a single support surface, and a single codebase, while presenting a genuinely tailored experience per client type.

### Gap two: Foreign supplier invoices with reverse-charge logic

Imports and foreign service purchases fall outside both SEF and most of the accounting software's built-in automation. A Serbian company buying software from AWS, buying goods from Italy, or contracting services from Germany receives invoices that SEF does not touch. The accounting treatment is also more complex: foreign VAT (MwSt, IVA, TVA) is not claimable as Serbian input PDV, reverse-charge self-assessment applies for imported services, customs declarations (JCI) carry the actual claimable PDV for imported goods, currency conversion to RSD must use NBS middle rate on invoice date, and withholding tax (porez po odbitku) may apply unless a double taxation agreement is in effect.

Saldora's existing OCR stack and AccountingIntent layer extend directly to multi-language foreign invoices with appropriate prompt engineering and classification rules. The NBS exchange rate integration is already implemented. The genuinely new work is in the accounting logic: recognizing foreign VAT as expense rather than input credit, generating internal PDV documents for reverse-charge transactions, matching supplier invoices to customs documents, applying the correct withholding tax treatment per country and service type, and producing the interni obračun PDV documents that must accompany the entry.

This gap is valuable because it is work that accounting agencies currently do manually for every foreign invoice, with high error rates and significant time cost. A module that handles it correctly is purely additive and fits naturally as an extension of AccountingIntent.

### Gap three: Compliance watchdog

The final intelligence gap is ambient: accounting agencies operate under constant risk of missing compliance deadlines across their portfolio. PDV return deadlines, paušalac revenue limits, doprinosi due dates, withholding tax obligations, archive compliance requirements, and licensed activity renewals all carry penalties. No existing tool proactively monitors these across an entire client portfolio.

The automation rules engine already provides the technical foundation: conditions, actions, priorities, and rule execution logging are all in place. Extending it into a compliance watchdog means adding a scheduled evaluation layer that runs rules against each client's current state daily, not just on invoice processing. The rules themselves become compliance checks: "paušalac revenue exceeds 75% of limit," "PDV return due in less than 7 days," "foreign invoice has no interni obračun PDV generated," "archive export has not been run for this period."

Alerts appear in context (inline in the client's timeline, summarized in the client header, aggregated in the portfolio view), explain themselves with a citation to the applicable law, and auto-update when regulations change. Agencies are paid to avoid problems; Saldora's watchdog prevents problems before they happen. This is net-new information that neither MiniMax nor any other tool in the Serbian market produces.

### Gap four: Client portal for end clients

This is the highest-leverage structural expansion of Saldora because it changes who uses the product, not just what the product does.

Today, an agency's client (a small business owner, a restaurant owner, a paušalac freelancer) never touches Saldora. They send documents to the agency via WhatsApp, email, paper, or Viber. The agency's staff then re-uploads those documents into Saldora, which is manual work and a lossy handoff. Every photo forwarded through WhatsApp is one more place data integrity breaks down.

The client portal inverts this. The agency invites their clients to Saldora. Clients get a lightweight, mobile-first surface where they can submit documents directly (photos of receipts, forwarded PDFs, issued invoices for paušalci), see the status of their books, view compliance alerts relevant to them, and for paušalci, issue invoices themselves. The agency sees everything in the full Saldora workspace; the client sees their own slice.

This architecture is important for several reasons. It raises switching costs dramatically: an agency that has fifty paušalci clients using the portal cannot easily switch to a competing product without migrating all those clients too. Saldora becomes infrastructure, not just a tool. It improves data quality at the source: documents arrive tagged by client, timestamped, in their original resolution, without the context loss of WhatsApp forwarding. And it preserves the B2B-only commercial model: the agency remains the paying customer. End clients get portal access as a benefit of working with that agency. Saldora never needs to do B2C marketing, B2C pricing, B2C support, or B2C payment collection. ARPU stays at agency level while usage expands across thousands of end users. The earlier question of whether to build a separate direct-to-paušalac product is resolved: no, the same product serves both audiences through different lenses.

Full architecture for the portal is detailed in Part Six.

---

## Part Four: What Stays Untouched

The repositioning does not require rewriting Saldora's core. Substantial functionality already exists and continues to work exactly as built. The OCR pipeline via dots.ocr VLM, the Anthropic Claude-based field extraction with regex fallback, the invoice template learning and LLM cost optimization system, multi-country tax ID validation architecture (Serbia, Croatia, Bosnia, Montenegro, North Macedonia, Slovenia, EU), the fiscal receipt PIB extraction rules including client-side capture, duplicate detection, all nine invoice report templates, the product catalog with pg_trgm fuzzy matching, email ingestion with dedicated inbound addresses per organization, automated monthly archive exports, the support ticket system, PDV computation logic, NBS exchange rate integration, audit exports for tax inspections, and the full compliance flows around DPA, consent management, right to erasure, and breach notification.

Most importantly, four foundational pieces are already built and should be treated as load-bearing:

**The AccountingIntent layer** (classification into document types, transaction types, VAT treatments; generation of suggested konta and PDV book entries; confidence scoring and review flagging) already elevates Saldora beyond OCR. Foreign invoice reverse-charge handling and paušalci logic will extend AccountingIntent rather than build parallel systems.

**The automation rules engine** (conditions, actions, priorities, rule templates, execution logging) already provides per-organization customization. The compliance watchdog will extend this engine with scheduled evaluation rather than build a separate alert system.

**The MiniMax integration** (XML export plus REST API push with OAuth, customer find-or-create, currency lookup, VAT rate mapping validated against the RS Swagger spec) already provides the handoff infrastructure. Every new Saldora workflow will terminate in this integration.

**Client management for the Agency plan** (client CRUD, PIB-based auto-assignment of invoices to clients, retroactive assignment when new clients are created, sidebar client selector) already provides the multi-client foundation. The UI redesign builds on top of this rather than replacing it.

The additions required to support the repositioning are focused and bounded. Data model changes include adding `client_type` to the clients table, adding `direction` to the invoices table, introducing a Period entity for close-cycle management, introducing a ChecklistItem entity for close workflows, and extending the Alert surface to cover watchdog output. Existing records migrate with safe defaults: all current clients become `vat_payer`, all current invoices become `incoming`, historical periods are backfilled from invoice_date data.

Nothing that currently works gets deleted. Nothing gets rewritten. This is a strategic extension of a functional product.

---

## Part Five: The UI/UX Redesign

This is the heart of the repositioning. The current UI is feature-indexed: a top-left client dropdown filters global lists of invoices, reports, and settings. Users navigate by feature and scope by client. The replacement architecture inverts this: users navigate by client and, within each client, work through their current period from start to close. Features are expressions of work, not menu destinations.

### Core mental model

Every piece of work in an accounting agency maps to a triple: which client, what period, what task. Saldora's UI reflects this structure directly. Navigation concepts like "Invoices," "Reports," "Rules," and so on do not disappear - they become contextual surfaces within the per-client workspace rather than global destinations.

The product presents five surfaces:

1. **Portfolio view** - agency-wide home showing all clients, their health indicators, and what needs attention today across the whole book of business.
2. **Client view** - the single-page workspace for one client, showing their full story for the current period.
3. **Timeline** - the chronological heart of each client view, recording every event that touched this client.
4. **Close checklist** - the task spine that drives each period's work from start to finish.
5. **Global inbox** - cross-client triage for unprocessed documents, unmatched items, and open compliance alerts.

These five concepts together absorb the full complexity of the product. New capabilities do not add new menus; they enrich existing surfaces.

### The client view: where accountants live

When an accountant clicks on a client, they land on a single page that represents everything about that client's current state. The page has three zones stacked top to bottom.

The **header** always displays the client's name, type badge (VAT payer, Paušalac, Foreign entity, Non-profit), key identifiers (PIB, MB, activity code for paušalci), the period currently being worked with prev/next navigation, the close status for that period, and any persistent compliance alerts specific to this client.

The **timeline** is the central zone. It is a chronological list of every event that touched this client during the current period. Every uploaded document, every AccountingIntent classification, every automation rule that fired, every issued invoice for paušalci, every fiscal receipt submission, every watchdog alert, every export to MiniMax. Each entry shows its type icon, direction (incoming or outgoing), AccountingIntent status (auto-classified, pending review, verified), and a one-line description. Entries are filterable by type, status, and keyword, but the default view is everything in order, because that is how accountants actually think about their clients' months.

The **close checklist** at the bottom of the client view is the task list that drives the period to completion. The checklist is generated automatically based on the client's type and configuration. For a VAT payer, it includes reviewing all incoming documents, verifying AccountingIntent classifications, processing any foreign or fiskalni documents, running the PDV pre-computation check, and exporting journal entries to MiniMax. For a paušalac, it includes logging all issued invoices in the KPO, verifying revenue remains under the limit, confirming tax and doprinosi payments, processing any received supplier documents, and closing the period. Each unchecked item links directly to the work required to complete it, eliminating the need to hunt through feature menus.

Closing a period locks its data for audit integrity and advances the client to the next period.

### Timeline as the central unlock

The timeline replaces the typical accounting tool's pattern of separate feature tabs. The current feature-indexed model forces users to remember where each type of information lives and manually switch context to build a mental model of a client's month.

The timeline eliminates that overhead entirely. Everything that happens to a client appears in one place, in order, with clear type differentiation by icon and color. The accountant opens a client and immediately sees what happened this month: the incoming invoices that were processed, the AccountingIntent classifications that were made, the automation rules that fired, the fiscal receipts submitted through the client portal, the issued invoices for paušalci clients, the alerts the watchdog surfaced. Nothing is hidden behind a tab.

The timeline is also the mechanism for handling the inverse workflow of paušalci gracefully. A paušalac's timeline is dominated by outgoing invoices they issued and their downstream processing (KPO entries, revenue tracking), while a VAT payer's timeline is dominated by incoming invoices and their AccountingIntent classifications. Same timeline, same UI, different composition. When a paušalac occasionally receives a supplier invoice, it drops into the timeline like any other incoming document and is handled through the same flow, without any special mode or context switch.

### Close checklist as the spine

The close checklist is not a status display; it is an actionable to-do list. Each item links directly to the work it represents. Clicking "5 documents pending AccountingIntent review" takes the accountant to a focused view of just those five documents. Clicking "2 foreign invoices missing interni obračun PDV" opens the reverse-charge interface scoped to those two. The accountant should be able to close a period entirely by working through the checklist from top to bottom, never hunting through menus.

This pattern makes the product feel guided rather than exploratory. New accountants at an agency can onboard quickly because the checklist teaches them what a complete close looks like for each client type. Experienced accountants move fast because every task is one click away from every other task.

The final item on every close checklist is always "Export to MiniMax." This is the moment Saldora's work ends and MiniMax's begins. Making this explicit in every checklist reinforces the intelligence-only positioning: Saldora does not replace MiniMax, it prepares perfectly clean, fully classified, intelligence-enriched input for MiniMax.

### Unified document intake

Every incoming document, regardless of source, flows through the same intake surface. A single Add button in the client view, plus a global drop-zone at the top of the app, accepts anything. Additionally, documents arrive automatically through the existing email ingestion pipeline (dedicated inbound address per organization) and through the client portal (direct submission by end clients). Every source lands in the same timeline uniformly, with a source badge (upload, email, portal, fiscal receipt capture) that makes provenance visible without fragmenting the workflow.

### Ambient watchdog

Alerts do not have their own screen. The watchdog surfaces warnings in three contextually appropriate places: inline in the timeline next to the event that triggered them, as persistent badges in the client header summarizing what is open for this client, and aggregated in the portfolio view so agency owners see all clients needing attention.

This design makes the watchdog feel less like a module and more like a quality of the product. Saldora simply notices things. Users do not need to remember to check an alerts screen; the alerts come to them where they are already working.

### The portfolio view

Accountants live in individual client views. Agency owners live in the portfolio view. It displays a grid of clients with health indicators for close status and compliance status, progress on the current month's close across the full book of business, top alerts requiring attention across all clients, and optional team capacity metrics showing which accountants are handling which clients.

This view is what justifies agency-wide pricing rather than per-seat pricing. It gives owners a single surface from which to run the agency as a business, not just a collection of clients.

### Migration path from current UI

The feature-indexed UI that exists today does not need to be torn out on day one. The intermediate state is that the per-client workspace becomes available as an additional page accessible from the clients list, while the existing global lists and feature-indexed navigation remain available. Users can switch freely between the two models during the transition.

This matters because it de-risks the redesign. Pilot agencies can start using the per-client view immediately while the rest of the UI stays familiar. As usage shifts to the new model (which it will, because working client-by-client is dramatically less cognitive overhead than filtering global lists), the old model quietly becomes secondary and eventually retires. At no point is the product broken for existing users.

### How the architecture handles every edge case

The five surfaces and client-type-aware content absorb all the complexity of a Serbian accounting agency's portfolio without requiring separate modes or modules for different situations.

A paušalac who sometimes receives supplier invoices is handled by the same UI as a VAT payer. Only the timeline composition and checklist content differ.

A foreign entity with reverse-charge obligations is handled by the same UI, with foreign-specific entries flowing through the timeline, the AccountingIntent layer applying the right VAT treatment, and foreign-specific checklist items appearing in the close spine.

A client submitting receipts through the portal is handled by the same UI as one whose accountant uploads manually. Only the source badge on the timeline entry differs.

A VAT-payer client whose invoices mostly arrive through email ingestion is handled the same as one whose invoices are uploaded. The source varies; the processing and presentation are unified.

New capabilities added in the future do not add new menus or screens. They become new entry types in the timeline, new items in the checklist, new rules in the watchdog, new actions in the automation rules engine. The product grows in capability without growing in surface area.

---

## Part Six: The Client Portal Architecture

The client portal deserves its own architectural description because it introduces a second class of users (end clients, not agency staff) into the product and needs explicit boundaries.

### Who uses the portal

The portal is for the end clients of an agency: the small business owner whose accounting is done by Računovodstvo Petrović, the paušalac freelancer whose tax returns are filed by an agency, the restaurant owner whose receipts and invoices need to be submitted monthly. These are not paying users of Saldora. The agency is the paying customer. The portal is a benefit the agency extends to their clients.

### What the portal exposes

The portal is deliberately narrow. End clients see only their own data, in a simplified view. The features available to them are: submission of documents (photos, PDFs, forwarded emails) that land in the agency's Saldora workspace tagged with the correct client; a view of documents they have submitted with status (received, processed, verified); for paušalci, an invoice issuance form with sequential numbering and PDF generation; a view of their own KPO ledger and revenue-limit status; a view of compliance alerts that apply to them personally (for example, "your paušalni porez payment is due in 5 days"); and a notifications panel that includes anything the agency wants to communicate to them through Saldora rather than through WhatsApp.

The portal does not expose the agency's internal workspace, other clients' data, the AccountingIntent internals, the automation rules, the portfolio view, or any agency-level configuration.

### How invitations and access work

An agency invites an end client from the client detail page. The invitation carries a one-time token tied to that specific client record. The end client receives an email with a link, creates a lightweight account (just email, password, optionally phone for notifications), and lands directly in their portal scoped to their own data.

Authentication is separate from agency-user authentication. The user role model gains a new `client_portal_user` role that has access only to data where they are the linked end client. The existing `admin | manager | operator | viewer` roles remain for agency-side users.

### Mobile-first submission

Because end clients submit documents primarily from their phones (gas station receipts, hotel invoices in hand, photos of supplier deliveries), the portal's submission flow is mobile-first. The agency-side workspace remains desktop-primary. This means the portal needs its own responsive treatment with large touch targets, a prominent camera-capture action, and a minimum of typing required. Submission should feel like posting to a messaging app, not like filling out a form.

### Data flow into the agency workspace

Every submission from the portal enters the agency's Saldora instance as a timeline entry on the correct client's workspace, tagged with `source: portal` and linked to the submitting end-client user. The existing OCR and AccountingIntent pipeline runs exactly as it does for any other document. From the agency's perspective, portal submissions are simply one more source of documents to be processed, with the advantage that they arrive already correctly attributed.

Notifications flow the other direction: when the agency verifies a document, when a compliance alert needs client action, or when the agency wants to message the client, the portal shows a notification. Email fallback is available for clients who rarely log in.

### Strategic effect

The portal's effect on Saldora's competitive position is disproportionate to the effort of building it. Three dynamics stand out.

Switching costs compound. An agency with twenty paušalci clients using the portal to submit their monthly receipts and issue their invoices cannot easily migrate to a competing product. The portal users would all need to be migrated too, which is a logistical nightmare for the agency and a significant friction even to start thinking about.

Data quality improves structurally. Documents arriving through the portal are attributed correctly from the moment of capture, reducing the manual re-tagging work that WhatsApp-and-email workflows require. OCR accuracy improves because phone-captured images taken specifically for Saldora tend to be better framed than screenshots forwarded from WhatsApp.

The agency relationship deepens. When an agency gives their clients a modern tool that makes the monthly cycle easier, the client's perception of the agency shifts from "the people who send me reminders" to "the agency with the good app." Saldora effectively makes the agency's service better, which is a powerful retention and sales angle for the agency itself.

---

## Part Seven: The Sales Positioning

Given the intelligence-only commitment and the additive principle, the sales conversation has a specific shape.

The agency owner hears something close to this: "You have MiniMax and it works for the books. Keep it. What you do not have is a way to handle paušalci clients without Excel, a way to process foreign invoices correctly the first time with reverse-charge logic, a way to catch compliance risks before they become problems, or a way for your clients to submit documents without WhatsApp chaos. Saldora handles all of that and posts perfectly structured, intelligence-enriched data to MiniMax. Your accountants keep everything they know. Your clients get a modern way to work with you. You get back the thirty or more hours a month your team currently loses to the work MiniMax does not cover."

The pitch is quantified and non-threatening. It names specific work currently happening outside the existing stack, promises measurable time recovery, explicitly preserves the tools the agency already uses, and adds a concrete benefit (modern client experience) that is a selling point for the agency's own business. The agency owner has almost no defensive reason to say no, which is the defining characteristic of a must-have sale.

---

## Part Eight: Guiding Principles

A few principles should guide product decisions going forward.

**Intelligence-only, never operational.** Saldora classifies, enriches, and hands off. Payments, reconciliation, and ledger operations belong to MiniMax. When in doubt, ask whether a feature is producing intelligence or running operations. Operations get cut.

**Additive, never replacement.** Every feature must justify itself as something the existing stack does not do. Anything that duplicates MiniMax functionality gets cut.

**Work-organized, never feature-organized.** The UI reflects how accountants think (client, period, task), not how the product is implemented (OCR, AccountingIntent, rules, watchdog).

**Client type adapts content, not structure.** Paušalci, VAT payers, foreign entities, and non-profits share the same UI. What differs is which entries appear in the timeline and which items appear in the checklist.

**Source-agnostic intake.** Documents are documents regardless of whether they came from uploads, OCR, email ingestion, fiscal receipt capture, or the client portal. The timeline absorbs them all uniformly.

**Ambient alerts, never alert screens.** Compliance risks surface where the work is happening, not in a separate panel that requires discipline to check.

**Handoff to MiniMax is always explicit.** The final item on every close checklist is exporting to MiniMax. This reinforces the intelligence-only positioning at every close cycle.

**Existing intelligence foundations are load-bearing.** The AccountingIntent layer handles classification. The automation rules engine handles per-organization customization. The MiniMax integration handles handoff. New features extend these foundations rather than build parallel systems.

**Client portal extends reach, not scope.** The portal exposes a narrow slice of Saldora to end clients. It never becomes a separate product or a separate codebase.

**Audit integrity is non-negotiable.** Every data mutation is logged. Every period can be closed and locked. Every automatic action is reversible by the user.

---

## Closing

Saldora's path forward is to commit unambiguously to intelligence-only positioning, narrow its scope to the work accounting agencies do outside MiniMax, organize its entire experience around each client's chronological story period by period, and extend its reach into end-client hands through the portal so that submission, intelligence, and handoff form a single coherent flow.

The OCR and template learning, the AccountingIntent layer, the automation rules engine, the MiniMax integration, the client management, the reports, the product catalog, the email ingestion, the archive exports, and all the other pieces already built continue to work as the foundation. The gaps to fill are paušalci handling, foreign invoice reverse-charge logic, the compliance watchdog that extends the rules engine with scheduled evaluation, the per-client UI redesign with timelines and close checklists, and the client portal that extends Saldora into end-client hands.

Everything sits inside a single coherent product that presents as five surfaces (portfolio, client view, timeline, close checklist, global inbox) plus a lightweight portal for end clients, all pointing toward one thing: a perfectly classified, intelligence-enriched handoff to MiniMax at the end of every client's month.

Agencies do not buy Saldora as a bundle of features. They buy it as the intelligence layer they have always been missing, for the work that never had a tool, delivered through the first accounting product in Serbia that treats each client's story as the first-class organizing principle of the workflow.

That is the product worth building.
