# Software Requirements Specification (SRS)
# Saldora - Intelligence Layer for Serbian Hospitality Accounting Agencies

**Version:** 4.0
**Date:** 2026-04-29
**Status:** Source of truth (post-pivot)

---

## Current Thesis (post-pivot)

Saldora is an **intelligence layer for Serbian accounting agencies whose clients are hospitality businesses** — restaurants, cafes, bars, fast food outlets, catering. The wedge is twofold:

1. **OCR on paper invoices with many line items** — beverage distributors, dry-goods suppliers, produce, meat, cleaning supplies, equipment maintenance — the kinds of invoices that still arrive on paper or as PDF email attachments and that SEF (eFaktura) does not and probably will not soon cover.
2. **Generation of legally-required Serbian hospitality forms** from the extracted line-item data — kalkulacije, šank lista, cenovnik, KEP, popis. Today, agencies generate these by hand in Excel.

The buyer is the **agency owner**; the daily users are **agency bookkeepers** who handle 30–40 hospitality clients each, with each client producing 20–40 invoices per month. Saldora is the pipeline from paper-invoice-in to fully-classified, legally-correct data out, and hands that data to **MiniMax** (the dominant Serbian cloud accounting product) for the general ledger and financial reporting. **Saldora does not replace MiniMax.** Saldora does not do bank reconciliation, payment tracking, or general-ledger postings.

The original positioning of this document — "generic AI-powered invoice processing for accountants, agencies, and enterprises" — is **superseded** by the hospitality thesis. Capabilities that were generic (multi-tenant org model, OCR + LLM extraction, exports, automation rules, client management) still work and are still in scope; they are simply no longer the primary marketing or product framing. Anything that was paušalci-specific, generic-B2B-portal-shaped, or SEF-load-bearing has been dropped or deferred (see Section 4.17, "Out of scope / dropped").

For the strategic narrative, see [`saldora-strategy-and-ux-redesign.md`](saldora-strategy-and-ux-redesign.md). For milestone status, see [`saldora-implementation-plan.md`](saldora-implementation-plan.md).

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Overall Description](#2-overall-description)
3. [System Architecture](#3-system-architecture)
4. [Functional Requirements](#4-functional-requirements)
   - 4.1 [User Authentication & Authorization](#41-user-authentication--authorization)
   - 4.9 [Business Logic & Validation Rules](#49-business-logic--validation-rules)
   - 4.10 [Accounting Intent Layer](#410-accounting-intent-layer)
   - 4.11 [Automation Rules Engine](#411-automation-rules-engine)
   - 4.12 [Client Management (Agency)](#412-client-management-agency)
   - 4.13 [Invoice Reports (Izveštaji)](#413-invoice-reports-izveštaji)
   - 4.14 [Email Ingestion Pipeline (planned, not yet wired)](#414-email-ingestion-pipeline-planned)
   - 4.15 [Product Catalog (Katalog proizvoda)](#415-product-catalog-katalog-proizvoda)
   - 4.16 [In-App Support System (planned)](#416-in-app-support-system-planned)
   - 4.17 [Out-of-Scope / Dropped Features](#417-out-of-scope--dropped-features)
   - 4.18 [Client-First UI (M19)](#418-client-first-ui-m19)
   - 4.19 [Hospitality Legal Forms (deferred, M20)](#419-hospitality-legal-forms-deferred-m20)
5. [Non-Functional Requirements](#5-non-functional-requirements)
6. [Tech Stack](#6-tech-stack)
7. [Database Design](#7-database-design)
8. [API Specification](#8-api-specification)
9. [AI/ML Components](#9-aiml-components)
10. [Security Requirements](#10-security-requirements)
    - 10.6 [Legal & Compliance Flows](#106-legal--compliance-flows)
11. [Deployment Architecture](#11-deployment-architecture)
12. [Third-Party Integrations](#12-third-party-integrations)
13. [User Interface Requirements](#13-user-interface-requirements)
14. [Testing Requirements](#14-testing-requirements)
15. [Appendices](#15-appendices)

---

## 1. Introduction

### 1.1 Purpose

This Software Requirements Specification (SRS) document is the source-of-truth description of the Saldora platform — an intelligence layer for Serbian accounting agencies handling hospitality clients. The document outlines functional and non-functional requirements, system architecture, and technical specifications as the product exists today (post-pivot, April 2026).

This is a living document. Content describing pre-pivot generic-B2B positioning has been either rewritten in place to reflect the hospitality thesis or explicitly marked as superseded.

### 1.2 Scope

Saldora is a SaaS platform that enables Serbian accounting agencies handling hospitality portfolios (restaurants, cafes, bars) to:

- Ingest paper invoices, fiscal receipts, and PDF email attachments at scale
- Automatically extract structured data (header fields **and** line items) using a vision-language OCR pipeline plus an LLM extraction layer
- Process both Cyrillic and Latin script documents
- Normalize line-item descriptions to canonical product identities via a per-organization product catalog
- Manage clients (the agency's hospitality businesses), scope every invoice to one client, and surface the agency's portfolio at a glance
- Apply per-client and org-wide automation rules to classify invoices (document type, VAT treatment, suggested konto)
- Generate procurement intelligence reports (kalkulacija, RUC, spending by category, dnevna evidencija robe) on top of normalized line items
- Export structured data to MiniMax (XML file or REST API push), XLSX, CSV, JSON
- Generate monthly archives (ZIP with invoice register, PDV summary, audit trail, original PDFs) for retention

The system's deliberate non-goals are documented in Section 4.17.

### 1.3 Definitions, Acronyms, and Abbreviations

| Term | Definition |
|------|------------|
| OCR | Optical Character Recognition |
| PIB | Poreski Identifikacioni Broj (Tax Identification Number in Serbia) |
| APR | Agencija za Privredne Registre (Serbian Business Registers Agency) |
| PDV | Porez na Dodatu Vrednost (Value Added Tax in Serbia) |
| SEF | Sistem Elektronskih Faktura (Serbian E-Invoice System / eFaktura) |
| Konto | Account code in Serbian chart of accounts (Kontni plan) |
| MB | Matični Broj (Company Registration Number in Serbia) |
| PPPDV | Poreska Prijava PDV (VAT Return Form) |
| KPR | Knjiga Primljenih Računa (Received Invoice Book) |
| KIR | Knjiga Izdatih Računa (Issued Invoice Book) |
| ZZPL | Zakon o zaštiti podataka o ličnosti (Serbian Data Protection Law, Sl. glasnik RS br. 87/2018) |
| GDPR | General Data Protection Regulation (reference standard) |
| NBS | Narodna banka Srbije (National Bank of Serbia) |
| SaaS | Software as a Service |
| JWT | JSON Web Token |
| REST | Representational State Transfer |

### 1.4 Target Audience

**Primary:**
- Accounting agencies whose portfolios include hospitality clients (restaurants, cafes, bars, catering, fast food). Buyer = agency owner; daily users = agency bookkeepers.

**Secondary (still supported, no longer the primary motion):**
- Independent accountants and small-to-medium accounting practices that handle a mixed portfolio.
- Hospitality SMEs that do their own bookkeeping in-house (a small minority of the market).

**Removed from target audience:**
- Paušalci (flat-rate entrepreneurs) as a persona — the paušal module was reverted; MiniMax's dedicated paušal product handles that segment.
- End clients of agencies (e.g., a restaurant owner directly using Saldora) — see "no client portal" in Section 4.17. The agency remains the sole user class.
- Generic enterprise B2B users (large corporations with thousands of invoices/month) — not the wedge; these companies receive the bulk of their invoices via SEF and have established workflows.

### 1.5 Document Conventions

- **MUST** - Mandatory requirement
- **SHOULD** - Recommended requirement
- **MAY** - Optional requirement

---

## 2. Overall Description

### 2.1 Product Perspective

Saldora operates as a standalone web application with the following integration points:

```
┌─────────────────────────────────────────────────────────────────┐
│                        Saldora Platform                        │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Web App   │  │  REST API   │  │    AI Processing Engine │  │
│  │  (Next.js)  │  │  (FastAPI)  │  │    (Python/PyTorch)     │  │
│  └──────┬──────┘  └──────┬──────┘  └────────────┬────────────┘  │
│         │                │                      │                │
│         └────────────────┼──────────────────────┘                │
│                          │                                       │
├──────────────────────────┼───────────────────────────────────────┤
│                    External Services                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │  APR API    │  │   Storage   │  │    Payment Processor    │  │
│  │  (Serbia)   │  │   (S3/R2)   │  │    (Paddle)             │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Product Features (High-Level)

| Feature | Description | Status |
|---------|-------------|--------|
| Invoice Upload | Multi-format document upload (PDF, JPG, PNG, TIFF, WEBP) | Shipped |
| AI Data Extraction | Vision-language OCR (dots.ocr) + Anthropic Claude Haiku LLM extraction | Shipped |
| Cyrillic/Latin Support | Full support for Serbian scripts at OCR, extraction, and UI level | Shipped |
| Manual Approval Gate | New organizations land in `pending` status; require admin approval before access | Shipped (M-Auth) |
| Multi-Tenant Org Model | All data scoped by `organization_id`; role-based access | Shipped |
| Client Management | First-class for Agency plan: CRUD, hard delete, retroactive PIB-based assignment | Shipped (M12) |
| Per-Client Automation Rules | Rules optionally scoped to specific clients via `rule_client_associations` | Shipped (M19) |
| Client Event Log (Timeline) | Append-only `client_events` table for per-client activity feed | Shipped (M19.1) |
| Client-First UI | Portfolio view + per-client workspace + Hronologija/Fakture/Izveštaji/Pravila tabs | Shipping (M19) |
| Procurement Reports | Kalkulacija, RUC, spending by category, dnevna evidencija robe | Shipped (M16-equivalent) |
| Product Catalog | Canonical products + aliases + pg_trgm fuzzy matching from line items | Shipped |
| Automation Rules Engine | Org-wide and per-client rules for konto/VAT classification | Shipped |
| Accounting Intent Layer | Document type, transaction type, VAT treatment, suggested konta | Shipped |
| MiniMax Export | XML file export and REST API push (received invoices, partner sync) | Shipped |
| Generic Exports | XLSX, CSV, JSON with custom templates | Shipped |
| Monthly Archives | Automated ZIP delivery via email; retention shifted to user | Shipped |
| Hospitality Legal Forms | Kalkulacije, šank lista, cenovnik, KEP, popis (data foundation in place) | **Deferred** (M20, post-accountant-meeting) |
| Email Ingestion | Per-org inbound address `org-slug@invoices.saldora.ai` | **Planned, not yet wired** |
| In-App Support Tickets | Ticket system with attachments | **Planned** (M15) |
| API Access | REST API + per-org API keys | Shipped |
| Paddle Billing | Merchant of Record subscription billing (no Stripe) | Shipped |

### 2.3 User Classes and Characteristics

#### 2.3.1 Agency Owner (primary buyer)

- Owns or manages a small accounting agency (typically 1–10 bookkeepers).
- Holds 30–40 hospitality clients in the portfolio.
- Decides whether to adopt Saldora; signs the contract; pays the bill.
- Cares about: time saved per bookkeeper per month, audit traceability, smooth handoff to MiniMax, ZZPL compliance posture.
- Day-to-day, primarily uses the Portfolio view and the Billing / Settings pages.

#### 2.3.2 Agency Bookkeeper (primary daily user)

- Processes 20–40 invoices per hospitality client per month, across the agency's full portfolio.
- Spends most time inside the per-client workspace: uploading or reviewing invoices, fixing OCR misreads on line items, generating reports, exporting to MiniMax.
- Needs the workflow to be fast and keyboard-friendly; needs the OCR to actually capture line items, not just totals.
- Cares about: line-item accuracy, low review rate, one-click export.

#### 2.3.3 Independent Accountant (secondary)

- Processes 50–200 invoices/month for a mixed portfolio.
- Uses the same UI as agency bookkeepers but typically does not need the Portfolio view and Client Management as heavily.
- Still supported on Professional and Agency plans.

#### 2.3.4 Hospitality SME (rare, secondary)

- Owner-operated restaurant or cafe doing in-house bookkeeping.
- Single-client organization. Treated as a degenerate case of the agency model with one client = the SME itself.

### 2.4 Operating Environment

- **Client Side:** Modern web browsers (Chrome 90+, Firefox 88+, Safari 14+, Edge 90+)
- **Server Side:** Linux-based cloud infrastructure
- **Mobile:** Responsive design for tablet/mobile viewing (upload via mobile camera)

### 2.5 Design and Implementation Constraints

1. Must comply with ZZPL (Zakon o zaštiti podataka o ličnosti) as primary data protection law, with GDPR as a reference standard
2. All data must be stored in data centers that provide adequate protection (EU/EEA or Serbia)
3. Must support both Cyrillic and Latin character sets
4. Response time for OCR processing must not exceed 10 seconds per page
5. System must handle concurrent processing of up to 100 documents

### 2.6 Assumptions and Dependencies

**Assumptions:**
- Users have stable internet connection
- Invoice documents are legible (not severely damaged or blurred); the OCR worker logs and surfaces an error otherwise — there is no automatic OCR fallback
- APR registry data is available via a licensed intermediary or commercial contract; a manual override path exists for outages
- The hospitality clients of an agency continue to receive invoices on paper / PDF email attachments at meaningful volume (the wedge depends on this)

**Dependencies:**
- **Cloudflare R2** for production document storage (S3-compatible, MinIO for local dev)
- **Modal.com** for GPU OCR inference (dots.ocr on A10G, scale-to-zero)
- **Anthropic** for Claude Haiku LLM field extraction
- **Resend** for transactional email (welcome, password reset, monthly archive delivery, admin approval notifications)
- **Paddle** as Merchant of Record for subscription billing (Stripe is not available in Serbia)
- **Cloudflare** for DNS, SSL, CDN, DDoS protection
- **Hetzner CX32 VPS** as the application host
- **NBS** (Narodna banka Srbije) public exchange-rate API for foreign-currency → RSD conversion
- **APR** registry for PIB verification (licensed intermediary or commercial contract; manual override available)
- **MiniMax** REST API for direct push of received invoices and partner sync (per-org credentials)

---

## 3. System Architecture

### 3.1 High-Level Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                              CLIENT LAYER                               │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                     Next.js Web Application                       │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐  │  │
│  │  │   Pages    │  │ Components │  │   Hooks    │  │   Store    │  │  │
│  │  │  (App Dir) │  │    (UI)    │  │  (Logic)   │  │  (Zustand) │  │  │
│  │  └────────────┘  └────────────┘  └────────────┘  └────────────┘  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ HTTPS
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                              API LAYER                                  │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                    FastAPI Application                            │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐  │  │
│  │  │  Routers   │  │   Auth     │  │ Middleware │  │ Validators │  │  │
│  │  │ (Endpoints)│  │   (JWT)    │  │  (CORS)    │  │ (Pydantic) │  │  │
│  │  └────────────┘  └────────────┘  └────────────┘  └────────────┘  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
┌──────────────────────┐ ┌──────────────────┐ ┌──────────────────────┐
│   AI PROCESSING      │ │    DATABASE      │ │   FILE STORAGE       │
│  ┌────────────────┐  │ │  ┌────────────┐  │ │  ┌────────────────┐  │
│  │ Modal.com      │  │ │  │ PostgreSQL │  │ │  │ Cloudflare R2  │  │
│  │ - dots.ocr VLM │  │ │  │ (Hetzner)  │  │ │  │ (prod)         │  │
│  │ (A10G GPU,     │  │ │  └────────────┘  │ │  │ MinIO (dev)    │  │
│  │  scale-to-zero)│  │ │  ┌────────────┐  │ │  └────────────────┘  │
│  └────────────────┘  │ │  │   Redis    │  │ └──────────────────────┘
│  ┌────────────────┐  │ │  │  (Cache+   │  │
│  │ OCR Worker     │  │ │  │   Celery)  │  │
│  │ (Celery, CPU)  │  │ │  └────────────┘  │
│  └────────────────┘  │ └──────────────────┘
│  ┌────────────────┐  │
│  │ LLM Extractor  │  │
│  │ (Claude Haiku) │  │
│  └────────────────┘  │
└──────────────────────┘
```

### 3.2 Component Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Frontend Components                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────────┐  │
│  │   Auth      │    │  Dashboard  │    │    Invoice Processing   │  │
│  │  - Login    │    │  - Stats    │    │    - Upload             │  │
│  │  - Register │    │  - History  │    │    - Preview            │  │
│  │  - Reset PW │    │  - Charts   │    │    - Edit               │  │
│  └─────────────┘    └─────────────┘    │    - Export             │  │
│                                         └─────────────────────────┘  │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────────┐  │
│  │  Settings   │    │   Billing   │    │    Shared Components    │  │
│  │  - Profile  │    │  - Plans    │    │    - Navigation         │  │
│  │  - API Keys │    │  - Usage    │    │    - Forms              │  │
│  │  - Team     │    │  - Invoices │    │    - Tables             │  │
│  └─────────────┘    └─────────────┘    └─────────────────────────┘  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                        Backend Services                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐  │
│  │  Auth Service   │    │ Invoice Service │    │  Export Service │  │
│  │  - JWT tokens   │    │ - CRUD ops      │    │  - XLSX gen     │  │
│  │  - OAuth        │    │ - Search        │    │  - CSV gen      │  │
│  │  - Sessions     │    │ - Filtering     │    │  - JSON gen     │  │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘  │
│                                                                      │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐  │
│  │   OCR Service   │    │   APR Service   │    │ Storage Service │  │
│  │  - Preprocessing│    │ - PIB lookup    │    │  - Upload       │  │
│  │  - Text extract │    │ - Company info  │    │  - Download     │  │
│  │  - Layout parse │    │ - Caching       │    │  - Delete       │  │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘  │
│                                                                      │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐  │
│  │ Billing Service │    │  Queue Service  │    │ MiniMax Service │  │
│  │  - Paddle (MoR) │    │ - Celery tasks  │    │  - XML export   │  │
│  │  - Usage record │    │ - Job status    │    │  - REST push    │  │
│  │  - Approval gate│    │ - Retry logic   │    │  - Token cache  │  │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘  │
│                                                                      │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐  │
│  │ Reports Service │    │ Catalog Service │    │ Event Logger    │  │
│  │  - SQL aggreg.  │    │  - pg_trgm      │    │  - client_events│  │
│  │  - CSV export   │    │  - merge UI     │    │  - timeline     │  │
│  │  - per-client   │    │  - aliases      │    │  - audit_log    │  │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.3 Data Flow Diagram

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  User    │     │  Upload  │     │   OCR    │     │   LLM    │
│  Uploads │────▶│  Service │────▶│  Engine  │────▶│  Extract │
│  Invoice │     │  (S3)    │     │(dots.ocr)│     │ (Claude) │
└──────────┘     └──────────┘     └──────────┘     └──────────┘
                                                         │
                                                         ▼
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  Export  │     │  User    │     │   PIB    │     │  Math    │
│  Data    │◀────│  Review  │◀────│  Verify  │◀────│  Validate│
│          │     │  & Edit  │     │          │     │          │
└──────────┘     └──────────┘     └──────────┘     └──────────┘
```

---

## 4. Functional Requirements

### 4.1 User Authentication & Authorization

#### FR-4.1.1 User Registration
| ID | FR-4.1.1 |
|----|----------|
| **Description** | System MUST allow users to register using email and password and creates a fresh organization for the registrant |
| **Input** | Email, password, first/last name, organization name |
| **Output** | User account created, organization created with `subscription_status = 'pending'`, admin notification email dispatched |
| **Validation** | Email format, password strength (min 8 chars, 1 uppercase, 1 number) |
| **Default role** | `admin` of the new org (the registrant); subsequent users are invited via `/invitations` |

#### FR-4.1.2 User Login
| ID | FR-4.1.2 |
|----|----------|
| **Description** | System MUST authenticate users via email/password |
| **Input** | Email, password |
| **Output** | JWT access token, refresh token |
| **Session** | Access token expires in 1 hour, refresh token in 7 days |

#### FR-4.1.3 Password Reset
| ID | FR-4.1.3 |
|----|----------|
| **Description** | System MUST allow password reset via email |
| **Flow** | Request reset → Resend email with link → New password form → Confirmation |

#### FR-4.1.4 Role-Based Access Control
| ID | FR-4.1.4 |
|----|----------|
| **Description** | System MUST support multiple user roles |
| **Roles** | Admin, Manager, Operator, Viewer |

| Role | Permissions |
|------|-------------|
| Admin | Full access, billing, team management, Paddle settings |
| Manager | Invoice processing, export, team view |
| Operator | Invoice processing, export |
| Viewer | Read-only access to processed invoices |

#### FR-4.1.5 Manual Approval Gate (registration → access)

| ID | FR-4.1.5 |
|----|----------|
| **Description** | New organizations MUST land in `subscription_status = 'pending'` and be unable to access functional endpoints until an admin manually approves the account |
| **Enforcement** | The shared `require_role(...)` dependency 403s with body `{"code": "subscription_pending_approval", "subscription_status": "pending"}` whenever a user belongs to an org whose `subscription_status` is `pending` |
| **Frontend** | Pending users are routed to `/awaiting-approval`, which polls user info every ~10 seconds; once status flips to `active` or `trial`, the AuthContext refreshes and the user is forwarded into the app |
| **Admin notification** | On registration, a Resend email is dispatched to the address in `ADMIN_EMAIL` containing org name, slug, contact, and the registrant's email |
| **Approval mechanism** | An interactive script `scripts/admin_orgs.py` (run by Saldora staff over SSH) lists pending orgs and allows the operator to flip `subscription_status` to `active` or `trial` and choose the plan tier. There is no card-on-file step at this stage of the company; billing is handled out-of-band via Paddle once an org is active. |
| **Rationale** | Pre-revenue, every signup is hand-vetted to avoid abuse and to keep our agency-buyer focus tight. This is intentionally manual until self-serve onboarding is wired with Paddle Checkout. |

**`subscription_status` allowed values:**

| Value | Meaning |
|-------|---------|
| `pending` | Newly registered org awaiting admin approval (default for new registrations) |
| `trial` | Approved, active in trial window |
| `active` | Approved, paying or evaluation account |
| `canceled` | Subscription canceled by user/admin; access typically revoked at period end |
| `expired` | Trial ended without conversion or subscription lapsed |
| `NULL` | Legacy value for orgs created before the column existed; treated as `active` by gating logic and backfilled on access |

#### FR-4.1.6 Team Invitations & Join Requests

| ID | FR-4.1.6 |
|----|----------|
| **Description** | Admins MUST be able to invite teammates via email; the invitee accepts via a tokenized link |
| **Models** | `invitations` (admin → email, role, token, expires_at), `join_requests` (a user requesting to join a known org by email match, requires approval) |
| **Limits** | Plan-defined seat caps |

### 4.2 Invoice Upload & Management

#### FR-4.2.1 Single Invoice Upload
| ID | FR-4.2.1 |
|----|----------|
| **Description** | System MUST allow single invoice file upload |
| **Supported Formats** | PDF, JPEG, PNG, TIFF, BMP, WEBP |
| **Max File Size** | 20 MB per file |
| **Validation** | File type, file size, image quality check |

#### FR-4.2.2 Batch Upload
| ID | FR-4.2.2 |
|----|----------|
| **Description** | System MUST allow multiple invoice upload |
| **Max Files** | 50 files per batch |
| **Max Total Size** | 200 MB per batch |
| **Progress** | Real-time upload progress indicator |

#### FR-4.2.3 Drag & Drop Upload
| ID | FR-4.2.3 |
|----|----------|
| **Description** | System SHOULD support drag & drop file upload |
| **Feedback** | Visual indication of drop zone, file validation feedback |

#### FR-4.2.4 Mobile Camera Upload
| ID | FR-4.2.4 |
|----|----------|
| **Description** | System SHOULD allow direct camera capture on mobile |
| **Features** | Auto-crop, perspective correction suggestion |

### 4.3 AI-Powered Data Extraction

#### FR-4.3.1 OCR Processing
| ID | FR-4.3.1 |
|----|----------|
| **Description** | System MUST extract text from uploaded documents |
| **Scripts** | Full support for Cyrillic and Latin alphabets |
| **Accuracy** | Minimum 95% character accuracy on clear documents |
| **Languages** | Serbian (primary), English (secondary) |

#### FR-4.3.2 Field Extraction
| ID | FR-4.3.2 |
|----|----------|
| **Description** | System MUST extract structured invoice fields |
| **Primary Method** | LLM-based extraction (Anthropic Claude) — sends raw OCR text with JSON schema, receives complete structured output |
| **Fallback Method** | Regex pattern matching when LLM is unavailable |

**Required Fields:**

| Field | Description | Validation |
|-------|-------------|------------|
| invoice_number | Unique invoice identifier | Alphanumeric |
| invoice_date | Date of invoice issue | Valid date format |
| due_date | Payment due date | Valid date, >= invoice_date |
| seller_name | Seller company name | Non-empty string |
| seller_pib | Seller tax ID (PIB) | 9 digits, mod-11 checksum |
| seller_mb | Seller registration number (MB) | 8 digits |
| seller_address | Seller address | Non-empty string |
| seller_city | Seller city | String |
| seller_postal_code | Seller postal code | String |
| buyer_name | Buyer company name | Non-empty string |
| buyer_pib | Buyer tax ID (PIB) | 9 digits, mod-11 checksum |
| buyer_mb | Buyer registration number (MB) | 8 digits |
| buyer_address | Buyer address | Non-empty string |
| buyer_city | Buyer city | String |
| buyer_postal_code | Buyer postal code | String |
| subtotal | Amount before tax | Decimal number |
| tax_rate | VAT rate applied | 0%, 10%, or 20% |
| tax_amount | Calculated tax | Decimal number |
| total_amount | Total including tax | Decimal number |
| currency | Currency code | RSD, EUR, USD |
| line_items | Individual items/services | Array of items |
| tax_groups | Per-section PDV breakdown | Array of tax groups |

**Line Item Fields:**

| Field | Description |
|-------|-------------|
| description | Item/service description |
| quantity | Number of units |
| unit_price | Price per unit |
| discount | Discount percentage (rabat), e.g. 7.00 for 7% (nullable) |
| tax_base | Taxable base after discount, before VAT (poreska osnovica) (nullable) |
| total | Line total |
| tax_rate | VAT rate for this line item |
| tax_amount | VAT amount for this line item (nullable) |

**Tax Group Fields:**

| Field | Description |
|-------|-------------|
| rate | VAT rate (e.g., 20, 10, 0) |
| base_amount | Taxable base (osnovica) for this group |
| tax_amount | Tax amount (PDV iznos) for this group |

**Note:** Each separate PDV line on the invoice becomes its own `tax_group` entry. Groups are NOT merged even when they share the same rate (e.g., goods at 20% and services at 20% remain as two separate entries).

#### FR-4.3.3 Confidence Scoring
| ID | FR-4.3.3 |
|----|----------|
| **Description** | System MUST provide confidence scores at both overall and per-field level |
| **Scale** | 0-100% confidence (stored as 0.0-1.0 in DB, scaled in API) |
| **Threshold** | Fields below 80% confidence individually flagged with `needs_review: true` |
| **Display** | Text labels instead of percentages: "Pouzdano" (green, ≥75%), "Proveriti" (amber, 50-74%), "Nepouzdano" (red, <50%) |
| **Field Confidence** | Each extracted field has: `field_name`, `value`, `confidence`, `needs_review` |

#### FR-4.3.4 Multi-Page Document Support
| ID | FR-4.3.4 |
|----|----------|
| **Description** | System MUST handle multi-page invoice documents |
| **Detection** | Automatic detection of invoice continuation |
| **Merge** | Combine data from multiple pages into single record |

### 4.4 Data Verification

#### FR-4.4.1 PIB Verification
| ID | FR-4.4.1 |
|----|----------|
| **Description** | System MUST verify PIB numbers against APR database |
| **Data Retrieved** | Company name, address, status, registration date |
| **Caching** | Cache APR responses for 24 hours |
| **Offline** | Show warning if APR unavailable, allow manual override |

#### FR-4.4.2 Mathematical Verification
| ID | FR-4.4.2 |
|----|----------|
| **Description** | System MUST verify invoice calculations |
| **Checks** | Line items sum = Subtotal, Subtotal + Tax = Total, Line item math (qty * price = total), Tax groups consistency |
| **Tolerance** | Tiered tolerance based on amount range (see Section 4.9.5) |
| **Tax Groups** | Sum of group base_amounts ≈ subtotal; sum of group tax_amounts ≈ tax_amount |
| **Note** | Tax amount is extracted as-printed from the document; it is NOT recomputed from subtotal * rate |

#### FR-4.4.3 Duplicate Detection
| ID | FR-4.4.3 |
|----|----------|
| **Description** | System MUST detect and block duplicate invoices at verification time |
| **Criteria** | Same invoice number + seller PIB within the same organization, where the existing invoice has status `verified` or `exported` |
| **Action** | Return HTTP 409 with message "Faktura sa ovim brojem od ovog dobavljača već postoji" |
| **Override** | Admin can force-verify by passing `?force=true` query parameter; non-admins always receive 409 |

**Duplicate Detection Logic:**
```
DUPLICATE_CHECK(invoice, organization_id):
  IF EXISTS(
    invoice_number == invoice.invoice_number
    AND seller_pib == invoice.seller.pib
    AND organization_id == organization_id
    AND status IN ('verified', 'exported')
  ):
    RETURN HTTP 409 ("Faktura sa ovim brojem od ovog dobavljača već postoji")
    IF caller is admin AND force=true:
      CONTINUE verification
    ELSE:
      BLOCK
```

### 4.5 Data Review & Editing

#### FR-4.5.1 Side-by-Side View
| ID | FR-4.5.1 |
|----|----------|
| **Description** | System MUST display original document alongside extracted data |
| **Features** | Zoom, pan, rotate document view |
| **Highlighting** | Click field to highlight corresponding area in document |

#### FR-4.5.2 Inline Editing
| ID | FR-4.5.2 |
|----|----------|
| **Description** | System MUST allow editing of extracted fields |
| **Validation** | Real-time validation on edit, field-level warning/error highlighting |
| **Features** | Per-field confidence badges, dirty-state indicators, per-field reset, Ctrl+S save shortcut |
| **Line Items** | Add, edit, and remove individual line items inline |
| **Tax Groups** | Add, edit, and remove tax rate groups inline |
| **Status** | Editing a verified invoice reverts it to `review` status |
| **Feedback** | Toast notifications for save and verify actions |

#### FR-4.5.3 Bulk Editing
| ID | FR-4.5.3 |
|----|----------|
| **Description** | System SHOULD allow bulk editing across multiple invoices |
| **Use Case** | Correct common extraction errors across batch |

### 4.6 Data Export

#### FR-4.6.1 Excel Export (XLSX)
| ID | FR-4.6.1 |
|----|----------|
| **Description** | System MUST export data to Excel format |
| **Features** | Formatted headers, data validation, multiple sheets |
| **Templates** | Support custom export templates |

#### FR-4.6.2 CSV Export
| ID | FR-4.6.2 |
|----|----------|
| **Description** | System MUST export data to CSV format |
| **Encoding** | UTF-8 with BOM for Excel compatibility |
| **Delimiter** | Configurable (comma, semicolon, tab) |

#### FR-4.6.3 JSON Export
| ID | FR-4.6.3 |
|----|----------|
| **Description** | System MUST export data to JSON format |
| **Structure** | Configurable (flat or nested) |
| **Use Case** | API integration, data exchange |

#### FR-4.6.4 Custom Export Templates
| ID | FR-4.6.4 |
|----|----------|
| **Description** | System SHOULD support custom export field mapping |
| **Features** | Field selection, ordering, renaming, formatting |

#### FR-4.6.5 MiniMax XML Export
| ID | FR-4.6.5 |
|----|----------|
| **Description** | System MUST export data to MiniMax-compatible XML format |
| **Format** | XML per MiniMax import schema (Stranke + Temeljnice) |
| **Content** | Deduplicated partners by PIB, journal entries from accounting_intent |
| **Use Case** | Import into MiniMax accounting software (minimax.rs) |

#### FR-4.6.6 MiniMax REST API Push
| ID | FR-4.6.6 |
|----|----------|
| **Description** | System SHOULD support direct push of invoices to MiniMax via REST API |
| **Authentication** | OAuth 2.0 (client_id, client_secret, username, password) |
| **Features** | Push received invoices, find/create customers by PIB, currency lookup |
| **Configuration** | Per-organization MiniMax credentials and org ID |

#### FR-4.6.7 Export UI
| ID | FR-4.6.7 |
|----|----------|
| **Description** | System MUST provide a frontend dialog for selecting export format and options |
| **Trigger** | Batch export from invoice list (multiple selection) or single export from invoice detail |
| **Formats** | XLSX, CSV, JSON, MiniMax XML — each with format-specific options |
| **Error Handling** | Display blocked invoices with reasons when export is rejected (422) |

### 4.7 Dashboard & Analytics

#### FR-4.7.1 Processing Statistics
| ID | FR-4.7.1 |
|----|----------|
| **Description** | System MUST display processing statistics |
| **Metrics** | Total processed, success rate, average processing time |
| **Period** | Daily, weekly, monthly, custom range |

#### FR-4.7.2 Usage Tracking
| ID | FR-4.7.2 |
|----|----------|
| **Description** | System MUST track usage against subscription limits |
| **Display** | Current usage, remaining quota, usage history |
| **Alerts** | Notification at 80%, 90%, 100% of limit |
| **Implementation** | Monthly invoice counts are tracked in the write-only `usage_records` table (incremented on successful processing). Plan limits are checked against this counter, NOT by counting live invoices. This prevents billing exploits where deleting invoices would reset usage. |

#### FR-4.7.3 Processing History
| ID | FR-4.7.3 |
|----|----------|
| **Description** | System MUST maintain searchable processing history |
| **Search** | By date, invoice number, seller/buyer, amount |
| **Retention** | Minimum 10 years (per Serbian Accounting Law) |

#### FR-4.7.4 — REMOVED

Payment tracking is not part of Saldora. Saldora is an intelligence-only platform. Payment operations are handled by downstream accounting software (MiniMax, etc.).

#### FR-4.7.5 Automated Archive Export (Arhiviranje)
| ID | FR-4.7.5 |
|----|----------|
| **Description** | System MUST provide automated monthly archive exports delivered via email |
| **Content** | ZIP containing invoice register (CSV), PDV summary (Excel), audit trail (CSV), and original PDF documents |
| **Delivery** | Email with download link (valid 24 hours) to organization's billing email |
| **Schedule** | Monthly, configurable; can also be triggered manually via "Testiraj odmah" |
| **Data Retention** | The system generates and delivers archives but does NOT guarantee long-term storage. Data retention responsibility is shifted to the end user — they must save the received ZIP archive as part of their accounting records per Zakon o računovodstvu (10-year retention). The platform retains invoice data for the subscription period only. |
| **Frontend** | `/arhiviranje` page with settings, manual trigger, and delivery history |

### 4.8 API Access

#### FR-4.8.1 REST API
| ID | FR-4.8.1 |
|----|----------|
| **Description** | System MUST provide REST API for programmatic access |
| **Authentication** | API key or OAuth 2.0 |
| **Rate Limiting** | Based on subscription tier |

#### FR-4.8.2 — DEPRIORITIZED

Webhook notifications are not being implemented at this time. Webhooks become useful only after the full workflow (verify → export) is API-driven.

### 4.9 Business Logic & Validation Rules

This section defines explicit decision rules for invoice processing, determining when to auto-approve, flag for review, or block export.

#### 4.9.1 PIB Validation Rules

| Scenario | APR Response | Action | User Notification |
|----------|--------------|--------|-------------------|
| Valid PIB, Active company | Status: "AKTIVAN" | ✅ Auto-approve | Green checkmark, company name shown |
| Valid PIB, Inactive company | Status: "BRISAN" / "U LIKVIDACIJI" | ⚠️ Flag for review | Warning: "Firma nije aktivna u APR" |
| Valid PIB, Company in bankruptcy | Status: "STEČAJ" | ⚠️ Flag for review | Warning: "Firma u stečaju" |
| Invalid PIB format | N/A (format check) | 🚫 Block export | Error: "PIB mora imati 9 cifara" |
| PIB not found in APR | 404 response | ⚠️ Flag for review | Warning: "PIB nije pronađen u APR bazi" |
| APR service unavailable | Timeout/5xx | ⚠️ Allow with warning | Warning: "APR verifikacija nedostupna" |

**Decision Matrix:**
```
PIB_FORMAT_VALID(pib):
  - MUST be exactly 9 digits
  - MUST not start with 0
  - SHOULD pass mod-11 checksum (Serbian PIB algorithm)

PIB_VALIDATION_OUTCOME(pib) → { AUTO_APPROVE, REVIEW, BLOCK }:
  IF NOT PIB_FORMAT_VALID(pib) → BLOCK
  IF APR_UNAVAILABLE → REVIEW (allow manual override)
  IF APR.status == "AKTIVAN" → AUTO_APPROVE
  IF APR.status IN ["BRISAN", "U LIKVIDACIJI", "STEČAJ"] → REVIEW
  IF APR.status == "NOT_FOUND" → REVIEW
```

#### 4.9.2 Same Seller/Buyer Validation

| Scenario | Action | Rationale |
|----------|--------|-----------|
| seller_pib == buyer_pib | ⚠️ Flag for review | Could be valid (internal transfer) or OCR error |
| Same company name, different PIB | ⚠️ Flag for review | Possible OCR misread of PIB |
| Seller == Buyer confirmed by user | ✅ Allow export | User explicitly confirmed internal transfer |

**Decision Logic:**
```
SAME_PARTY_CHECK(seller, buyer):
  IF seller.pib == buyer.pib:
    FLAG_FOR_REVIEW("Prodavac i kupac imaju isti PIB")
    REQUIRE_CONFIRMATION("Da li je ovo interni transfer?")

  IF similarity(seller.name, buyer.name) > 0.85 AND seller.pib != buyer.pib:
    FLAG_FOR_REVIEW("Slična imena, različiti PIB-ovi")
```

#### 4.9.2a Fiscal Receipt PIB Extraction Rules

Serbian fiscal receipts (FISKALNI RAČUN / ФИСКАЛНИ РАЧУН) have a distinct layout that requires special extraction rules:

| Element | Location | Rule |
|---------|----------|------|
| Seller PIB | Standalone 9-digit number near top, before company name | Extract as `seller_pib` |
| Store/branch number | Part of location line (e.g. `1036918-БС Нови Сад 16`) | Do NOT extract as PIB |
| Buyer ID | `ИД купца: XX:NNNNNNNNN` | Extract only digits AFTER the colon |

**Buyer ID Type Codes (ИД купца):**

| Code | Type | Description |
|------|------|-------------|
| 10 | PIB | Tax identification number (9 digits) |
| 11 | JMBG | Personal identification number (13 digits) |
| 12 | PIB + JBKJS | Tax ID + budget user code |
| 20 | Broj pasoša | Passport number (foreign buyer) |

**Sanitization Rules (post-extraction):**
```
SANITIZE_PIB(raw_value):
  # Strip OCR noise: spaces, dashes, dots, slashes
  cleaned = STRIP_CHARS(raw_value, " -./ ")

  # Handle fiscal receipt prefix: "XX:NNNNNNNNN"
  IF ":" IN cleaned:
    candidate = PART_AFTER_LAST_COLON(cleaned)
    IF candidate.is_digits AND LEN(candidate) == 9:
      RETURN candidate

  RETURN cleaned
```

#### 4.9.2b Multi-Country Tax ID Validation (Future)

The system is designed Serbia-first, but the PIB field (`VARCHAR(20)`) and validation architecture support expansion to other Balkan and EU tax ID formats.

| Country | Tax ID | Format | Checksum Algorithm |
|---------|--------|--------|--------------------|
| **Serbia** | PIB | 9 digits | ISO 7064 Mod 11,10 |
| **Croatia** | OIB | 11 digits | ISO 7064 Mod 11,10 |
| **Bosnia & Herzegovina** | JIB | 13 digits | Mod 10 |
| **Montenegro** | PIB | 8 digits | Mod 11 |
| **North Macedonia** | EDB | 13 digits | Varies |
| **Slovenia** | Davčna | 8 digits | Mod 11 |
| **EU (generic)** | VAT ID | CC + 2-12 chars | Country-specific |

**Implementation approach:**
- Country auto-detected from tax ID length, invoice language, and currency
- `TaxIDValidator` dispatches to country-specific validator (PIBValidator, OIBValidator, etc.)
- LLM prompt extended with per-country extraction rules
- Existing PIB sanitization pipeline handles prefix stripping for all formats
- APR verification extended with country-specific registry lookups (Croatia: FINA, BiH: APIF)

#### 4.9.3 VAT Rate Validation

| Extracted Rate | Valid Rates | Action |
|----------------|-------------|--------|
| 0%, 10%, 20% | Standard Serbian rates | ✅ Auto-approve |
| Other value (e.g., 17%, 25%) | Invalid for Serbia | ⚠️ Flag for review |
| Missing/unclear | N/A | ⚠️ Flag for review, suggest 20% |

**Multi-Rate Invoice Handling:**

Invoices with multiple VAT sections are modeled using `tax_groups` — an array of `{rate, base_amount, tax_amount}` extracted directly from the invoice's PDV breakdown table. Each printed PDV row becomes one tax_group entry, even when multiple rows share the same rate (e.g., goods at 20% and services at 20% are kept separate).

```
VALIDATE_VAT_RATES(invoice):
  valid_rates = [0, 10, 20]

  # Validate individual tax group rates
  FOR EACH group IN invoice.tax_groups:
    IF group.rate NOT IN valid_rates:
      FLAG_FOR_REVIEW(f"Nepoznata stopa PDV: {group.rate}%")

  # Validate tax groups sum to invoice totals
  IF invoice.tax_groups IS NOT EMPTY:
    group_base_sum = SUM(tax_groups.base_amount)
    group_tax_sum = SUM(tax_groups.tax_amount)
    IF ABS(group_base_sum - invoice.subtotal) > TOLERANCE:
      FLAG("Osnovice po stopama se ne slažu sa međuzbirom")
    IF ABS(group_tax_sum - invoice.tax_amount) > TOLERANCE:
      FLAG("PDV iznosi po stopama se ne slažu sa ukupnim PDV-om")
```

#### 4.9.4 Currency Handling

| Scenario | Action | Conversion |
|----------|--------|------------|
| RSD (Serbian Dinar) | ✅ Default | N/A |
| EUR detected | ✅ Accept, store original | Optional: show RSD equivalent |
| USD detected | ✅ Accept, store original | Optional: show RSD equivalent |
| Mixed currencies in line items | 🚫 Block export | Error: "Mešovite valute" |
| Currency symbol unclear | ⚠️ Flag for review | Ask user to confirm |

**Currency Detection Rules:**
```
DETECT_CURRENCY(text):
  patterns = {
    "RSD": [r"RSD", r"дин", r"din", r"динара"],
    "EUR": [r"EUR", r"€", r"евра", r"evra"],
    "USD": [r"USD", r"\$", r"долара", r"dolara"]
  }

  IF multiple_currencies_detected:
    FLAG_FOR_REVIEW("Detektovane različite valute")
```

#### 4.9.5 Mathematical Verification & Rounding

**Tolerance Rules:**
| Amount Range | Acceptable Difference | Action if Exceeded |
|--------------|----------------------|-------------------|
| 0 - 10,000 RSD | ±1 RSD | ⚠️ Flag for review |
| 10,001 - 100,000 RSD | ±5 RSD | ⚠️ Flag for review |
| 100,001 - 1,000,000 RSD | ±10 RSD | ⚠️ Flag for review |
| > 1,000,000 RSD | ±50 RSD | ⚠️ Flag for review |

**Verification Checks:**
```
VERIFY_CALCULATIONS(invoice):
  # Check 1: Line items sum to subtotal
  calculated_subtotal = SUM(line_items.total)
  IF ABS(calculated_subtotal - invoice.subtotal) > TOLERANCE:
    FLAG("Stavke se ne slažu sa međuzbirom")

  # Check 2: Total = Subtotal + Tax
  expected_total = invoice.subtotal + invoice.tax_amount
  IF ABS(expected_total - invoice.total_amount) > TOLERANCE:
    FLAG("Zbir nije tačan")

  # Check 3: Tax groups consistency (if present)
  IF invoice.tax_groups IS NOT EMPTY:
    group_base_sum = SUM(tax_groups.base_amount)
    group_tax_sum = SUM(tax_groups.tax_amount)
    IF ABS(group_base_sum - invoice.subtotal) > TOLERANCE:
      FLAG("Osnovice po stopama se ne slažu sa međuzbirom")
    IF ABS(group_tax_sum - invoice.tax_amount) > TOLERANCE:
      FLAG("PDV iznosi po stopama se ne slažu sa ukupnim PDV-om")

  # Check 4: Line item math
  FOR EACH item IN line_items:
    expected = item.quantity * item.unit_price
    IF ABS(expected - item.total) > 1:  # 1 RSD tolerance per line
      FLAG(f"Greška u stavci: {item.description}")

  # Note: Tax amount is NOT recomputed from subtotal * rate.
  # It is extracted as-printed from the document, because Serbian
  # invoices may have rounding differences or per-section PDV lines.
```

#### 4.9.6 Date Validation

| Scenario | Action |
|----------|--------|
| Invoice date in future | ⚠️ Flag for review |
| Due date before invoice date | ⚠️ Flag for review |
| Invoice date > 1 year old | ⚠️ Warning (allowed) |
| Unparseable date format | ⚠️ Flag for review |

#### 4.9.7 Export Blocking Rules

**An invoice MUST NOT be exported if:**
1. PIB format is invalid (neither seller nor buyer)
2. Required fields are missing: invoice_number, invoice_date, seller_pib, total_amount
3. Mathematical verification fails beyond tolerance
4. User has not reviewed flagged warnings
5. Confidence score < 60% and not manually verified

**Export Allowed with Warnings if:**
1. APR verification failed (service unavailable)
2. Confidence score between 60-80%
3. Non-critical field missing (e.g., buyer address)

### 4.10 Accounting Intent Layer

This section defines the **AccountingIntent** - a critical domain model that sits between raw invoice extraction and accounting system export. This transforms Saldora from an "OCR tool" into an "accounting intelligence platform".

#### 4.10.1 Overview

The AccountingIntent layer bridges the gap between extracted invoice data and accounting semantics:

```
┌──────────────┐    ┌──────────────────┐    ┌───────────────────┐    ┌─────────────┐
│   Document   │    │   Extracted      │    │   Accounting      │    │   Export    │
│   Upload     │───▶│   Invoice Data   │───▶│   Intent          │───▶│   (Konta,   │
│              │    │   (OCR + NER)    │    │   (Semantics)     │    │   PDV, ERP) │
└──────────────┘    └──────────────────┘    └───────────────────┘    └─────────────┘
                                                     │
                                                     │ Includes:
                                                     │ • Document classification
                                                     │ • VAT treatment decision
                                                     │ • Suggested konta
                                                     │ • PDV book mapping
                                                     │ • Transaction type
```

#### 4.10.2 AccountingIntent Data Model

| Field | Type | Description | Required |
|-------|------|-------------|----------|
| id | UUID | Unique identifier | Yes |
| invoice_id | UUID | Reference to source invoice | Yes |
| document_type | Enum | Classification of document | Yes |
| transaction_type | Enum | Nature of transaction | Yes |
| vat_treatment | Enum | How VAT should be handled | Yes |
| vat_breakdown | JSON | VAT amounts per rate | Yes |
| suggested_konta | JSON | Suggested account codes | Yes |
| pdv_book_entries | JSON | PDV-PP field mappings | Yes |
| is_deductible | Boolean | VAT deductibility flag | Yes |
| confidence | Decimal | AI confidence in classification | Yes |
| requires_review | Boolean | Needs human verification | Yes |
| reviewed_by | UUID | User who verified (if reviewed) | No |
| reviewed_at | Timestamp | When verified | No |
| notes | Text | Accountant notes | No |

**Document Types:**

| Value | Serbian | Description |
|-------|---------|-------------|
| `INPUT_INVOICE` | Ulazna faktura | Invoice received from supplier |
| `OUTPUT_INVOICE` | Izlazna faktura | Invoice issued to customer |
| `CREDIT_NOTE_IN` | Knjižno odobrenje (primljeno) | Credit note received |
| `CREDIT_NOTE_OUT` | Knjižno odobrenje (izdato) | Credit note issued |
| `DEBIT_NOTE_IN` | Knjižno zaduženje (primljeno) | Debit note received |
| `DEBIT_NOTE_OUT` | Knjižno zaduženje (izdato) | Debit note issued |
| `ADVANCE_INVOICE` | Avansna faktura | Advance payment invoice |
| `FINAL_INVOICE` | Konačna faktura | Final invoice (after advance) |
| `PROFORMA` | Profaktura | Proforma invoice (non-booking) |

**Transaction Types:**

| Value | Serbian | VAT Implication |
|-------|---------|-----------------|
| `DOMESTIC` | Domaći promet | Standard Serbian VAT applies |
| `FOREIGN_EU` | Uvoz/Izvoz EU | EU VAT rules, potential reverse charge |
| `FOREIGN_NON_EU` | Uvoz/Izvoz van EU | Import VAT or zero-rated export |
| `REVERSE_CHARGE` | Obrnuta naplata | Buyer accounts for VAT |
| `EXEMPT` | Oslobođeno PDV | VAT exempt transaction |
| `INTERNAL` | Interni prenos | Internal transfer (same PIB) |

**VAT Treatment:**

| Value | Description | PDV-PP Field |
|-------|-------------|--------------|
| `DEDUCTIBLE_FULL` | Fully deductible input VAT | Polje 8 |
| `DEDUCTIBLE_PARTIAL` | Partially deductible (mixed use) | Calculated |
| `NON_DEDUCTIBLE` | Non-deductible (entertainment, etc.) | N/A |
| `OUTPUT_STANDARD` | Output VAT at standard rate | Polje 3 |
| `OUTPUT_REDUCED` | Output VAT at reduced rate | Polje 4 |
| `OUTPUT_EXEMPT` | Exempt output (export, etc.) | Polje 6 |
| `REVERSE_CHARGE_IN` | Reverse charge (buyer side) | Polje 8a |
| `REVERSE_CHARGE_OUT` | Reverse charge (seller side) | Polje 6a |

#### 4.10.3 Suggested Konta (Account Codes)

The system SHOULD suggest appropriate account codes based on:
- Document type
- Transaction type
- Line item descriptions
- Historical patterns for this supplier/customer
- Organization's chart of accounts

**Standard Konta Suggestions (Serbian Kontni Plan):**

| Scenario | Suggested Konta | Description |
|----------|-----------------|-------------|
| Input invoice - Services | 5xx (e.g., 533) | Expense - Services |
| Input invoice - Goods | 5xx (e.g., 501) | Expense - Cost of goods |
| Input invoice - VAT | 270 | Input VAT receivable |
| Input invoice - Payable | 433 | Accounts payable |
| Output invoice - Revenue | 6xx (e.g., 601) | Revenue - Sales |
| Output invoice - VAT | 470 | Output VAT payable |
| Output invoice - Receivable | 204 | Accounts receivable |
| Advance received | 430 | Advances from customers |
| Advance paid | 150 | Advances to suppliers |

**Konta Suggestion Data Structure:**

```json
{
  "suggested_konta": {
    "debit": [
      {
        "konto": "5330",
        "description": "Usluge održavanja",
        "amount": 50000.00,
        "confidence": 0.92,
        "source": "keyword_match",
        "keywords_matched": ["održavanje", "servis"]
      },
      {
        "konto": "2700",
        "description": "PDV u primljenim fakturama",
        "amount": 10000.00,
        "confidence": 1.00,
        "source": "vat_calculation"
      }
    ],
    "credit": [
      {
        "konto": "4330",
        "description": "Dobavljači u zemlji",
        "amount": 60000.00,
        "confidence": 0.95,
        "source": "document_type"
      }
    ]
  }
}
```

#### 4.10.4 PDV Book Mapping

The system MUST map invoice data to correct PDV book entries:

**KPR (Knjiga Primljenih Obračuna) - Received Invoices:**

| KPR Field | Source | Calculation |
|-----------|--------|-------------|
| Redni broj | Auto-increment | Sequential |
| Datum prijema | invoice.created_at | Import date |
| Datum fakture | invoice.invoice_date | From OCR |
| Broj fakture | invoice.invoice_number | From OCR |
| PIB isporučioca | seller.pib | Verified via APR |
| Naziv isporučioca | seller.name | From OCR/APR |
| Osnovica 20% | vat_breakdown.rate_20.base | Calculated |
| PDV 20% | vat_breakdown.rate_20.tax | Calculated |
| Osnovica 10% | vat_breakdown.rate_10.base | Calculated |
| PDV 10% | vat_breakdown.rate_10.tax | Calculated |
| Ukupno | invoice.total_amount | Validated |

**KIR (Knjiga Izdatih Obračuna) - Issued Invoices:**

| KIR Field | Source |
|-----------|--------|
| Redni broj | Auto-increment |
| Datum fakture | invoice.invoice_date |
| Broj fakture | invoice.invoice_number |
| PIB kupca | buyer.pib |
| Naziv kupca | buyer.name |
| (Same VAT fields as KPR) | |

**PDV-PP Mapping:**

```json
{
  "pdv_book_entries": {
    "book_type": "KPR",
    "period": "2025-01",
    "pp_pdv_fields": {
      "polje_8_1": 50000.00,    // Nabavke sa PDV 20% - osnovica
      "polje_8_2": 10000.00,    // Nabavke sa PDV 20% - PDV
      "polje_9_1": 0.00,        // Nabavke sa PDV 10% - osnovica
      "polje_9_2": 0.00         // Nabavke sa PDV 10% - PDV
    },
    "kpo_entry": {
      "sequence": 42,
      "entry_date": "2025-01-15",
      "invoice_date": "2025-01-10",
      "invoice_number": "2025-0001",
      "supplier_pib": "123456789",
      "supplier_name": "Dobavljač ABC d.o.o.",
      "base_20": 50000.00,
      "vat_20": 10000.00,
      "base_10": 0.00,
      "vat_10": 0.00,
      "total": 60000.00
    }
  }
}
```

#### 4.10.5 AccountingIntent Generation Pipeline

```
┌─────────────────────────────────────────────────────────────────────┐
│                AccountingIntent Generation Pipeline                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐                                                   │
│  │ Extracted    │                                                   │
│  │ Invoice      │                                                   │
│  └──────┬───────┘                                                   │
│         │                                                           │
│         ▼                                                           │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ Step 1: Document Classification                              │  │
│  │ ────────────────────────────────────────────────────────────│  │
│  │ • Analyze seller/buyer PIB relationship to organization     │  │
│  │ • Check for credit note indicators ("odobrenje", "storno")  │  │
│  │ • Detect advance invoice patterns                           │  │
│  │ • Identify proforma indicators                              │  │
│  └──────────────────────────────────────────────────────────────┘  │
│         │                                                           │
│         ▼                                                           │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ Step 2: Transaction Type Detection                           │  │
│  │ ────────────────────────────────────────────────────────────│  │
│  │ • Check if seller/buyer PIB is foreign (non-Serbian format) │  │
│  │ • Detect EU VAT numbers (country prefix)                    │  │
│  │ • Identify reverse charge indicators in text                │  │
│  │ • Check for export documentation                            │  │
│  └──────────────────────────────────────────────────────────────┘  │
│         │                                                           │
│         ▼                                                           │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ Step 3: VAT Treatment Decision                               │  │
│  │ ────────────────────────────────────────────────────────────│  │
│  │ • Apply organization's deductibility rules                  │  │
│  │ • Check line item categories for non-deductible expenses    │  │
│  │ • Calculate partial deduction if applicable                 │  │
│  │ • Apply reverse charge rules if foreign transaction         │  │
│  └──────────────────────────────────────────────────────────────┘  │
│         │                                                           │
│         ▼                                                           │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ Step 4: Konta Suggestion                                     │  │
│  │ ────────────────────────────────────────────────────────────│  │
│  │ • Match line item descriptions to expense categories        │  │
│  │ • Check supplier history for this organization              │  │
│  │ • Apply organization's custom rules (Section 4.11)          │  │
│  │ • Generate balanced debit/credit entries                    │  │
│  └──────────────────────────────────────────────────────────────┘  │
│         │                                                           │
│         ▼                                                           │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ Step 5: Review Flag Decision                                 │  │
│  │ ────────────────────────────────────────────────────────────│  │
│  │ • Flag if overall confidence < 80%                          │  │
│  │ • Flag if transaction type is unusual for this supplier     │  │
│  │ • Flag if konta suggestion is new (never used before)       │  │
│  │ • Flag if amount exceeds organization threshold             │  │
│  └──────────────────────────────────────────────────────────────┘  │
│         │                                                           │
│         ▼                                                           │
│  ┌──────────────┐                                                   │
│  │ Accounting   │                                                   │
│  │ Intent       │                                                   │
│  └──────────────┘                                                   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

#### 4.10.6 Database Schema

```sql
CREATE TABLE accounting_intents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_id UUID NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    organization_id UUID NOT NULL REFERENCES organizations(id),

    -- Classification
    document_type VARCHAR(30) NOT NULL,
    transaction_type VARCHAR(30) NOT NULL,
    vat_treatment VARCHAR(30) NOT NULL,
    is_deductible BOOLEAN NOT NULL DEFAULT TRUE,

    -- VAT Breakdown
    vat_breakdown JSONB NOT NULL DEFAULT '{}',
    -- Example: {"rate_20": {"base": 50000, "tax": 10000}, "rate_10": {"base": 0, "tax": 0}}

    -- Suggested Konta
    suggested_konta JSONB NOT NULL DEFAULT '{}',
    -- Structure as shown in 4.10.3

    -- PDV Book Mapping
    pdv_book_entries JSONB NOT NULL DEFAULT '{}',
    -- Structure as shown in 4.10.4

    -- Confidence & Review
    confidence DECIMAL(5, 2) NOT NULL,
    requires_review BOOLEAN NOT NULL DEFAULT FALSE,
    review_reasons JSONB DEFAULT '[]',
    reviewed_by UUID REFERENCES users(id),
    reviewed_at TIMESTAMP WITH TIME ZONE,

    -- Applied Rules (for audit)
    applied_rules JSONB DEFAULT '[]',
    -- References to rules from 4.11 that were applied

    -- Accountant notes
    notes TEXT,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT valid_document_type CHECK (document_type IN (
        'INPUT_INVOICE', 'OUTPUT_INVOICE',
        'CREDIT_NOTE_IN', 'CREDIT_NOTE_OUT',
        'DEBIT_NOTE_IN', 'DEBIT_NOTE_OUT',
        'ADVANCE_INVOICE', 'FINAL_INVOICE', 'PROFORMA'
    )),
    CONSTRAINT valid_transaction_type CHECK (transaction_type IN (
        'DOMESTIC', 'FOREIGN_EU', 'FOREIGN_NON_EU',
        'REVERSE_CHARGE', 'EXEMPT', 'INTERNAL'
    )),
    CONSTRAINT valid_vat_treatment CHECK (vat_treatment IN (
        'DEDUCTIBLE_FULL', 'DEDUCTIBLE_PARTIAL', 'NON_DEDUCTIBLE',
        'OUTPUT_STANDARD', 'OUTPUT_REDUCED', 'OUTPUT_EXEMPT',
        'REVERSE_CHARGE_IN', 'REVERSE_CHARGE_OUT'
    ))
);

CREATE INDEX idx_accounting_intents_invoice ON accounting_intents(invoice_id);
CREATE INDEX idx_accounting_intents_org ON accounting_intents(organization_id);
CREATE INDEX idx_accounting_intents_review ON accounting_intents(requires_review) WHERE requires_review = TRUE;
CREATE INDEX idx_accounting_intents_type ON accounting_intents(document_type, transaction_type);
```

#### 4.10.7 Non-Deductible Expense Categories

The system MUST recognize and flag non-deductible VAT expenses per Serbian tax law:

| Category | Serbian | Examples | VAT Deductible |
|----------|---------|----------|----------------|
| Representation | Reprezentacija | Restaurants, gifts > threshold | 50% |
| Employee benefits | Benefiti zaposlenih | Private use of company car | 0% |
| Entertainment | Zabava | Events, sponsorships | 0% |
| Personal use | Lična upotreba | Mixed business/personal | Proportional |
| Exempt supplies | Oslobođene isporuke | Banking, insurance services | 0% |

**Detection Keywords:**

```python
NON_DEDUCTIBLE_PATTERNS = {
    "reprezentacija": {
        "keywords": ["ručak", "večera", "restoran", "kafić", "poklon", "dar"],
        "deductibility": 0.50,
        "vat_treatment": "DEDUCTIBLE_PARTIAL"
    },
    "gorivo_putničko": {
        "keywords": ["gorivo", "benzin", "dizel", "gas"],
        "vehicle_type_check": True,  # Check if passenger vehicle
        "deductibility": 0.00,
        "vat_treatment": "NON_DEDUCTIBLE"
    },
    "zabava": {
        "keywords": ["sponzorstvo", "donacija", "event", "proslava"],
        "deductibility": 0.00,
        "vat_treatment": "NON_DEDUCTIBLE"
    }
}
```

### 4.11 Automation Rules Engine

This section defines the office-specific rules engine that allows accounting offices to customize invoice processing with their own heuristics.

#### 4.11.1 Overview

The Rules Engine enables accountants to define custom automation rules that:
- Auto-assign konta based on supplier or keywords
- Flag invoices for review based on custom criteria
- Set default VAT treatment for specific scenarios
- Automate repetitive classification decisions

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Rules Engine Architecture                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────────┐    ┌──────────────────┐    ┌───────────────┐  │
│  │ Invoice Data     │───▶│  Rules Engine    │───▶│ Accounting    │  │
│  │ + Extracted      │    │                  │    │ Intent        │  │
│  │   Fields         │    │  1. Evaluate     │    │ (Modified)    │  │
│  └──────────────────┘    │     conditions   │    └───────────────┘  │
│                          │  2. Apply        │                       │
│                          │     actions      │    ┌───────────────┐  │
│  ┌──────────────────┐    │  3. Log applied  │───▶│ Audit Log     │  │
│  │ Organization     │───▶│     rules        │    │ (Which rules  │  │
│  │ Rules            │    │                  │    │  were applied)│  │
│  └──────────────────┘    └──────────────────┘    └───────────────┘  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

#### 4.11.2 Rule Structure

| Field | Type | Description | Required |
|-------|------|-------------|----------|
| id | UUID | Unique identifier | Yes |
| organization_id | UUID | Owner organization | Yes |
| name | String | Human-readable rule name | Yes |
| description | String | What this rule does | No |
| rule_type | Enum | Type of rule | Yes |
| priority | Integer | Execution order (lower = first) | Yes |
| conditions | JSON | When rule applies | Yes |
| actions | JSON | What rule does | Yes |
| is_active | Boolean | Rule enabled | Yes |
| created_by | UUID | User who created | Yes |
| stats | JSON | Execution statistics | No |

**Rule Types:**

| Type | Description | Use Case |
|------|-------------|----------|
| `KONTO_ASSIGNMENT` | Assign specific konto | "Invoices from supplier X → konto 5330" |
| `VAT_TREATMENT` | Set VAT handling | "Fuel invoices → non-deductible" |
| `AUTO_APPROVE` | Skip review | "Invoices < 5000 RSD → auto-approve" |
| `FLAG_FOR_REVIEW` | Force review | "New supplier → always review" |
| `DOCUMENT_TYPE` | Override classification | "Supplier Y always sends credit notes" |
| `CUSTOM_FIELD` | Set metadata | "Add cost center based on project code" |

#### 4.11.3 Condition Syntax

Conditions use a structured JSON format that supports:

**Field Conditions:**

```json
{
  "conditions": {
    "operator": "AND",
    "rules": [
      {
        "field": "seller.pib",
        "operator": "equals",
        "value": "123456789"
      },
      {
        "field": "total_amount",
        "operator": "greater_than",
        "value": 10000
      }
    ]
  }
}
```

**Available Operators:**

| Operator | Description | Applicable To |
|----------|-------------|---------------|
| `equals` | Exact match | All fields |
| `not_equals` | Not equal | All fields |
| `contains` | Substring match | String fields |
| `starts_with` | Prefix match | String fields |
| `ends_with` | Suffix match | String fields |
| `regex` | Regex pattern | String fields |
| `greater_than` | > value | Numeric fields |
| `less_than` | < value | Numeric fields |
| `between` | Range inclusive | Numeric/Date fields |
| `in` | Value in list | All fields |
| `not_in` | Value not in list | All fields |
| `is_null` | Field is empty | All fields |
| `is_not_null` | Field has value | All fields |

**Available Fields:**

| Field Path | Type | Description |
|------------|------|-------------|
| `seller.pib` | String | Seller PIB |
| `seller.name` | String | Seller name |
| `buyer.pib` | String | Buyer PIB |
| `buyer.name` | String | Buyer name |
| `total_amount` | Decimal | Invoice total |
| `subtotal` | Decimal | Amount before tax |
| `tax_rate` | Decimal | VAT rate |
| `currency` | String | Currency code |
| `invoice_date` | Date | Invoice date |
| `line_items[].description` | String | Any line item description |
| `line_items[].total` | Decimal | Any line item total |
| `document_type` | Enum | Detected document type |
| `is_first_from_supplier` | Boolean | New supplier flag |
| `supplier_invoice_count` | Integer | Historical count |

**Logical Operators:**

```json
{
  "conditions": {
    "operator": "OR",
    "rules": [
      {
        "operator": "AND",
        "rules": [
          {"field": "seller.pib", "operator": "equals", "value": "111111111"},
          {"field": "total_amount", "operator": "greater_than", "value": 50000}
        ]
      },
      {
        "field": "line_items[].description",
        "operator": "contains",
        "value": "gorivo"
      }
    ]
  }
}
```

#### 4.11.4 Action Syntax

Actions define what happens when conditions match:

**Konto Assignment:**

```json
{
  "actions": [
    {
      "type": "SET_KONTO",
      "target": "expense",
      "value": "5330",
      "description": "IT usluge"
    },
    {
      "type": "SET_KONTO",
      "target": "vat_input",
      "value": "2700"
    }
  ]
}
```

**VAT Treatment:**

```json
{
  "actions": [
    {
      "type": "SET_VAT_TREATMENT",
      "value": "NON_DEDUCTIBLE",
      "reason": "Gorivo za putnička vozila"
    }
  ]
}
```

**Flag for Review:**

```json
{
  "actions": [
    {
      "type": "FLAG_REVIEW",
      "reason": "Faktura preko 100.000 RSD - potrebna dodatna provera",
      "assign_to": "senior_accountant"
    }
  ]
}
```

**Auto-Approve:**

```json
{
  "actions": [
    {
      "type": "AUTO_APPROVE",
      "skip_review": true,
      "conditions_verified": ["amount_threshold", "known_supplier"]
    }
  ]
}
```

**Set Custom Field:**

```json
{
  "actions": [
    {
      "type": "SET_CUSTOM_FIELD",
      "field": "cost_center",
      "value": "IT-001"
    },
    {
      "type": "SET_CUSTOM_FIELD",
      "field": "project_code",
      "value_from_field": "line_items[0].description",
      "regex_extract": "PRJ-([A-Z0-9]+)"
    }
  ]
}
```

#### 4.11.5 Example Rules

**Rule 1: Telecom Provider → Specific Konto**

```json
{
  "name": "Telekom Srbija - Telefonija",
  "description": "Sve fakture od Telekoma idu na konto 5210 (PTT troškovi)",
  "rule_type": "KONTO_ASSIGNMENT",
  "priority": 10,
  "conditions": {
    "operator": "AND",
    "rules": [
      {"field": "seller.pib", "operator": "in", "value": ["100002534", "100002535"]},
      {"field": "document_type", "operator": "equals", "value": "INPUT_INVOICE"}
    ]
  },
  "actions": [
    {"type": "SET_KONTO", "target": "expense", "value": "5210", "description": "PTT troškovi"},
    {"type": "SET_VAT_TREATMENT", "value": "DEDUCTIBLE_FULL"}
  ]
}
```

**Rule 2: Fuel Invoices → Non-Deductible**

```json
{
  "name": "Gorivo - putnička vozila",
  "description": "PDV na gorivo za putnička vozila nije priznat",
  "rule_type": "VAT_TREATMENT",
  "priority": 5,
  "conditions": {
    "operator": "AND",
    "rules": [
      {"field": "line_items[].description", "operator": "regex", "value": "(gorivo|benzin|dizel|nafta)"},
      {"field": "seller.name", "operator": "regex", "value": "(NIS|MOL|OMV|Petrol|Lukoil)"}
    ]
  },
  "actions": [
    {"type": "SET_VAT_TREATMENT", "value": "NON_DEDUCTIBLE", "reason": "Gorivo za putnička vozila - PDV se ne priznaje"},
    {"type": "SET_KONTO", "target": "expense", "value": "5130", "description": "Troškovi goriva"}
  ]
}
```

**Rule 3: Large Invoice → Senior Review**

```json
{
  "name": "Velike fakture - pregled",
  "description": "Fakture preko 500.000 RSD zahtevaju pregled starijeg računovođe",
  "rule_type": "FLAG_FOR_REVIEW",
  "priority": 1,
  "conditions": {
    "operator": "AND",
    "rules": [
      {"field": "total_amount", "operator": "greater_than", "value": 500000},
      {"field": "currency", "operator": "equals", "value": "RSD"}
    ]
  },
  "actions": [
    {"type": "FLAG_REVIEW", "reason": "Faktura prelazi 500.000 RSD", "assign_to_role": "manager"}
  ]
}
```

**Rule 4: New Supplier → Always Review**

```json
{
  "name": "Novi dobavljač",
  "description": "Prve fakture od novih dobavljača uvek pregledati",
  "rule_type": "FLAG_FOR_REVIEW",
  "priority": 2,
  "conditions": {
    "operator": "AND",
    "rules": [
      {"field": "is_first_from_supplier", "operator": "equals", "value": true}
    ]
  },
  "actions": [
    {"type": "FLAG_REVIEW", "reason": "Prvi put primamo fakturu od ovog dobavljača"}
  ]
}
```

**Rule 5: Small Invoice Auto-Approve**

```json
{
  "name": "Male fakture - automatski",
  "description": "Fakture ispod 5.000 RSD od poznatih dobavljača idu automatski",
  "rule_type": "AUTO_APPROVE",
  "priority": 100,
  "conditions": {
    "operator": "AND",
    "rules": [
      {"field": "total_amount", "operator": "less_than", "value": 5000},
      {"field": "supplier_invoice_count", "operator": "greater_than", "value": 5},
      {"field": "confidence", "operator": "greater_than", "value": 0.90}
    ]
  },
  "actions": [
    {"type": "AUTO_APPROVE", "skip_review": true}
  ]
}
```

#### 4.11.6 Database Schema

```sql
CREATE TABLE automation_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),

    -- Rule definition
    name VARCHAR(255) NOT NULL,
    description TEXT,
    rule_type VARCHAR(30) NOT NULL,
    priority INTEGER NOT NULL DEFAULT 50,

    -- Rule logic (JSON)
    conditions JSONB NOT NULL,
    actions JSONB NOT NULL,

    -- Status
    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    -- Metadata
    created_by UUID NOT NULL REFERENCES users(id),
    updated_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Statistics
    execution_count INTEGER DEFAULT 0,
    last_executed_at TIMESTAMP WITH TIME ZONE,

    CONSTRAINT valid_rule_type CHECK (rule_type IN (
        'KONTO_ASSIGNMENT', 'VAT_TREATMENT', 'AUTO_APPROVE',
        'FLAG_FOR_REVIEW', 'DOCUMENT_TYPE', 'CUSTOM_FIELD'
    )),
    CONSTRAINT unique_rule_name_per_org UNIQUE (organization_id, name)
);

CREATE INDEX idx_rules_org ON automation_rules(organization_id);
CREATE INDEX idx_rules_active ON automation_rules(organization_id, is_active) WHERE is_active = TRUE;
CREATE INDEX idx_rules_type ON automation_rules(rule_type);

-- Rule execution log for audit
CREATE TABLE rule_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_id UUID NOT NULL REFERENCES automation_rules(id),
    invoice_id UUID NOT NULL REFERENCES invoices(id),
    accounting_intent_id UUID REFERENCES accounting_intents(id),

    -- Execution details
    conditions_matched JSONB NOT NULL,  -- Which conditions were true
    actions_applied JSONB NOT NULL,     -- What actions were taken

    -- Timing
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    execution_time_ms INTEGER
);

CREATE INDEX idx_rule_exec_rule ON rule_executions(rule_id);
CREATE INDEX idx_rule_exec_invoice ON rule_executions(invoice_id);
CREATE INDEX idx_rule_exec_date ON rule_executions(executed_at);
```

#### 4.11.7 Rule Evaluation Order

Rules are evaluated in the following order:

1. **Priority order** (lower number = higher priority)
2. **Within same priority**: By creation date (older first)
3. **Rule type precedence** for conflicts:
   - `FLAG_FOR_REVIEW` always applies (additive)
   - `AUTO_APPROVE` can be overridden by `FLAG_FOR_REVIEW`
   - `KONTO_ASSIGNMENT` - last matching rule wins
   - `VAT_TREATMENT` - last matching rule wins

**Conflict Resolution:**

```
IF multiple KONTO_ASSIGNMENT rules match:
    Use rule with lowest priority number
    Log warning about conflict

IF AUTO_APPROVE and FLAG_FOR_REVIEW both match:
    FLAG_FOR_REVIEW wins (safety first)
    Log both rules in audit trail
```

#### 4.11.8 Rule Templates

The system SHOULD provide pre-built rule templates for common Serbian accounting scenarios:

| Template | Description |
|----------|-------------|
| `fuel_non_deductible` | Fuel invoices → non-deductible VAT |
| `telecom_expenses` | Telecom providers → PTT expense konto |
| `office_supplies` | Office supply vendors → material expense |
| `professional_services` | Consulting/legal → service expense |
| `utilities` | Utility companies → utility expense konto |
| `rent_payments` | Rent invoices → rent expense |
| `large_invoice_review` | High-value invoice review threshold |
| `new_supplier_review` | First invoice from new supplier |
| `foreign_supplier_review` | Non-Serbian supplier review |

### 4.12 Client Management (Agency)

Client Management is the **central organizational entity for agency users** post-pivot. The agency's "clients" are the hospitality businesses the agency serves; every invoice, every event, every report, and every per-client rule is scoped to one client.

This section defines the data model and CRUD surface. The UX surface that makes this load-bearing — the per-client workspace, timeline, and tab structure — is documented in Section 4.18 (Client-First UI).

**Feature Gate:** Available on the Agency plan. Other plans use a single implicit "self" client.

#### FR-4.12.1 Client CRUD
| ID | FR-4.12.1 |
|----|-----------|
| **Description** | System MUST allow Agency-plan users to create, list, update, deactivate, and delete clients |
| **Create** | Name (required), PIB (required, unique per organization, validated format), contact email, address, notes |
| **List** | Paginated list with search by name or PIB; supports `?search=` and `?page=`/`?page_size=` query params |
| **Update** | All client fields except `organization_id` and `id` |
| **Toggle Active** | `POST /clients/{id}/toggle-active` flips `is_active`; deactivated clients are hidden from the selector but data is retained |
| **Hard Delete** | `DELETE /clients/{id}` permanently removes the client record and sets `client_id = NULL` on all linked invoices and line items; no soft-delete |
| **Authorization** | Only users in organizations with `CLIENT_MANAGEMENT` feature flag enabled |

#### FR-4.12.2 Invoice Auto-Assignment via PIB Matching
| ID | FR-4.12.2 |
|----|-----------|
| **Description** | The system MUST automatically assign invoices to the matching client based on the seller PIB, both during OCR processing and retroactively when a new client is created |
| **Matching Logic** | Compare `seller.pib` against all active clients' PIBs within the same organization |
| **Match Found** | Set `invoice.client_id` to the matched client's ID |
| **No Match** | Leave `invoice.client_id` as NULL; invoice remains unassigned |
| **Timing (OCR)** | Assignment occurs during the post-OCR processing pipeline, before the invoice is saved |
| **Timing (Retroactive)** | When a new client is created, the system immediately searches for existing unassigned invoices (`client_id IS NULL`) whose `seller.pib` matches the new client's PIB and assigns them |

#### FR-4.12.3 Invoice Scoping by Client
| ID | FR-4.12.3 |
|----|-----------|
| **Description** | System MUST support filtering invoices by `client_id` |
| **Query Parameter** | `GET /invoices?client_id={uuid}` returns only invoices assigned to that client |
| **No Filter** | When `client_id` is omitted, all organization invoices are returned |
| **Authorization** | Client MUST belong to the requesting user's organization |

#### FR-4.12.4 Client Workspace (replaces sidebar selector)

The previous sidebar client selector has been **superseded** by the per-client workspace introduced in M19 (see Section 4.18). Instead of filtering global lists by a sticky selector, agency users navigate to `/klijenti/{id}` and find every per-client view (invoices, reports, rules, timeline) pre-scoped within that workspace. The Portfolio view at `/pregled` is the agency-wide home and primary entry point.

#### FR-4.12.5 Client Event Log

| ID | FR-4.12.5 |
|----|-----------|
| **Description** | The system MUST maintain an append-only event log per client to power the timeline view |
| **Model** | `client_events` table — `id`, `organization_id`, `client_id`, `event_type`, `entity_type`, `entity_id`, `metadata` (JSONB), `created_by`, `created_at` |
| **Event types at launch** | `invoice_uploaded`, `invoice_verified`, `invoice_exported`, `accounting_intent_classified`, `rule_fired`, `client_assigned` |
| **Future event types** | `form_generated`, `period_closed`, etc. (added as new milestones land) |
| **Emission** | Events are emitted from the existing write sites: invoice upload pipeline, verify endpoint, export endpoints, accounting-intent classification step, rules engine execution, client assignment (manual or PIB-match) |
| **Backfill** | A one-shot backfill script populates historical events from `audit_logs`, `correction_logs`, and `invoices` so timelines are not empty at deploy time |
| **API** | `GET /api/v1/clients/{id}/events?period=YYYY-MM&type=...` — paginated, filterable by event type, sorted reverse-chronological |
| **Append-only** | No update/delete operations; events are immutable history |

#### FR-4.12.6 Per-Client Automation Rules

| ID | FR-4.12.6 |
|----|-----------|
| **Description** | Automation rules (Section 4.11) MAY be scoped to one or more specific clients, or remain global within the organization |
| **Model** | `rule_client_associations` join table — `rule_id`, `client_id`, `created_at` |
| **Default** | A rule with no associations applies organization-wide; a rule with one or more associations applies only when the invoice's `client_id` matches one of the associated client IDs |
| **UI** | Rules listed inside `/klijenti/{id}` Pravila tab show only rules associated with this client + global rules; a "Create rule for this client" CTA pre-fills the association |
| **Org-wide editor** | Sidebar entry `Pravila` shows all rules and exposes per-rule client associations |

---

### 4.13 Invoice Reports (Izveštaji)

This section defines the Invoice Reports feature, which replaces the previously planned PDV book generation (KPR/KIR) milestone. Reports provide five pre-built analytical views over a denormalized `invoice_line_items` table. All reports are generated by pure SQL aggregation — no LLM calls are made.

**Feature Gate:** The Reports feature is gated behind the `REPORTS` feature flag, which MUST be enabled for Professional and Agency plans. Starter-plan users receive a 403 response.

#### 4.13.1 Denormalized Line Items Table

To avoid unpacking JSON on every report query, the system maintains a dedicated `invoice_line_items` table that mirrors line items from processed invoices.

**Population rules:**
- Populated non-blocking immediately after OCR processing completes (the worker writes rows after saving the invoice).
- Re-populated (delete + re-insert for the affected invoice) whenever the user saves edits to line items on the invoice detail page.
- Scoped by `organization_id` on every query.

**Table schema:**

```sql
CREATE TABLE invoice_line_items (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    invoice_id    UUID NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    client_id     UUID REFERENCES clients(id) ON DELETE SET NULL,  -- nullable; set via PIB matching
    description   TEXT,
    quantity      NUMERIC(12, 4),
    unit_price    NUMERIC(15, 4),
    total         NUMERIC(15, 2),
    tax_rate      NUMERIC(5, 2),
    currency      VARCHAR(3) NOT NULL DEFAULT 'RSD',
    supplier_name TEXT,
    supplier_pib  VARCHAR(20),
    invoice_date  DATE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_invoice_line_items_org     ON invoice_line_items(organization_id);
CREATE INDEX ix_invoice_line_items_invoice ON invoice_line_items(invoice_id);
CREATE INDEX ix_invoice_line_items_date    ON invoice_line_items(invoice_date);
CREATE INDEX ix_invoice_line_items_supplier ON invoice_line_items(supplier_pib);
CREATE INDEX ix_ili_client_id              ON invoice_line_items(client_id);
```

#### 4.13.2 Report Templates

All report endpoints live under `/api/v1/reports/` and accept a common set of query parameters:

| Parameter | Type | Description |
|-----------|------|-------------|
| `date_from` | `YYYY-MM-DD` | Start of reporting period (required) |
| `date_to` | `YYYY-MM-DD` | End of reporting period (required) |
| `supplier_pib` | String | Optional — filter to a single supplier |
| `search` | String | Optional — keyword filter on item description (case-insensitive) |
| `client_id` | UUID | Optional — filter to a specific agency client (Agency plan only; ignored on other plans) |

##### FR-4.13.2.1 Received Goods Report (`/received-goods`)

| ID | FR-4.13.2.1 |
|----|-------------|
| **Description** | Groups line items by description, sums quantity and total amount, and lists all unique suppliers that supplied each item |
| **Group by** | `description` (case-insensitive, trimmed) |
| **Aggregates** | `SUM(quantity)`, `SUM(total)`, `array_agg(DISTINCT supplier_name)` |
| **Use case** | "How much of product X did we receive, and from which suppliers?" |

##### FR-4.13.2.2 Spending by Supplier (`/spending-by-supplier`)

| ID | FR-4.13.2.2 |
|----|-------------|
| **Description** | Returns total invoice amount spent per supplier over the selected period |
| **Group by** | `supplier_pib`, `supplier_name` |
| **Aggregates** | `SUM(total)`, `COUNT(DISTINCT invoice_id)` |
| **Use case** | "Who are our top suppliers by spend?" |

##### FR-4.13.2.3 Monthly Breakdown (`/monthly-breakdown`)

| ID | FR-4.13.2.3 |
|----|-------------|
| **Description** | Paginated flat list of all individual line items for the selected period |
| **Sort** | `invoice_date DESC`, then `supplier_name ASC` |
| **Pagination** | `?page=` and `?page_size=` (default 50 rows per page) |
| **Use case** | "Show me everything we bought in March." |

##### FR-4.13.2.4 Price Comparison (`/price-comparison`)

| ID | FR-4.13.2.4 |
|----|-------------|
| **Description** | For each unique item description that appears from more than one supplier, returns min, max, and average unit price alongside the supplier list |
| **Group by** | `description` |
| **Aggregates** | `MIN(unit_price)`, `MAX(unit_price)`, `AVG(unit_price)`, `array_agg(DISTINCT supplier_name)` |
| **Filter** | Only descriptions with `COUNT(DISTINCT supplier_pib) > 1` |
| **Use case** | "Are we paying different prices for the same item from different suppliers?" |

##### FR-4.13.2.5 Expense Summary (`/expense-summary`)

| ID | FR-4.13.2.5 |
|----|-------------|
| **Description** | Expense totals grouped by month or week |
| **Group by** | `date_trunc('month', invoice_date)` or `date_trunc('week', invoice_date)`, controlled by `?group_by=month\|week` parameter |
| **Aggregates** | `SUM(total)`, `COUNT(DISTINCT invoice_id)` |
| **Use case** | "How did our spending change month by month?" |

##### FR-4.13.2.6 Price Calculation (`/kalkulacija`)

| ID | FR-4.13.2.6 |
|----|-------------|
| **Description** | Per-line-item price calculation showing purchase price (nabavna cena), margin (marža), and calculated selling price (prodajna cena) for each item |
| **Data source** | `invoice_line_items` joined with `product_catalog` via `product_id` FK |
| **Columns** | `description`, `unit_price` (nabavna cena), `default_margin_pct`, calculated `selling_price` |
| **Use case** | "What is the selling price and margin for each item we purchased?" |

##### FR-4.13.2.7 Markup Analysis — RUC (`/ruc`)

| ID | FR-4.13.2.7 |
|----|-------------|
| **Description** | Razlika u ceni (markup/margin analysis) grouped by product catalog entry |
| **Group by** | `product_id` (canonical product) |
| **Aggregates** | `AVG(unit_price)` as average purchase price, `selling_price` from catalog, calculated markup amount and percentage |
| **Use case** | "What is our markup across all purchases of each product?" |

##### FR-4.13.2.8 Spending by Category (`/spending-by-category`)

| ID | FR-4.13.2.8 |
|----|-------------|
| **Description** | Total spending grouped by product catalog category |
| **Group by** | `category` from `product_catalog` |
| **Aggregates** | `SUM(total)`, `COUNT(DISTINCT invoice_id)`, `array_agg(DISTINCT supplier_name)` |
| **Use case** | "How much did we spend in each product category?" |

##### FR-4.13.2.9 Daily Goods Tracking — Dnevna evidencija robe (`/dpu`)

| ID | FR-4.13.2.9 |
|----|-------------|
| **Description** | All line items received on a specific date (replaces former "Šank lista" / DPU page) |
| **Filter** | `invoice_date` (required — exact date) |
| **Columns** | `description`, `quantity`, `unit_price`, `total`, `supplier_name`, `invoice_number` |
| **Use case** | "What goods did we receive on a given day?" |

#### 4.13.3 CSV Export

Every report endpoint accepts an `Accept: text/csv` header (or `?format=csv` query parameter) and returns a UTF-8 BOM CSV with:

- Semicolon delimiter
- Comma as decimal separator (Serbian locale)
- Serbian column headers
- Filename: `izvestaj_{report_type}_{date_from}_{date_to}.csv`

#### 4.13.4 Frontend Page

The `/izvestaji` page is a unified hub for all reports, product catalog management, and daily goods tracking. It replaces the formerly separate `/katalog` and `/dpu` pages.

| Requirement | Detail |
|-------------|--------|
| **Route** | `/{orgSlug}/izvestaji` |
| **Navigation** | Group pills at the top: "Opšti" (5 general reports), "Nabavka i prodaja" (kalkulacija, RUC, categories, daily tracking), "Upravljanje" (product catalog) |
| **Tab layout** | Horizontal tabs within each group for individual report/management views |
| **Filters** | Date range picker, optional supplier PIB/name field, optional keyword search (per-tab) |
| **Results** | Rendered in a sortable table below the filter bar |
| **Export** | "Izvezi CSV" button — triggers browser file download |
| **Plan gate** | Non-PRO users see an upgrade modal instead of the filter form |
| **Removed pages** | `/katalog` and `/dpu` routes removed; content consolidated here |

---

<a id="414-email-ingestion-pipeline-planned"></a>
### 4.14 Email Ingestion Pipeline (planned, not yet wired)

> **Status (April 2026):** This feature is **planned** for milestone M17 but is **not yet provisioned**. No DNS records, no inbound email provider account (Postmark / Resend Inbound / SES), and no `inbound_emails` table exist in production today. The spec below is the design target; the section describes intended behavior and is retained so the implementation can land directly against it.

This section defines the Email Ingestion feature, which will allow organizations to receive invoices via a dedicated email address and automatically route them into the processing pipeline — eliminating manual upload for the majority of invoices.

**Feature Gate (planned):** Email Ingestion will be available on Professional and Agency plans.

#### 4.14.1 Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Email Ingestion Architecture                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Supplier sends invoice         Dedicated inbox                      │
│  via email                      (Postmark Inbound)                   │
│  ┌─────────┐                    ┌──────────────┐                    │
│  │ Email   │───────────────────▶│ Webhook      │                    │
│  │ + PDF   │                    │ /api/v1/     │                    │
│  │ attach  │                    │ inbound/email│                    │
│  └─────────┘                    └──────┬───────┘                    │
│                                        │                             │
│                                        ▼                             │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ Processing Pipeline                                          │   │
│  │                                                              │   │
│  │ 1. Validate sender domain / organization mapping             │   │
│  │ 2. Extract PDF/image attachments (skip .html, .sig, etc.)   │   │
│  │ 3. Upload attachments to S3                                  │   │
│  │ 4. Create invoice records (status: processing)               │   │
│  │ 5. Dispatch OCR tasks (same pipeline as manual upload)       │   │
│  │ 6. Send confirmation email to sender (optional)              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

#### 4.14.2 Dedicated Inbox

Each organization receives a unique inbound email address upon activation:

| Field | Value |
|-------|-------|
| **Format** | `{org-slug}@invoices.saldora.ai` |
| **Example** | `racunovodstvo-petrovic@invoices.saldora.ai` |
| **Provider** | Postmark Inbound (or similar: SendGrid Inbound Parse, AWS SES) |
| **Webhook** | `POST /api/v1/inbound/email` |

**Configuration (per organization):**

```json
{
  "email_ingestion": {
    "enabled": true,
    "inbound_address": "racunovodstvo-petrovic@invoices.saldora.ai",
    "allowed_sender_domains": ["*"],
    "allowed_sender_emails": [],
    "auto_process": true,
    "send_confirmation": true,
    "confirmation_language": "sr-Latn"
  }
}
```

#### 4.14.3 Inbound Email Processing

**Accepted Attachments:**

| File Type | Action |
|-----------|--------|
| PDF | Process as invoice |
| JPEG, PNG, TIFF, BMP, WEBP | Process as invoice |
| ZIP | Extract and process contained PDFs/images |
| HTML, TXT, .sig, .p7s, .vcf | Ignore (email signature artifacts) |
| Other | Ignore, log warning |

**Processing Rules:**

```
PROCESS_INBOUND_EMAIL(email):
  # 1. Identify organization from recipient address
  org = LOOKUP_ORG_BY_INBOUND_ADDRESS(email.to)
  IF NOT org:
    LOG_WARNING("Unknown inbound address", email.to)
    RETURN  # silently drop — prevents bounce loops

  # 2. Check if email ingestion is enabled
  IF NOT org.email_ingestion.enabled:
    RETURN

  # 3. Filter sender (if allowlist configured)
  IF org.allowed_sender_domains != ["*"]:
    IF sender_domain(email.from) NOT IN org.allowed_sender_domains:
      SEND_REJECTION("Vaša adresa nije odobrena za slanje faktura")
      RETURN

  # 4. Extract valid attachments
  attachments = FILTER_ATTACHMENTS(email.attachments, ACCEPTED_TYPES)
  IF NOT attachments:
    SEND_REPLY("Email nema priložene fakture (PDF ili sliku)")
    RETURN

  # 5. Check plan limits
  IF org.usage + LEN(attachments) > org.plan.invoice_limit:
    SEND_REPLY("Dostignut mesečni limit faktura")
    RETURN

  # 6. Process each attachment
  FOR EACH attachment IN attachments:
    invoice = CREATE_INVOICE(
      organization_id=org.id,
      source="email",
      source_email=email.from,
      source_subject=email.subject
    )
    UPLOAD_TO_S3(attachment, invoice.id)
    DISPATCH_OCR_TASK(invoice.id)

  # 7. Send confirmation (if enabled)
  IF org.send_confirmation:
    SEND_CONFIRMATION(
      to=email.from,
      count=LEN(attachments),
      org_name=org.name
    )
```

#### 4.14.4 Security Considerations

| Concern | Mitigation |
|---------|------------|
| Spam / unsolicited emails | Sender domain allowlist (optional), attachment type filtering |
| Malicious attachments | File type validation, virus scanning (ClamAV), size limits |
| Bounce loops | Never send auto-replies to noreply/mailer-daemon addresses |
| Rate limiting | Max 50 emails per hour per organization |
| Data privacy | Inbound email body is NOT stored — only attachments are processed |
| Email authentication | Validate SPF/DKIM on inbound emails when available |

#### 4.14.5 Database Schema

```sql
-- Track inbound email processing
CREATE TABLE inbound_emails (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),

    -- Email metadata (body NOT stored for privacy)
    sender_email VARCHAR(255) NOT NULL,
    sender_name VARCHAR(255),
    subject TEXT,
    message_id VARCHAR(500),          -- Email Message-ID header for dedup

    -- Processing
    attachment_count INTEGER NOT NULL DEFAULT 0,
    invoices_created INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'processed',
    error_message TEXT,

    -- Timestamps
    received_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT valid_inbound_status CHECK (status IN (
        'processed', 'rejected', 'error', 'no_attachments', 'limit_exceeded'
    )),
    CONSTRAINT unique_message_id UNIQUE (organization_id, message_id)
);

CREATE INDEX idx_inbound_emails_org ON inbound_emails(organization_id);
CREATE INDEX idx_inbound_emails_received ON inbound_emails(received_at);
```

**Invoice source tracking** — add `source` and `source_email` columns to `invoices` table:

```sql
ALTER TABLE invoices ADD COLUMN source VARCHAR(20) DEFAULT 'upload';
-- Values: 'upload', 'email', 'sef', 'api'
ALTER TABLE invoices ADD COLUMN source_email VARCHAR(255);
ALTER TABLE invoices ADD COLUMN source_subject TEXT;
```

#### 4.14.6 API Endpoints

##### POST /api/v1/inbound/email (Webhook)

Receives inbound email from Postmark/SendGrid. Not authenticated via JWT — uses webhook signature verification.

##### GET /api/v1/settings/email-ingestion

Returns email ingestion configuration for the current organization.

**Response:**
```json
{
  "enabled": true,
  "inbound_address": "racunovodstvo-petrovic@invoices.saldora.ai",
  "allowed_sender_domains": ["*"],
  "auto_process": true,
  "send_confirmation": true,
  "emails_received_today": 12,
  "invoices_created_today": 18
}
```

##### PUT /api/v1/settings/email-ingestion

Update email ingestion settings.

#### 4.14.7 Frontend

| Requirement | Detail |
|-------------|--------|
| **Settings location** | Settings → Integracije → "Email prijem faktura" card |
| **Display** | Show inbound address with copy button |
| **Configuration** | Toggle enable/disable, sender domain allowlist, confirmation toggle |
| **Activity log** | Recent inbound emails table (sender, subject, attachments count, status) |
| **Invoice source badge** | Invoices received via email show an email icon badge in the invoice list |

#### 4.14.8 Confirmation Email Template

```
Predmet: Primljene fakture ({count}) — Saldora

Poštovani,

Primili smo {count} faktur(u/e) poslatih na {inbound_address}.

Fakture su u obradi i biće dostupne u vašem nalogu u roku od
nekoliko minuta.

Fajlovi:
{for each attachment}
  • {filename} ({file_size})
{end for}

Pozdrav,
Saldora tim

---
Ovo je automatska poruka. Za podešavanja email prijema,
posetite Podešavanja → Integracije u aplikaciji.
```

---

### 4.15 Product Catalog (Katalog proizvoda)

This section defines the Product Catalog feature, which provides a canonical list of products that enables accurate inventory tracking, margin analysis, and price comparison for restaurant and hospitality clients.

**Feature Gate:** Product Catalog is available on Professional and Agency plans.

#### 4.15.1 Overview

The product catalog stores canonical product names with aliases (alternative names from different suppliers). When line items are linked to catalog entries, the system can normalize item descriptions across suppliers and enable procurement intelligence reports (Section 4.13.2.6–4.13.2.9).

#### 4.15.2 Database Schema

```sql
CREATE TABLE product_catalog (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    canonical_name  TEXT NOT NULL,
    unit_of_measure VARCHAR(20),
    category        VARCHAR(50),
    aliases         JSONB NOT NULL DEFAULT '[]',
    selling_price   NUMERIC(15, 2),
    default_margin_pct NUMERIC(5, 2),
    match_count     INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX ix_pc_org_name ON product_catalog(organization_id, canonical_name);
CREATE INDEX ix_pc_org_id ON product_catalog(organization_id);
CREATE INDEX ix_pc_category ON product_catalog(category);
```

**PostgreSQL `pg_trgm` extension** is used for trigram-based fuzzy matching of `description` values in `invoice_line_items` against catalog entries. This allows the system to suggest catalog matches even when supplier descriptions vary.

The `invoice_line_items` table includes a `product_id` FK column (nullable) that links a line item to its canonical catalog entry after matching.

#### 4.15.3 API Endpoints

All catalog endpoints live under `/api/v1/products/`:

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/products/` | List all catalog entries for the organization |
| `POST` | `/api/v1/products/` | Create a new catalog entry |
| `GET` | `/api/v1/products/{id}` | Retrieve a single entry |
| `PATCH` | `/api/v1/products/{id}` | Update canonical name, aliases, selling price, margin, category |
| `DELETE` | `/api/v1/products/{id}` | Delete a catalog entry |
| `GET` | `/api/v1/products/merge-suggestions` | Return pairs of catalog entries that are likely duplicates (trigram similarity above threshold) |
| `POST` | `/api/v1/products/merge` | Merge two entries: keep one as canonical, move aliases from the other, reassign `product_id` FKs |

#### 4.15.4 Matching Logic

When a new line item is written to `invoice_line_items` (at OCR completion or on edit), the system attempts to match its `description` against the catalog using `pg_trgm` trigram similarity. On a successful match (similarity ≥ 0.6), the `product_id` FK is set on the line item.

`match_count` on the catalog entry is incremented each time a line item is matched to it.

#### 4.15.5 Frontend (within /izvestaji)

Product catalog management is accessible from the "Upravljanje" group on the `/izvestaji` page:

| Feature | Detail |
|---------|--------|
| **Entry list** | Table of catalog entries with canonical name, category, aliases count, selling price, margin |
| **Add/edit entry** | Form to set canonical name, category, unit of measure, aliases (tag input), selling price, margin |
| **Merge suggestions** | Tab showing pairs of likely-duplicate entries with a "Merge" action |
| **Search/filter** | Search by canonical name or category |

---

<a id="416-in-app-support-system-planned"></a>
### 4.16 In-App Support System (planned)

> **Status (April 2026):** Planned for milestone M15. The data model, endpoints, and frontend described below are not yet built. Support today is handled out-of-band via email.

Ticket-based support system to be built into the application. Clients will create tickets from a Podrška page, attach files, and track status. Admins will manage all tickets from a dedicated admin panel.

**Feature Gate (planned):** Available on all plans.

#### 4.16.1 Data Model

**support_tickets:**
- id, organization_id, user_id (creator), subject, status (open/in_progress/resolved/closed), priority (low/normal/high), category (billing/technical/feature_request/other), created_at, updated_at

**support_messages:**
- id, ticket_id, user_id (sender), body (TEXT), is_admin_reply (BOOLEAN), created_at

**support_attachments:**
- id, message_id, file_name, file_path (S3 key), file_size, content_type, created_at

#### 4.16.2 Client Endpoints
- POST /api/v1/support/tickets — create ticket with initial message
- GET /api/v1/support/tickets — list org tickets (paginated, filterable)
- GET /api/v1/support/tickets/{id} — ticket detail with messages
- POST /api/v1/support/tickets/{id}/messages — add reply (with file attachments)
- POST /api/v1/support/tickets/{id}/close — close ticket

#### 4.16.3 Admin Endpoints
- GET /api/v1/admin/support/tickets — all tickets across orgs
- PATCH /api/v1/admin/support/tickets/{id} — update status/priority
- POST /api/v1/admin/support/tickets/{id}/messages — admin reply

#### 4.16.4 Frontend
- Client: /{orgSlug}/podrska — ticket list, create form, chat-like thread view
- Admin: /{orgSlug}/admin/podrska — cross-org ticket management
- Sidebar badge: unread reply count
- Status badges: Otvoren (green), U obradi (yellow), Rešen (blue), Zatvoren (gray)

#### 4.16.5 Notifications
- Sidebar badge for unread replies (client) and open tickets (admin)
- Optional email notification on admin reply and new ticket

---

### 4.17 Out-of-Scope / Dropped Features

This section consolidates everything that has been explicitly removed, deferred, or is permanently out of scope. It exists so future contributors do not waste time re-litigating decisions.

| Feature | Status | Rationale |
|---------|--------|-----------|
| **Paušal module** (M14) — KPO ledger, paušalci-as-customers, `direction` field on invoices, `client_type`, `customers` table, `invoice_counters`, paušal-specific routers | **Dropped, code reverted** | Paušalci are not the target market. MiniMax's dedicated paušal product handles that segment well; competing there is a multi-year battle we cannot win. |
| **Client portal** (end clients submitting documents directly) | **Dropped** | Hospitality owners are not portal users. The agency receives documents by email/WhatsApp/paper today and that channel is not Saldora's surface. The agency stays the sole user class. |
| **Compliance Watchdog** (M18) — scheduled rule evaluation producing alerts | **Dropped** | Paušal-era thinking. Rules continue to fire on events; a scheduled watchdog adds no value for hospitality agencies. |
| **Foreign reverse-charge as a standalone module** (M15) | **Deferred indefinitely** | The existing NBS conversion + AccountingIntent already handle the small volume of foreign hospitality invoices adequately. Revisit only if hospitality agencies report it as real pain. |
| **Payment tracking** (FR-4.7.4 in earlier versions) — `payment_status`, `paid_amount`, `paid_date`, open items, aging reports | **Removed** | Saldora is intelligence-only. Payment operations belong in MiniMax. |
| **Webhook notifications** (FR-4.8.2 in earlier versions) | **Deprioritized** | Webhooks become useful only after the full workflow is API-driven from the customer's side; we are not there. Paddle webhooks for billing remain in scope. |
| **SEF integration as a load-bearing input source** (M-SEF, formerly Section 12.5/12.6) | **Deprioritized** | The wedge is paper invoices SEF doesn't cover. SEF ingestion as a secondary data source remains as out-of-milestone ongoing work but is not on any active milestone and was removed from this SRS as a first-class section. |
| **Bank reconciliation, general-ledger postings, payment matching** | **Permanently out of scope** | MiniMax handles these. Saldora hands off; it does not do the books. |
| **Model retraining / fine-tuning on user data** | **Permanently out of scope** | Pre-trained models only (dots.ocr for OCR, Claude Haiku for extraction). Correction logs (Section 9.8) exist for monitoring quality, not for training. |
| **Image preprocessing for VLM** (deskewing, binarization, contrast adjustments before sending to dots.ocr) | **Disabled** | dots.ocr works best on original color images. The preprocessing pipeline that existed for traditional OCR engines is bypassed for the VLM path. |
| **EasyOCR fallback** when dots.ocr fails | **Removed** | Alternative OCR engines deliver insufficient accuracy on Serbian Cyrillic/Latin documents. If dots.ocr fails, the invoice is flagged for manual review by the user — no automatic fallback engine. |
| **Stripe integration** | **Permanently out of scope** | Stripe is unavailable in Serbia. Paddle is the Merchant of Record. Any references to Stripe in older drafts are stale. |
| **Compliance Watchdog scheduled checks** | **Dropped** | See above. |

---

<a id="418-client-first-ui-m19"></a>
### 4.18 Client-First UI (M19)

This section defines the client-first UI surface introduced in milestone M19. The previous feature-indexed UI (top-level `Fakture`, `Klijenti`, `Izveštaji`, `Pravila` sidebar entries with global lists filtered per client) is **superseded** by a client-axis UI in which the agency picks a client first and finds every per-client capability inside that client's workspace.

The full UX rationale lives in [`saldora-strategy-and-ux-redesign.md`](saldora-strategy-and-ux-redesign.md), Part Three. This section captures the requirement-level surface only.

#### FR-4.18.1 Portfolio View (`/pregled`)

| ID | FR-4.18.1 |
|----|-----------|
| **Description** | The agency-wide home view. A grid of all the agency's clients, each card showing health indicators |
| **Indicators (at launch)** | Invoices pending review, invoices blocked from export, activity recency (last invoice processed timestamp) |
| **Indicators (extensible)** | New indicator types plug in as new data lights up (e.g., overdue forms once M20 ships) |
| **Action** | Each card links to `/klijenti/{id}` (the per-client workspace) |
| **Default route** | `/pregled` is the default landing page after login for agency users |

#### FR-4.18.2 Client Workspace (`/klijenti/{id}`)

| ID | FR-4.18.2 |
|----|-----------|
| **Description** | A single-page surface for one client. Header with client name, PIB, activity details, month navigation |
| **Tabs (at M19 merge)** | Hronologija (default), Fakture, Izveštaji, Pravila |
| **Pre-scoping** | Every tab is pre-scoped to the current client; the embedded list components have their client-filter controls removed |
| **Extensibility** | Tabs are routable subsections; new capabilities (forms, close checklist) land as additional tabs without restructuring the shell |

#### FR-4.18.3 Hronologija (Timeline) Tab

| ID | FR-4.18.3 |
|----|-----------|
| **Description** | The default tab inside the client workspace. Renders events from `client_events` (FR-4.12.5) for the selected period |
| **Grouping** | By day, reverse chronological |
| **Filtering** | By event type (chips at the top of the tab) |
| **Click-through** | Clicking an event opens the underlying entity (invoice detail, rule execution detail, accounting-intent detail) |

#### FR-4.18.4 Fakture Tab

The existing invoice list component embedded into the client workspace, pre-scoped to the current client. The client filter control is hidden (it is implicit). All other filters (date range, status, search, supplier) remain.

#### FR-4.18.5 Izveštaji Tab

The existing reports surface (FR-4.13) embedded into the client workspace, pre-scoped to the current client. Reports use `client_id` as a fixed filter. Hospitality forms (M20, deferred) will land as additional groupings within this tab.

#### FR-4.18.6 Pravila Tab

Lists rules associated with this client (via `rule_client_associations`) plus org-wide rules. A "Kreiraj pravilo za ovog klijenta" CTA opens the rule editor with the client association pre-filled. Org-wide rule management remains under the sidebar `Pravila` entry.

#### FR-4.18.7 Sidebar Structure (post-M19)

```
— Klijent radna tabla —
🏠 Pregled portfelja          (/pregled — default home)
👥 Klijenti                   (flat client list, quick jump to workspace)

— Operacije agencije —
⚙️ Pravila                    (org-wide rules editor)
📦 Arhiviranje                (period archives for tax/retention)
📁 Katalog proizvoda          (canonical products, shared across clients)

— Pomoćno —
📊 Dashboard                  (global stats, kept for now)
🔧 Podešavanja
👤 Tim
💳 Naplata
```

Top-level `Fakture` and `Izveštaji` entries are **removed**. Both are client-scoped and live inside the per-client workspace.

#### FR-4.18.8 Coexistence Policy

Saldora has not yet deployed to paying customers. The M19 redesign ships as a **replacement**, not a parallel surface. Old feature pages are reachable from within the new shell during development only and are removed before the M19 branch merges.

---

<a id="419-hospitality-legal-forms-deferred-m20"></a>
### 4.19 Hospitality Legal Forms (deferred, M20)

> **Status:** Scope deliberately TBD until a working session with a real Serbian accountant who handles hospitality clients produces the requirements document. Building these from a reading of the law alone is known to produce wrong column structures and wrong workflows.

The deliberate next layer of value, on top of the existing OCR + product catalog data foundation, is the generation of legally-required Serbian hospitality forms directly from extracted invoice data:

| Form | Serbian | Purpose | Data source |
|------|---------|---------|-------------|
| **Kalkulacija** | Kalkulacija | Per-product cost-price → markup → VAT → sale-price calculation, regenerated when a new product is added or a supplier price changes | `invoice_line_items` + `product_catalog` (selling_price, default_margin_pct) |
| **Šank lista** | Šank lista | Periodic bar inventory: received goods, sold goods, closing stock | Line items + sales data (sales-side data acquisition is part of the open scope) |
| **Cenovnik** | Cenovnik | Current price list / menu, must match what is charged and must be publicly displayed | `product_catalog.selling_price` |
| **KEP** | Knjiga evidencije prometa | Trade records book — a ledger of all goods received and all sales | Line items + sales data |
| **Popis** | Popis | Periodic physical inventory count with valuation at period end | Inventory state derived from received minus sold (period-bounded) |

#### Data foundation status (already in place)

- **Line-item extraction** with discount/tax_base/quantity/unit_price/total per row (FR-4.3.2, FR-4.5.2).
- **Denormalized `invoice_line_items`** table populated post-OCR and on edits (FR-4.13.1).
- **Product catalog** with canonical names, aliases, categories, selling prices, default margins, and pg_trgm fuzzy matching of line-item descriptions (Section 4.15).
- **Per-line-item product_id FK** linking each extracted item to its canonical catalog entry.

#### Open questions (for the accountant meeting)

1. The exact set of forms an agency is legally required to produce for a hospitality client, and how often.
2. For each form: exact columns / fields / formulas required by law, and any audit-trail requirements.
3. The source data for each form — purchase-side only or sales-side too?
4. The monthly close workflow as accountants actually perform it, step by step.
5. Whether fiscal-receipt integration is needed for KEP, and how the agency receives daily sales data today.

#### Implementation plan once meeting output exists

- Data-model additions (e.g., per-client product markup overrides, period entity).
- Form generators (one Celery-friendly module per legal form).
- New tabs / sections within the per-client `Izveštaji` tab.
- PDF + Excel export templates (Excel at minimum; PDF likely also).

#### M21 — Close Checklist & Period Semantics (further deferred)

A period entity with close/lock semantics, plus the per-period checklist that drives a hospitality client's month to completion, lands in M21. Both depend on the form set being known and the close workflow being captured from the meeting. No issues will be opened until M20 produces output.

---

## 5. Non-Functional Requirements

### 5.1 Performance Requirements

| Requirement | Specification |
|-------------|---------------|
| **Page Load Time** | < 2 seconds for initial load |
| **OCR Processing Time** | < 5 seconds per page (single page) |
| **Batch Processing** | < 2 minutes for 50 documents |
| **API Response Time** | < 200ms for non-processing endpoints |
| **Concurrent Users** | Support 500 simultaneous users |
| **Concurrent Processing** | Support 100 simultaneous OCR jobs |

### 5.2 Scalability Requirements

| Requirement | Specification |
|-------------|---------------|
| **Horizontal Scaling** | API and worker services must scale horizontally |
| **Auto-scaling** | Scale based on queue depth and CPU utilization |
| **Database** | Support read replicas for scaling reads |
| **Storage** | Unlimited document storage capacity |

### 5.3 Availability Requirements

| Requirement | Specification |
|-------------|---------------|
| **Uptime SLA** | 99.9% monthly uptime (excluding planned maintenance) |
| **Planned Maintenance** | Maximum 4 hours/month, outside business hours |
| **Recovery Time** | < 1 hour for critical failures |
| **Data Backup** | Daily automated backups, 30-day retention |

### 5.4 Security Requirements

| Requirement | Specification |
|-------------|---------------|
| **Data Encryption** | TLS 1.3 in transit, AES-256 at rest |
| **Authentication** | JWT with secure refresh token rotation |
| **Password Storage** | Argon2id hashing |
| **Session Management** | Secure, HTTP-only cookies |
| **Input Validation** | Server-side validation for all inputs |
| **SQL Injection** | Parameterized queries only |
| **XSS Prevention** | Content Security Policy, output encoding |
| **CSRF Protection** | Token-based CSRF protection |

### 5.5 Compliance Requirements

| Requirement | Specification |
|-------------|---------------|
| **ZZPL** | Full compliance with Serbian data protection law (primary) |
| **GDPR** | Alignment with GDPR principles as reference standard |
| **Data Residency** | All data stored in data centers with adequate protection (EU/EEA or Serbia) |
| **Data Retention** | Configurable retention policies |
| **Right to Erasure** | Support for complete data deletion |
| **Audit Logging** | Log all data access and modifications |

### 5.6 Usability Requirements

| Requirement | Specification |
|-------------|---------------|
| **Accessibility** | WCAG 2.1 AA compliance |
| **Browser Support** | Latest 2 versions of major browsers |
| **Mobile Support** | Responsive design, touch-friendly |
| **Language** | Serbian (primary), English (secondary) |
| **Onboarding** | Interactive tutorial for new users |

### 5.7 Reliability Requirements

| Requirement | Specification |
|-------------|---------------|
| **Error Handling** | Graceful degradation, user-friendly error messages |
| **Data Integrity** | Transaction support, no partial updates |
| **Fault Tolerance** | Automatic retry for transient failures |
| **Monitoring** | Real-time health monitoring and alerting |

---

## 6. Tech Stack

### 6.1 Frontend

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| **Framework** | Next.js | 15.x | React framework with App Router |
| **Language** | TypeScript | 5.x | Type-safe JavaScript |
| **Styling** | Tailwind CSS | 4.x | Utility-first CSS |
| **State Management** | Zustand | 5.x | Lightweight state management |
| **Data Fetching** | TanStack Query | 5.x | Server state management |
| **Forms** | React Hook Form | 7.x | Form handling |
| **Validation** | Zod | 3.x | Schema validation |
| **Charts** | Recharts | 2.x | Data visualization |
| **Tables** | TanStack Table | 8.x | Data tables |
| **File Upload** | react-dropzone | 14.x | Drag & drop uploads |
| **PDF Viewer** | react-pdf | 7.x | Document preview |
| **Icons** | Heroicons | 2.x | Icon library |
| **Animations** | Framer Motion | 11.x | Animations |

### 6.2 Backend

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| **Framework** | FastAPI | 0.110.x | Async Python web framework |
| **Language** | Python | 3.12.x | Backend language |
| **ORM** | SQLAlchemy | 2.x | Database ORM |
| **Migrations** | Alembic | 1.x | Database migrations |
| **Validation** | Pydantic | 2.x | Data validation |
| **Auth** | python-jose | 3.x | JWT handling |
| **Password** | passlib[argon2] | 1.7.x | Password hashing |
| **HTTP Client** | httpx | 0.27.x | Async HTTP client |
| **Task Queue** | Celery | 5.x | Distributed task queue |
| **Message Broker** | Redis | 7.x | Celery broker + caching |

### 6.3 AI/ML Stack

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| **OCR Inference Host** | Modal.com | — | Serverless GPU host for the dots.ocr server. A10G GPU, scale-to-zero (~2 min cold start, ~5 min warm window after last request). Deployed via `infra/modal/dots_ocr.py`. |
| **Document AI** | dots.ocr (rednote-hilab/dots.ocr) | 1.7B | Vision-language model for unified layout detection + OCR; supports ~100 languages including Serbian Cyrillic and Latin |
| **OCR Client** | openai (Python) | 1.x | OpenAI-compatible client used by the Celery OCR worker to call the Modal-hosted dots.ocr endpoint |
| **LLM Extraction** | anthropic (Python) | latest | Anthropic Claude API client for structured field extraction from OCR text |
| **LLM Model** | Claude Haiku | latest | Primary field extraction — converts raw OCR text to structured JSON. Sonnet may be selected via env for harder documents. |
| **PDF Processing** | PyMuPDF | 1.24.x | PDF parsing |
| **Image Processing** | Pillow | 10.x | Image manipulation (e.g. rendering PDF pages) |
| **OpenCV** | opencv-python | 4.9.x | Reserved for future preprocessing needs (currently bypassed for the VLM path) |
| **NumPy** | numpy | 1.26.x | Numerical computing |

**No image preprocessing is applied before sending to dots.ocr.** Original color images give the VLM the best signal. The preprocessing module exists in code but is bypassed for the dots.ocr path (Section 4.17).

**No automated OCR fallback engine.** EasyOCR has been removed. If dots.ocr fails or returns low-confidence output, the invoice is flagged for manual review.

### 6.4 Database

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| **Primary DB** | PostgreSQL | 16.x | Relational database |
| **Cache** | Redis | 7.x | Caching, sessions |
| **Search** | PostgreSQL FTS | - | Full-text search |

### 6.5 Infrastructure

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Container Runtime** | Docker + docker-compose | Containerization on the Hetzner VPS |
| **Orchestration** | docker-compose (single host) | No Kubernetes; one VPS runs the full stack via `infra/docker/docker-compose.prod.yml` |
| **Application Host** | Hetzner CX32 VPS | Single VPS hosting Caddy, Next.js, FastAPI, PostgreSQL, Redis, OCR worker, Celery beat |
| **Reverse Proxy** | Caddy | Routes `saldora.rs` → Next.js, `api.saldora.rs` → FastAPI; serves Let's Encrypt TLS certs |
| **GPU Inference** | Modal.com | Off-host serverless GPU for dots.ocr (A10G, scale-to-zero) |
| **Object Storage (prod)** | Cloudflare R2 | Document storage (S3-compatible API) |
| **Object Storage (dev)** | MinIO | S3-compatible local storage in dev compose |
| **CDN / DNS / SSL / DDoS** | Cloudflare | DNS, SSL termination at edge, CDN, DDoS protection |
| **Database backups** | pg_dump → R2 | Daily 04:00 UTC ZIP, 30-day retention |
| **Transactional email** | Resend | Welcome, password reset, monthly archives, admin approval notifications |

### 6.6 DevOps & Monitoring

| Component | Technology | Purpose |
|-----------|------------|---------|
| **CI/CD** | GitHub Actions | Continuous integration |
| **Container Registry** | GitHub Container Registry | Docker images |
| **Monitoring** | Prometheus + Grafana | Metrics & dashboards |
| **Logging** | Loki | Log aggregation |
| **Error Tracking** | Sentry | Error monitoring |
| **APM** | OpenTelemetry | Distributed tracing |

### 6.7 Development Tools

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Code Quality** | ESLint, Ruff | Linting |
| **Formatting** | Prettier, Black | Code formatting |
| **Testing** | Jest, Pytest | Unit testing |
| **E2E Testing** | Playwright | End-to-end testing |
| **API Docs** | OpenAPI/Swagger | API documentation |

---

## 7. Database Design

### 7.1 Entity Relationship Diagram

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│      users      │       │  organizations  │       │      teams      │
├─────────────────┤       ├─────────────────┤       ├─────────────────┤
│ id (PK)         │──┐    │ id (PK)         │───────│ id (PK)         │
│ email           │  │    │ name            │       │ organization_id │
│ password_hash   │  │    │ slug            │       │ name            │
│ first_name      │  └───▶│ billing_email   │       │ created_at      │
│ last_name       │       │ plan_id (FK)    │◀──┐   └─────────────────┘
│ organization_id │───────│ created_at      │   │
│ role            │       └─────────────────┘   │
│ created_at      │                             │
│ last_login      │       ┌─────────────────┐   │
└─────────────────┘       │      plans      │   │
                          ├─────────────────┤   │
                          │ id (PK)         │───┘
                          │ name            │
                          │ price_monthly   │
                          │ price_yearly    │
                          │ invoice_limit   │
                          │ features (JSON) │
                          └─────────────────┘

┌─────────────────────┐                             ┌─────────────────┐
│      invoices       │                             │  api_keys       │
├─────────────────────┤                             ├─────────────────┤
│ id (PK)             │                             │ id (PK)         │
│ organization_id(FK) │                             │ organization_id │
│ client_id (FK)      │  ← nullable                │ user_id (FK)    │
│ status              │                             │ key_hash        │
│ invoice_number      │                             │ name            │
│ invoice_date        │                             │ permissions     │
│ due_date            │                             │ last_used       │
│ seller (JSON)       │  ← {pib, mb, name, ...}    │ expires_at      │
│ buyer (JSON)        │  ← {pib, mb, name, ...}    └─────────────────┘
│ subtotal            │
│ tax_rate            │
│ tax_amount          │
│ total_amount        │
│ currency            │
│ line_items (JSON)   │  ← [{description, qty, ...}]
│ tax_groups (JSON)   │  ← [{rate, base_amount, tax_amount}]
│ confidence_score    │
│ field_confidence(J) │  ← [{field_name, value, confidence, ...}]
│ warnings (JSON)     │  ← [{message, severity, field_name}]
│ document_hash       │
│ document_path       │  ← S3 key
│ document_content_type│
│ ocr_engine          │
│ processing_time_ms  │
│ raw_ocr_text        │
│ raw_llm_output      │
│ created_at          │
│ updated_at          │
└─────────────────────┘

┌─────────────────────┐
│      clients        │  ← Agency plan only
├─────────────────────┤
│ id (PK)             │
│ organization_id(FK) │
│ name                │
│ pib                 │  ← unique per org
│ contact_email       │
│ address             │
│ notes               │
│ is_active           │
│ created_at          │
│ updated_at          │
└─────────────────────┘

┌─────────────────┐       ┌─────────────────┐       ┌─────────────────────┐
│  audit_logs     │       │  usage_records  │       │  client_events      │
├─────────────────┤       ├─────────────────┤       ├─────────────────────┤
│ id (PK)         │       │ id (PK)         │       │ id (PK)             │
│ organization_id │       │ organization_id │       │ organization_id     │
│ user_id (FK)    │       │ period_start    │       │ client_id (FK)      │
│ action          │       │ period_end      │       │ event_type          │
│ entity_type     │       │ invoices_count  │       │ entity_type         │
│ entity_id       │       │ api_calls_count │       │ entity_id           │
│ old_values      │       │ storage_bytes   │       │ metadata (JSONB)    │
│ new_values      │       └─────────────────┘       │ created_by (FK)     │
│ ip_address      │                                 │ created_at          │
│ user_agent      │       ┌─────────────────────────┴──┐
│ created_at      │       │  rule_client_associations  │
└─────────────────┘       ├────────────────────────────┤
                          │ rule_id (FK)               │
                          │ client_id (FK)             │
                          │ created_at                 │
                          └────────────────────────────┘
```

**Models actually present in `apps/api/app/models/`:**

`accounting_intent`, `api_key`, `audit_log`, `automation_rule`, `client`, `client_event`, `consent_record`, `correction_log`, `data_processing_agreement`, `deletion_request`, `exchange_rate`, `export_template`, `invitation`, `invoice`, `join_request`, `line_item`, `minimax_config`, `organization`, `product_catalog`, `rule_client_association`, `scheduled_export_log`, `usage_record`, `user`.

Notably **absent** (consistent with Section 4.17): `webhook`, `customer`, `invoice_counter`, `kpo_entry`, `sef_invoice`, `sef_connection`, `inbound_email`, `support_ticket`.

### 7.2 Table Definitions

#### 7.2.1 users
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    organization_id UUID REFERENCES organizations(id),
    role VARCHAR(20) NOT NULL DEFAULT 'operator',
    email_verified BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login TIMESTAMP WITH TIME ZONE,

    CONSTRAINT valid_role CHECK (role IN ('admin', 'manager', 'operator', 'viewer'))
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_organization ON users(organization_id);
```

#### 7.2.2 organizations
```sql
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    billing_email VARCHAR(255),
    plan_id UUID REFERENCES plans(id),
    payment_provider_customer_id VARCHAR(255),  -- Paddle customer ID
    subscription_status VARCHAR(50),            -- pending|trial|active|canceled|expired|NULL
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_organizations_slug ON organizations(slug);
CREATE INDEX idx_organizations_subscription_status ON organizations(subscription_status);
```

**`subscription_status` semantics:** see FR-4.1.5. New registrations default to `pending`; the `require_role` dependency 403s with `subscription_pending_approval` while pending. NULL is a legacy value treated as `active` and backfilled on access.

#### 7.2.3 invoices

Seller/buyer data, line items, and tax groups are stored as JSON columns directly on the invoice record rather than as foreign keys to separate tables. This accommodates the diverse structures found in OCR-extracted invoices without requiring schema migrations.

```sql
CREATE TABLE invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    client_id UUID REFERENCES clients(id),  -- nullable; set via PIB matching

    status VARCHAR(20) NOT NULL DEFAULT 'processing',

    -- Core invoice fields
    invoice_number VARCHAR(100),
    invoice_date DATE,
    due_date DATE,

    -- Seller/buyer as JSON: {pib, mb, name, address, city, postal_code, verified, apr_status}
    seller JSON,
    buyer JSON,

    -- Amounts
    subtotal DECIMAL(15, 2),
    tax_rate DECIMAL(5, 2),
    tax_amount DECIMAL(15, 2),
    total_amount DECIMAL(15, 2),
    currency VARCHAR(3) DEFAULT 'RSD',

    -- Structured data (JSON arrays)
    line_items JSON,       -- [{description, quantity, unit_price, discount, tax_base, total, tax_rate, tax_amount}]
    tax_groups JSON,       -- [{rate, base_amount, tax_amount}]

    -- Confidence and validation
    confidence_score DECIMAL(5, 4),  -- 0.0000–1.0000 in DB, scaled to 0–100 in API
    field_confidence JSON,  -- [{field_name, value, confidence, needs_review}]
    warnings JSON,          -- [{message, severity, field_name}]

    -- Document storage
    document_hash VARCHAR(64),         -- SHA-256 of uploaded file
    document_path VARCHAR(500),        -- S3/R2 key
    document_content_type VARCHAR(100),

    -- Processing metadata
    ocr_engine VARCHAR(50),
    processing_time_ms INTEGER,
    raw_ocr_text TEXT,
    raw_llm_output TEXT,               -- Raw LLM extraction JSON for debugging

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT valid_status CHECK (status IN ('processing', 'review', 'verified', 'exported', 'error'))
);

CREATE INDEX idx_invoices_organization ON invoices(organization_id);
CREATE INDEX idx_invoices_client ON invoices(client_id);
CREATE INDEX idx_invoices_status ON invoices(status);
CREATE INDEX idx_invoices_date ON invoices(invoice_date);
```

**Note:** The `companies` and `documents` tables described in earlier SRS versions have been replaced by inline JSON columns (`seller`, `buyer`) and direct storage fields (`document_hash`, `document_path`, `document_content_type`) on the invoices table. A standalone `companies` table may be reintroduced for APR verification caching in a future milestone.

#### 7.2.4 clients
```sql
CREATE TABLE clients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    name VARCHAR(255) NOT NULL,
    pib VARCHAR(20) NOT NULL,
    contact_email VARCHAR(255),
    address TEXT,
    notes TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT uq_clients_org_pib UNIQUE (organization_id, pib)
);

CREATE INDEX idx_clients_organization ON clients(organization_id);
CREATE INDEX idx_clients_pib ON clients(pib);
```

#### 7.2.5 invoice_line_items

Denormalized table for report queries (Section 4.13). Populated after OCR processing and re-populated on user edits.

```sql
CREATE TABLE invoice_line_items (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    invoice_id    UUID NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    client_id     UUID REFERENCES clients(id) ON DELETE SET NULL,  -- nullable; set via PIB matching (migration 0008)
    description   TEXT,
    quantity      NUMERIC(12, 4),
    unit_price    NUMERIC(15, 4),
    discount      NUMERIC(5, 2),        -- Rabat percentage (e.g. 7.00 for 7%)
    tax_base      NUMERIC(15, 2),        -- Poreska osnovica (after discount, before VAT)
    total         NUMERIC(15, 2),
    tax_rate      NUMERIC(5, 2),
    tax_amount    NUMERIC(15, 2),
    currency      VARCHAR(3) NOT NULL DEFAULT 'RSD',
    supplier_name TEXT,
    supplier_pib  VARCHAR(20),
    invoice_date  DATE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_invoice_line_items_org      ON invoice_line_items(organization_id);
CREATE INDEX ix_invoice_line_items_invoice  ON invoice_line_items(invoice_id);
CREATE INDEX ix_invoice_line_items_date     ON invoice_line_items(invoice_date);
CREATE INDEX ix_invoice_line_items_supplier ON invoice_line_items(supplier_pib);
CREATE INDEX ix_ili_client_id              ON invoice_line_items(client_id);
```

#### 7.2.6 product_catalog

Canonical product entries for procurement intelligence (Section 4.15). Populated and managed by users via the catalog API. Used for fuzzy-matching line item descriptions.

```sql
CREATE TABLE product_catalog (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    canonical_name  TEXT NOT NULL,
    unit_of_measure VARCHAR(20),
    category        VARCHAR(50),
    aliases         JSONB NOT NULL DEFAULT '[]',
    selling_price   NUMERIC(15, 2),
    default_margin_pct NUMERIC(5, 2),
    match_count     INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX ix_pc_org_name ON product_catalog(organization_id, canonical_name);
CREATE INDEX ix_pc_org_id ON product_catalog(organization_id);
CREATE INDEX ix_pc_category ON product_catalog(category);
```

Note: `invoice_line_items` includes a `product_id UUID REFERENCES product_catalog(id) ON DELETE SET NULL` column (added in migration 0007) for linking line items to their canonical catalog entry.

#### 7.2.7 client_events

Append-only event log per client, powering the timeline view (FR-4.12.5, FR-4.18.3).

```sql
CREATE TABLE client_events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    client_id       UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    event_type      VARCHAR(50) NOT NULL,
    entity_type     VARCHAR(50),               -- e.g. 'invoice', 'rule', 'accounting_intent'
    entity_id       UUID,                      -- FK to the relevant entity (no DB-level constraint to keep flexibility)
    metadata        JSONB NOT NULL DEFAULT '{}',
    created_by      UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT valid_client_event_type CHECK (event_type IN (
        'invoice_uploaded', 'invoice_verified', 'invoice_exported',
        'accounting_intent_classified', 'rule_fired', 'client_assigned'
        -- Additional types added by future milestones (form_generated, period_closed, …)
    ))
);

CREATE INDEX idx_client_events_org_client ON client_events(organization_id, client_id, created_at DESC);
CREATE INDEX idx_client_events_type       ON client_events(event_type);
CREATE INDEX idx_client_events_entity     ON client_events(entity_type, entity_id);
```

#### 7.2.8 rule_client_associations

Per-client scoping for automation rules (FR-4.12.6).

```sql
CREATE TABLE rule_client_associations (
    rule_id    UUID NOT NULL REFERENCES automation_rules(id) ON DELETE CASCADE,
    client_id  UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (rule_id, client_id)
);

CREATE INDEX idx_rca_client ON rule_client_associations(client_id);
```

A rule with no associations applies organization-wide; a rule with one or more associations applies only when the invoice's `client_id` matches one of the associated client IDs.

#### 7.2.9 correction_logs

Defined in Section 9.8 (extraction quality monitoring). Logs every human field correction for monitoring purposes — **not** for model training.

#### 7.2.10 usage_records

Write-only counter that tracks monthly invoice processing per organization. Plan limits are checked against this counter, not against live invoice counts, so deleting invoices does not reset usage (see FR-4.7.2).

#### 7.2.11 minimax_configs

Per-organization MiniMax credentials and integration state (Section 12.5).

#### 7.2.12 scheduled_export_logs

History of automated monthly archive exports (delivered via email, FR-4.7.5).

#### 7.2.13 Additional present models

`api_keys`, `audit_logs`, `consent_records`, `data_processing_agreements`, `deletion_requests`, `exchange_rates`, `export_templates`, `invitations`, `join_requests`, `accounting_intents`, `automation_rules` — schemas appear elsewhere in this document where directly relevant; otherwise their definitions live in the SQLAlchemy models under `apps/api/app/models/`.

---

## 8. API Specification

### 8.1 API Overview

**Base URL:** `https://api.saldora.rs/api/v1`

**Authentication:** Bearer token (JWT) or per-org API key

**Content Type:** `application/json`

**Rate Limits:**

| Plan | Requests/minute | Requests/day |
|------|-----------------|--------------|
| Starter | 30 | 1,000 |
| Professional | 100 | 10,000 |
| Agency | 300 | 30,000 |
| Enterprise (custom) | 500+ | Unlimited |

### 8.2 Authentication Endpoints

#### POST /auth/register
Register a new user account.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123",
  "first_name": "Marko",
  "last_name": "Petrović",
  "organization_name": "Računovodstvo Petrović"
}
```

**Response (201 Created):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "organization_id": "660e8400-e29b-41d4-a716-446655440001",
  "message": "Verification email sent"
}
```

#### POST /auth/login
Authenticate user and receive tokens.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123"
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

#### POST /auth/refresh
Refresh access token.

**Request:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

### 8.3 Invoice Endpoints

#### POST /invoices/upload
Upload invoice document for processing.

**Request:** `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| file | File | Yes | Invoice document |
| priority | String | No | `normal` or `high` |
| callback_url | String | No | Webhook URL |

**Response (202 Accepted):**
```json
{
  "id": "770e8400-e29b-41d4-a716-446655440002",
  "status": "processing",
  "estimated_time": 5,
  "document_id": "880e8400-e29b-41d4-a716-446655440003"
}
```

#### GET /invoices/{id}
Get invoice details.

**Response (200 OK):**
```json
{
  "id": "770e8400-e29b-41d4-a716-446655440002",
  "status": "verified",
  "confidence_score": 94.5,
  "invoice_number": "2025-00042",
  "invoice_date": "2025-01-15",
  "due_date": "2025-02-15",
  "seller": {
    "pib": "123456789",
    "mb": "12345678",
    "name": "Firma ABC d.o.o.",
    "address": "Bulevar Kralja Aleksandra 1",
    "city": "Beograd",
    "postal_code": "11000",
    "verified": false,
    "apr_status": null
  },
  "buyer": {
    "pib": "987654321",
    "mb": "87654321",
    "name": "Kompanija XYZ d.o.o.",
    "address": "Cara Dušana 15",
    "city": "Novi Sad",
    "postal_code": "21000",
    "verified": false,
    "apr_status": null
  },
  "line_items": [
    {
      "description": "Usluge konsaltinga",
      "quantity": "10",
      "unit_price": "5000.00",
      "discount": null,
      "tax_base": null,
      "total": "50000.00",
      "tax_rate": "20",
      "tax_amount": null
    }
  ],
  "tax_groups": [
    {
      "rate": "20",
      "base_amount": "50000.00",
      "tax_amount": "10000.00"
    }
  ],
  "subtotal": "50000.00",
  "tax_rate": "20.00",
  "tax_amount": "10000.00",
  "total_amount": "60000.00",
  "currency": "RSD",
  "field_confidences": [
    {"field_name": "invoice_number", "value": "2025-00042", "confidence": 95.0, "needs_review": false},
    {"field_name": "seller_pib", "value": "123456789", "confidence": 92.0, "needs_review": false}
  ],
  "warnings": [],
  "blocked": false,
  "field_warnings": {},
  "document_url": "https://storage.saldora.rs/docs/...",
  "raw_ocr_text": null,
  "raw_llm_output": null,
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:30:05Z"
}
```

#### GET /invoices
List invoices with filtering.

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| page | Integer | Page number (default: 1) |
| per_page | Integer | Items per page (default: 20, max: 100) |
| status | String | Filter by status |
| date_from | Date | Start date filter |
| date_to | Date | End date filter |
| seller_pib | String | Filter by seller PIB |
| buyer_pib | String | Filter by buyer PIB |
| search | String | Full-text search |
| sort | String | Sort field |
| order | String | `asc` or `desc` |

**Response (200 OK):**
```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 150,
    "total_pages": 8
  }
}
```

#### PATCH /invoices/{id}
Update invoice data (partial update). Supports all extracted fields including seller/buyer fields, line_items, and tax_groups.

**Request:**
```json
{
  "invoice_number": "2025-00042-A",
  "seller_pib": "123456789",
  "total_amount": 61000.00,
  "tax_groups": [
    {"rate": "20", "base_amount": "50000.00", "tax_amount": "10000.00"},
    {"rate": "10", "base_amount": "1000.00", "tax_amount": "100.00"}
  ]
}
```

#### DELETE /invoices/{id}
Delete invoice and associated document.

**Response (204 No Content)**

### 8.4 Export Endpoints

#### POST /export
Export invoices to specified format.

**Request:**
```json
{
  "format": "xlsx",
  "invoice_ids": ["id1", "id2", "id3"],
  "template_id": "default",
  "options": {
    "include_line_items": true,
    "date_format": "DD.MM.YYYY"
  }
}
```

**Response (200 OK):**
Streams the file directly as `StreamingResponse` (XLSX, CSV, JSON, or MiniMax XML).
Headers: `Content-Disposition: attachment; filename="fakture_izvoz.{ext}"`

**Response (422 Unprocessable Entity):**
```json
{
  "detail": {
    "blocked_invoices": [
      {
        "invoice_id": "uuid",
        "invoice_number": "FAK-001",
        "reasons": ["Nedostaje: PIB prodavca", "Confidence < 60% bez verifikacije"]
      }
    ],
    "message": "2 faktura blokirano za izvoz"
  }
}
```

#### POST /export/minimax/push
Push invoices to MiniMax accounting software via REST API.

**Request:**
```json
{
  "invoice_ids": ["id1", "id2"],
  "create_customers": true
}
```

**Response (200 OK):**
```json
{
  "results": [
    {"invoice_id": "id1", "invoice_number": "FAK-001", "minimax_id": 456, "status": "success"},
    {"invoice_id": "id2", "invoice_number": "FAK-002", "status": "error", "error": "Nedostaje PIB prodavca"}
  ],
  "total": 2,
  "success_count": 1,
  "error_count": 1
}
```

#### GET /export/minimax/config
Get MiniMax configuration for the current organization.

#### PUT /export/minimax/config
Create or update MiniMax configuration.

**Request:**
```json
{
  "client_id": "minimax-client-id",
  "client_secret": "minimax-secret",
  "username": "user@example.com",
  "password": "password",
  "minimax_org_id": 12345
}
```

#### POST /export/audit
Generate audit export for tax inspection (ZIP with invoice register, PDFs, audit trail, VAT summary).

**Request:**
```json
{
  "date_from": "2025-01-01",
  "date_to": "2025-12-31",
  "include_documents": true,
  "include_audit_trail": true,
  "include_vat_summary": true
}
```

**Response (200 OK):**
```json
{
  "download_url": "https://storage.saldora.rs/exports/audit/...",
  "expires_at": "2025-02-14T11:30:00Z",
  "file_size": 5242880,
  "invoice_count": 150,
  "contents": ["registar_faktura.csv", "pdv_pregled.xlsx", "revizijski_trag.csv", "dokumenti/"]
}
```

### 8.5 Verification Endpoints

#### GET /verify/pib/{pib}
Verify PIB against APR database.

**Response (200 OK):**
```json
{
  "pib": "123456789",
  "valid": true,
  "company": {
    "name": "Firma ABC d.o.o.",
    "address": "Bulevar Kralja Aleksandra 1",
    "city": "Beograd",
    "postal_code": "11000",
    "status": "active",
    "registration_date": "2015-03-20"
  },
  "verified_at": "2025-01-15T10:30:00Z",
  "source": "apr"
}
```

### 8.6 Error Responses

**Standard Error Format:**
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": [
      {
        "field": "email",
        "message": "Invalid email format"
      }
    ]
  }
}
```

**Error Codes:**

| HTTP Status | Code | Description |
|-------------|------|-------------|
| 400 | VALIDATION_ERROR | Invalid request data |
| 401 | UNAUTHORIZED | Missing or invalid token |
| 403 | FORBIDDEN | Insufficient permissions |
| 404 | NOT_FOUND | Resource not found |
| 409 | CONFLICT | Resource already exists |
| 422 | PROCESSING_ERROR | OCR processing failed |
| 429 | RATE_LIMITED | Too many requests |
| 500 | INTERNAL_ERROR | Server error |

---

## 9. AI/ML Components

### 9.1 OCR Pipeline Architecture

dots.ocr is a vision-language model (VLM) that performs **unified layout detection and text extraction** in a single pass. It runs on **Modal.com** as a serverless GPU endpoint (A10G, scale-to-zero). The Celery OCR worker on the Hetzner VPS calls it over HTTPS using the OpenAI-compatible chat completions API.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        OCR Processing Pipeline                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────┐    ┌─────────────────────────────────────────────┐  │
│  │   Input     │    │          Modal.com (A10G GPU)               │  │
│  │  Document   │    │  ┌───────────────────────────────────────┐  │  │
│  │ (PDF/Image) │    │  │  dots.ocr Vision-Language Model       │  │  │
│  └──────┬──────┘    │  │  (rednote-hilab/dots.ocr, 1.7B)       │  │  │
│         │           │  └───────────────────────────────────────┘  │  │
│         ▼           │  OpenAI-compatible HTTPS endpoint            │  │
│  ┌─────────────┐    │  Scale-to-zero (~2 min cold start)           │  │
│  │ OCR Worker  │    └──────────────────────┬──────────────────────┘  │
│  │ (Celery,    │                           │                         │
│  │  CPU only,  │    HTTPS POST             │ Structured              │
│  │  Hetzner)   │───▶/v1/chat/completions   │ JSON Output             │
│  │             │    (base64 image +        │ (layout +               │
│  │ openai      │     special tokens)       │  text + bbox)           │
│  │ Python      │◀──────────────────────────┘                         │
│  │ client      │                                                     │
│  └──────┬──────┘                                                     │
│         │                                                            │
│         ▼                                                            │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │              dots.ocr Structured Output                      │    │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────────────┐ │    │
│  │  │ Header  │  │  Table  │  │  Footer │  │  Text Blocks    │ │    │
│  │  │ + Text  │  │  + HTML │  │ + Text  │  │  + Markdown     │ │    │
│  │  └────┬────┘  └────┬────┘  └────┬────┘  └────────┬────────┘ │    │
│  └───────┼────────────┼────────────┼────────────────┼──────────┘    │
│          │            │            │                │                │
│          └────────────┴────────────┴────────────────┘                │
│                                    │                                 │
│                                    ▼                                 │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │        LLM Field Extraction (Anthropic Claude API)          │    │
│  │    Primary: Claude extracts all fields from raw OCR text    │    │
│  │    Fallback: Regex pattern matching if LLM unavailable      │    │
│  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────────┐ │    │
│  │  │ PIB  │ │ Date │ │Amount│ │ Name │ │TaxGrp│ │Line Items│ │    │
│  │  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └──────────┘ │    │
│  └──────────────────────────┬──────────────────────────────────┘    │
│                             │                                        │
│                             ▼                                        │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    Post-Processing                           │    │
│  │      - Field validation    - Confidence scoring              │    │
│  │      - Format normalization - Data structuring               │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    Fallback Path (if needed)                 │    │
│  │   If dots.ocr fails → manual review by user (no EasyOCR)    │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

**Note:** Image preprocessing (grayscale, deskewing, denoising) is **skipped** for dots.ocr — VLMs work best with original color images. Preprocessing is only applied when using traditional OCR engines.

**Key Advantages of dots.ocr VLM Approach:**
- **Single model** handles layout detection + OCR (no separate LayoutParser needed)
- **Structured output** with semantic regions, bounding boxes, and text
- **~100 language support** including Serbian Cyrillic and Latin
- **Reading order preservation** for logical document flow
- **Table understanding** with HTML output for structured tables
- **1.7B parameters** - compact yet powerful

### 9.2 Image Preprocessing

**Module:** `app/ml/preprocessing.py`

```python
class InvoicePreprocessor:
    """
    Preprocesses invoice images for optimal OCR performance.
    """

    def process(self, image: np.ndarray) -> np.ndarray:
        """
        Apply preprocessing pipeline.

        Steps:
        1. Color correction
        2. Deskewing
        3. Noise reduction
        4. Binarization
        5. Resolution normalization
        """
        pass
```

**Preprocessing Operations:**

| Operation | Description | Library |
|-----------|-------------|---------|
| Deskewing | Correct document rotation | OpenCV |
| Denoising | Remove noise artifacts | OpenCV |
| Binarization | Convert to black/white | OpenCV (Otsu's) |
| Contrast Enhancement | Improve text visibility | PIL/OpenCV |
| Resolution Scaling | Normalize to 300 DPI | PIL |
| Border Removal | Remove scanner artifacts | OpenCV |

### 9.3 OCR Engine

**Primary Engine:** dots.ocr, hosted on Modal.com

dots.ocr is optimized for document understanding and provides high accuracy on structured documents like invoices, with strong Cyrillic and Latin script support. In production it runs on **Modal.com** as a scale-to-zero GPU endpoint; the OCR worker on the Hetzner VPS calls it via the OpenAI-compatible chat completions API.

**Architecture:**
- **Modal app** (`infra/modal/dots_ocr.py`): A Modal deployment serving `rednote-hilab/dots.ocr` on an A10G GPU. Scales to zero when idle; first request after idle has roughly a 2-minute cold start (model loading); container stays warm ~5 minutes after the last request.
- **ocr-worker**: Python 3.12 Celery container on the Hetzner VPS (CPU only) calling Modal via the `openai` Python client.
- Worker sends base64-encoded images with the `<|img|><|imgpad|><|endofimg|>` prompt prefix.
- For local development the same code path can talk to a local vLLM server via the `DOTS_OCR_SERVER_URL` env var (so dev does not depend on Modal credit).

**Configuration (environment variables):**
```
DOTS_OCR_SERVER_URL=https://<modal-endpoint>/v1   # prod
DOTS_OCR_MODEL_NAME=model
OCR_PRIMARY_ENGINE=dots
OCR_FALLBACK_ENGINE=none
```

**Fallback Strategy:** Manual review by user. There is no automated OCR fallback engine — EasyOCR has been removed (Section 4.17).

### 9.4 Document Layout Analysis

**Model:** dots.ocr (integrated VLM - no separate layout parser needed)

dots.ocr provides layout detection as part of its unified vision-language model. The model outputs structured JSON with semantic region classification and bounding boxes.

**Detected Regions:**

| Region Type | Description | Output Format |
|-------------|-------------|---------------|
| Header | Invoice header (logo, company info) | Markdown text |
| Seller Info | Seller company details block | Markdown text |
| Buyer Info | Buyer company details block | Markdown text |
| Line Items Table | Products/services table | HTML table |
| Totals | Subtotal, tax, total amounts | Markdown text |
| Footer | Footer information, signatures | Markdown text |
| Metadata | Invoice number, dates | Markdown text |

**dots.ocr Output Example:**

```json
{
  "regions": [
    {
      "type": "header",
      "bbox": [10, 10, 590, 100],
      "content": "## FAKTURA\n**Br: 2025-042**",
      "confidence": 0.95
    },
    {
      "type": "table",
      "bbox": [10, 200, 590, 400],
      "content": "<table><tr><th>Opis</th><th>Kol</th><th>Cena</th></tr>...</table>",
      "confidence": 0.92
    }
  ],
  "reading_order": [0, 1, 2, 3],
  "full_text": "..."
}
```

### 9.5 Field Extraction

**Primary method:** LLM-based extraction via Anthropic Claude API

The raw OCR text from dots.ocr is sent to Claude along with a structured JSON schema prompt. The LLM returns a complete JSON object with all invoice fields extracted. This approach handles the diversity of Serbian invoice formats (mixed Cyrillic/Latin, varying layouts, multi-section invoices) more robustly than hand-crafted regex patterns.

**Fallback method:** Regex pattern matching (`FieldExtractor`) when LLM is unavailable.

**Extracted Fields:**

| Field | Pattern Examples | Validation |
|--------|------------------|------------|
| PIB | `PIB: 123456789`, `ПИБ: 123456789` | 9-digit number, mod-11 checksum |
| MB | `МБ: 12345678`, `MB: 12345678` | 8-digit number |
| DATE | `15.01.2025`, `15/01/2025` | Valid date |
| AMOUNT | `45.000,00 RSD`, `45000.00` | Decimal number |
| INVOICE_NUM | `Faktura br: 2025-042` | Alphanumeric |
| COMPANY | `Firma ABC d.o.o.` | Company name |
| ADDRESS | `Bulevar Kralja Aleksandra 1` | Address string |
| TAX_RATE | `PDV 20%`, `ПДВ 20%` | 0%, 10%, 20% |
| TAX_GROUPS | Per-PDV-section breakdown | rate, base_amount, tax_amount per group |
| LINE_ITEMS | Table rows | description, quantity, unit_price, discount, tax_base, total, tax_rate, tax_amount |

**LLM Extraction Design Decisions:**
- Tax amounts are extracted as-printed from the document; they are NOT recomputed from subtotal * rate
- Each separate PDV line on the invoice becomes its own `tax_group` entry, even when groups share the same rate (e.g., goods at 20% and services at 20% are kept as two separate groups)
- The LLM receives the complete OCR text (not pre-parsed fragments) for maximum context

### 9.6 Confidence Scoring

**Confidence Calculation:**

```python
def calculate_confidence(extracted_data: dict) -> float:
    """
    Calculate overall confidence score for extracted data.

    Factors:
    - OCR character confidence (40%)
    - Field validation success (30%)
    - Layout consistency (20%)
    - Cross-validation (10%)
    """
    weights = {
        "ocr_confidence": 0.4,
        "field_validation": 0.3,
        "layout_consistency": 0.2,
        "cross_validation": 0.1
    }

    scores = {
        "ocr_confidence": calculate_ocr_confidence(extracted_data),
        "field_validation": validate_fields(extracted_data),
        "layout_consistency": check_layout(extracted_data),
        "cross_validation": cross_validate(extracted_data)
    }

    return sum(weights[k] * scores[k] for k in weights)
```

### 9.7 ML Infrastructure

**GPU Requirements:**

| Component | GPU | Hosting | Notes |
|-----------|-----|---------|-------|
| dots.ocr | A10G | Modal.com (prod) | Scale-to-zero serverless GPU; ~2 min cold start; ~5 min warm window |
| dots.ocr (dev) | Any local GPU | Local vLLM (optional) | Switched via `DOTS_OCR_SERVER_URL` env var; not required for dev (Modal can be hit directly) |
| OCR Worker | None (CPU) | Hetzner CX32 | Celery worker calling Modal endpoint and Claude API |
| Claude (field extraction) | None (API call) | Anthropic API | No local compute needed |

**Model Note:** The system uses pre-trained models (dots.ocr for OCR, Claude Haiku for field extraction) without additional training on user data. This approach eliminates the need for training data collection, consent management, and complex MLOps infrastructure, while ensuring user privacy protection. Correction logs (Section 9.8) exist for monitoring quality, **not** for training.

**Modal deployment** (`infra/modal/dots_ocr.py`): a single Modal app exposes the OpenAI-compatible chat completions endpoint backed by dots.ocr on an A10G. Cost scales with usage; at ~10K invoices/month the GPU bill sits around $60 (see DEPLOYMENT.md cost table). Switching to a fixed-price always-on GPU (e.g., a Hetzner GEX44) is a deployment-only change — the worker code is unchanged.

### 9.8 Extraction Quality Monitoring

The system MUST track extraction quality through correction logging, purely for quality monitoring and analytics purposes, NOT for model training.

#### 9.8.1 Correction Logging

**Every human correction MUST be logged:**

```python
class CorrectionLog:
    """
    Tracks every field correction made by users.
    Used for quality monitoring and analytics, not for model training.
    """
    id: UUID
    invoice_id: UUID
    user_id: UUID
    field_name: str           # e.g., "seller_pib", "total_amount"
    original_value: str       # What the model extracted
    corrected_value: str      # What the user entered
    model_confidence: float   # Confidence at extraction time
    correction_type: str      # "ocr_error", "ner_error", "layout_error", "business_logic"
    created_at: datetime
```

**Database Schema:**
```sql
CREATE TABLE correction_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_id UUID NOT NULL REFERENCES invoices(id),
    user_id UUID NOT NULL REFERENCES users(id),
    field_name VARCHAR(50) NOT NULL,
    original_value TEXT,
    corrected_value TEXT NOT NULL,
    model_confidence DECIMAL(5, 2),
    correction_type VARCHAR(30),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_corrections_field ON correction_logs(field_name);
CREATE INDEX idx_corrections_date ON correction_logs(created_at);
```

#### 9.8.2 Quality Dashboard

The system SHOULD provide a dashboard for tracking extraction accuracy per field:

| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| Field Error Rate | % of invoices requiring correction per field | > 15% |
| High Confidence Errors | Corrections where model confidence > 90% | > 5% |
| Repeat Errors | Same error pattern across documents | > 10 occurrences |

These metrics serve to identify systemic issues and inform the team about potential problems with input document quality or system configuration.

### 9.9 Invoice Template Learning & LLM Cost Optimization

The system SHOULD implement a template learning mechanism that caches invoice layout patterns per seller, enabling field extraction without LLM calls for recurring invoice formats. This reduces per-invoice processing costs by eliminating redundant LLM API calls for invoices with previously seen structures.

#### 9.9.1 Template Learning Architecture

```
Invoice arrives → OCR extracts raw text + bounding boxes
                        ↓
              Compute layout fingerprint
                        ↓
         Template exists for (seller_pib, fingerprint)?
                        ↓
               ┌────────┴────────┐
               YES               NO
               ↓                  ↓
    Template-based extraction   LLM extraction (Claude API)
    (coordinate + regex)         ↓ (paid API call)
               ↓                Learn template from
    Confidence >= threshold?    successful extraction
               ↓                  ↓
         ┌─────┴─────┐     Store template
         YES          NO    (field mappings,
         ↓            ↓     coordinates, patterns)
    Use result   Fall back
    ($0.00)      to LLM ($)
```

#### 9.9.2 Layout Fingerprinting

The system MUST generate a deterministic structural fingerprint from OCR output that is:
- **Invariant to changing values** — same layout with different amounts/dates produces the same fingerprint
- **Sensitive to structural changes** — different label positions, added/removed sections produce different fingerprints
- **Based on structural elements** — label text (e.g., "Datum fakture:", "PIB:"), relative positions of text blocks, table column headers, section boundaries

**Fingerprint components:**
- Sorted list of detected label strings (normalized: lowered, trimmed)
- Relative positions of text blocks (quantized to grid cells, not pixel-exact)
- Table structure signature (column count, header text)
- Hash algorithm: SHA-256 of the canonical representation

#### 9.9.3 Template Storage

**InvoiceTemplate model:**

```python
class InvoiceTemplate:
    id: UUID
    organization_id: UUID          # Multi-tenant scoping
    seller_pib: str                # Primary lookup key
    layout_fingerprint: str        # SHA-256 hash of structural elements
    field_mappings: dict           # JSONB — per-field extraction rules
    sample_invoice_id: UUID        # Reference invoice this was learned from
    usage_count: int               # How many times used successfully
    success_rate: float            # Successful extractions / total attempts
    is_active: bool                # Deactivated after repeated failures
    last_used_at: datetime
    created_at: datetime
    updated_at: datetime
```

**Field mapping structure (per field):**

```json
{
  "invoice_number": {
    "bbox_region": [120, 45, 280, 65],
    "label_text": "Faktura br:",
    "label_offset": [-15, 0],
    "value_regex": "[A-Z0-9/-]+",
    "confidence_weight": 0.9
  },
  "total_amount": {
    "bbox_region": [400, 520, 580, 545],
    "label_text": "UKUPNO:",
    "label_offset": [-120, 0],
    "value_regex": "[\\d.,]+\\s*(RSD|EUR|USD)?",
    "confidence_weight": 0.85
  }
}
```

#### 9.9.4 Template-Based Extraction

The template extraction engine MUST implement a three-tier fallback chain:

1. **Coordinate-based extraction** (primary): Use stored bounding box regions to locate field values in OCR output at known positions relative to known labels
2. **Pattern-based extraction** (secondary): If coordinate extraction yields low confidence, use stored regex patterns matched against text near expected label positions
3. **LLM fallback** (last resort): If both template methods produce confidence below threshold, invoke Claude API as normal

**Confidence thresholds:**
- Template extraction minimum: 0.70 (configurable per organization)
- Per-field minimum: 0.60 — any field below this triggers LLM fallback for the entire invoice
- Overall invoice minimum: weighted average of field confidences >= 0.70

#### 9.9.5 Automatic Template Learning

Templates are learned automatically — no manual configuration required:

1. After a successful LLM extraction with overall confidence >= 0.85:
   - Compute the layout fingerprint
   - If no template exists for this `(seller_pib, fingerprint)` pair, create one
   - Map each extracted field back to its OCR bounding box region and nearby label text
   - Generate regex patterns from the extracted value formats
2. **Minimum field threshold:** At least 5 fields must be successfully mapped to create a template
3. **Template refinement:** Successful template uses reinforce field mappings; failures decrement success rate
4. **Auto-deactivation:** After 3 consecutive failures (configurable), the template is deactivated and the next successful LLM extraction creates a replacement

#### 9.9.6 Cost Tracking

The system MUST track LLM cost savings from template usage:

| Metric | Description |
|--------|-------------|
| `template_used` | Boolean — was a template used for this invoice? |
| `template_id` | Which template was used (nullable) |
| `llm_called` | Boolean — was the LLM API called? |
| `estimated_llm_cost` | Estimated cost of the LLM call (or saved cost if bypassed) |

**Expected cost reduction:** For organizations with recurring suppliers (typical for accounting agencies), template hit rate should reach 80-95% within 2-3 months, reducing LLM costs by a corresponding amount.

#### 9.9.7 Limitations and Considerations

- Templates are **per-organization** — different organizations may receive the same seller's invoices but cannot share templates (multi-tenant isolation)
- Template learning does NOT constitute model training — no neural network weights are modified. Templates are deterministic lookup tables.
- Line item extraction from tables is more complex to template than header fields; the system MAY fall back to LLM for line items while using templates for header fields
- Sellers who change their invoice software/layout will trigger new template creation automatically


---

## 10. Security Requirements

### 10.1 Authentication Security

| Requirement | Implementation |
|-------------|----------------|
| Password Hashing | Argon2id with salt |
| JWT Tokens | RS256 signing, 1-hour expiry; algorithm pinned to HS256 (no algorithm confusion) |
| Refresh Tokens | Secure HTTP-only cookies, 7-day expiry |
| MFA | TOTP-based 2FA (optional) |
| Session Management | Redis-backed sessions |
| Brute Force Protection | Rate limiting, account lockout |
| Account Lockout | 5 failed attempts → 15 min lockout via Redis |
| Token Blacklisting | Logout invalidates token via Redis set |
| Rate Limiting | slowapi, per-plan limits (see 8.1) |

### 10.2 Data Security

| Requirement | Implementation |
|-------------|----------------|
| Encryption in Transit | TLS 1.3 |
| Encryption at Rest | AES-256 |
| Document Storage | Encrypted S3 buckets |
| Database | Encrypted PostgreSQL |
| Key Management | AWS KMS or HashiCorp Vault |
| Data Masking | PII masking in logs |

### 10.3 Application Security

| Requirement | Implementation |
|-------------|----------------|
| Input Validation | Server-side validation (Pydantic) |
| SQL Injection | Parameterized queries (SQLAlchemy) |
| XSS Prevention | Output encoding, CSP headers |
| CSRF Protection | Token-based CSRF |
| File Upload | Type validation, size limits, virus scan |
| API Security | Rate limiting, API key rotation |
| Security Headers | X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy via middleware |
| JWT Algorithm | Pinned to HS256 (no algorithm confusion) |
| PII Masking | Email and PIB values masked in application logs |

### 10.4 Infrastructure Security

| Requirement | Implementation |
|-------------|----------------|
| Network Security | VPC, security groups, WAF |
| DDoS Protection | Cloudflare |
| Secrets Management | Environment variables, Vault |
| Container Security | Distroless images, scanning |
| Access Control | IAM roles, least privilege |

### 10.5 Compliance

| Regulation | Requirements |
|------------|--------------|
| ZZPL (primary) | Full compliance with Zakon o zaštiti podataka o ličnosti (Sl. glasnik RS, br. 87/2018). Data processing agreements, data protection officer, privacy policy. ZZPL is the primary regulatory framework for data protection in the Republic of Serbia. |
| GDPR (reference) | Alignment with GDPR principles as a reference standard for best practices |
| PCI DSS | Not storing payment data (Paddle handles as Merchant of Record) |

### 10.6 Legal & Compliance Flows

This section defines workflows for legal compliance, data processing agreements, and audit requirements.

#### 10.6.1 Data Processing Agreement (DPA) Flow

**For Enterprise Clients:**

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Enterprise │    │   Sales     │    │   Legal     │    │   Account   │
│   Signup    │───▶│   Review    │───▶│   Review    │───▶│   Active    │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
       │                  │                  │                  │
       ▼                  ▼                  ▼                  ▼
  DPA Required      Custom Terms?      Sign DPA         DPA Stored
  Flag Set           Review SLA        Countersign      in Vault
```

**DPA Database Schema:**
```sql
CREATE TABLE data_processing_agreements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    version VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    signed_by_customer VARCHAR(255),
    signed_by_customer_at TIMESTAMP WITH TIME ZONE,
    signed_by_saldora VARCHAR(255),
    signed_by_saldora_at TIMESTAMP WITH TIME ZONE,
    document_url VARCHAR(500),
    custom_clauses JSONB,
    valid_from DATE,
    valid_until DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT valid_dpa_status CHECK (status IN ('pending', 'customer_signed', 'active', 'expired', 'terminated'))
);
```

**DPA Requirements Checklist:**
- [ ] Data controller/processor relationship defined
- [ ] Sub-processors listed with notification obligations
- [ ] Data retention periods specified
- [ ] Data deletion procedures documented
- [ ] Security measures described
- [ ] Breach notification timeline (72 hours)
- [ ] Audit rights included
- [ ] Data transfer mechanisms (for EU data)

#### 10.6.2 Consent Management

**Consent Types:**

| Consent Type | Scope | Granularity | Revocable |
|--------------|-------|-------------|-----------|
| Basic Processing | Invoice OCR, data extraction | Required | No (service essential) |
| Analytics | Usage patterns, performance metrics | Organization-level | Yes |
| Marketing | Product updates, newsletters | User-level | Yes |

**Consent Database Schema:**
```sql
CREATE TABLE consent_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    user_id UUID NOT NULL REFERENCES users(id),
    consent_type VARCHAR(50) NOT NULL,  -- 'processing', 'analytics', 'marketing'
    granted BOOLEAN NOT NULL,
    granted_at TIMESTAMP WITH TIME ZONE,
    revoked_at TIMESTAMP WITH TIME ZONE,
    ip_address INET,
    user_agent TEXT,
    consent_text_version VARCHAR(20),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_consent_org ON consent_records(organization_id);
CREATE INDEX idx_consent_type ON consent_records(consent_type);
```

**Consent Revocation Process:**
1. User navigates to Organization Settings → Data & Privacy
2. Clicks "Opozovi saglasnost" for the relevant consent type
3. Confirmation dialog explains implications
4. On confirm: `revoked_at` timestamp set
5. Confirmation email sent to user

#### 10.6.3 Audit Export for Tax Inspections

**Serbian Tax Authority (Poreska Uprava) Requirements:**

When a tax inspection is requested, the system MUST provide:

| Export Type | Format | Content | Retention |
|-------------|--------|---------|-----------|
| Invoice Register | XML (eFaktura format) | All invoices in period | 10 years |
| Document Archive | ZIP with PDFs | Original uploaded documents | 10 years |
| Audit Trail | CSV/Excel | All actions on invoices | 10 years |
| VAT Summary | PDF/Excel | PDV-PP breakdown | 10 years |

**Audit Export Flow:**

```
Admin → Izveštaji → Izvoz za inspekciju
┌─────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  📋 Izvoz podataka za poresku inspekciju                            │
│                                                                      │
│  Period:  [01.01.2024] do [31.12.2024]                              │
│                                                                      │
│  Sadržaj izvoza:                                                    │
│  ☑ Registar faktura (XML)                                          │
│  ☑ Originalna dokumenta (PDF)                                      │
│  ☑ Revizorski trag (CSV)                                           │
│  ☑ PDV pregled (Excel)                                             │
│                                                                      │
│  Format: [ZIP arhiva ▼]                                             │
│                                                                      │
│  ⚠️ Ovaj izvoz će biti evidentiran u revizorskom tragu.            │
│                                                                      │
│  [Generiši izvoz]                                                   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

**Audit Export Schema:**
```sql
CREATE TABLE audit_exports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    requested_by UUID NOT NULL REFERENCES users(id),
    export_type VARCHAR(50) NOT NULL,
    date_from DATE NOT NULL,
    date_to DATE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    file_path VARCHAR(500),
    file_size_bytes BIGINT,
    invoice_count INTEGER,
    reason TEXT,  -- e.g., "Poreska kontrola br. 123/2025"
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT valid_export_status CHECK (status IN ('pending', 'processing', 'ready', 'downloaded', 'expired'))
);
```

**XML Export Format (eFaktura compatible):**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<RegistarFaktura xmlns="urn:saldora:export:v1">
  <Zaglavlje>
    <Organizacija>
      <Naziv>Računovodstvo Petrović d.o.o.</Naziv>
      <PIB>123456789</PIB>
      <MB>12345678</MB>
    </Organizacija>
    <PeriodOd>2024-01-01</PeriodOd>
    <PeriodDo>2024-12-31</PeriodDo>
    <DatumIzvoza>2025-01-15T10:30:00</DatumIzvoza>
    <BrojFaktura>1542</BrojFaktura>
  </Zaglavlje>
  <Fakture>
    <Faktura id="inv-001">
      <BrojFakture>2024-0001</BrojFakture>
      <DatumFakture>2024-01-15</DatumFakture>
      <DatumValute>2024-02-15</DatumValute>
      <Prodavac>
        <Naziv>Dobavljač ABC d.o.o.</Naziv>
        <PIB>987654321</PIB>
      </Prodavac>
      <Kupac>
        <Naziv>Računovodstvo Petrović d.o.o.</Naziv>
        <PIB>123456789</PIB>
      </Kupac>
      <Osnovica>100000.00</Osnovica>
      <PDV stopa="20">20000.00</PDV>
      <Ukupno>120000.00</Ukupno>
      <Valuta>RSD</Valuta>
      <DokumentRef>doc-uuid-here</DokumentRef>
    </Faktura>
    <!-- More invoices... -->
  </Fakture>
</RegistarFaktura>
```

#### 10.6.4 Data Retention & Deletion

**Retention Periods:**

| Data Type | Retention Period | Legal Basis |
|-----------|-----------------|-------------|
| Invoice data | 10 years | Serbian Accounting Law |
| Original documents | 10 years | Serbian Accounting Law |
| User accounts | Active + 2 years | Business necessity |
| Audit logs | 7 years | Compliance |
| Correction logs | 3 years | Quality monitoring |
| Session data | 30 days | Technical necessity |
| Temporary files | 24 hours | Processing |

**Right to Erasure (ZZPL Article 30):**

```
User Request → Validation → Partial Deletion → Confirmation
     │              │              │                │
     ▼              ▼              ▼                ▼
  Via email    Check if      Delete:           Email sent
  or in-app    legally       - Profile data    confirming
               required      - Preferences     what was
               to retain     - Session data    deleted
                             Retain:           and what
                             - Invoice data    was retained
                               (legal req.)    (with reason)
```

**Deletion Request Schema:**
```sql
CREATE TABLE deletion_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    organization_id UUID REFERENCES organizations(id),
    request_type VARCHAR(30) NOT NULL,  -- 'user_only', 'full_org', 'specific_data'
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    data_categories JSONB,  -- what was requested to be deleted
    retained_categories JSONB,  -- what was kept and why
    processed_by UUID REFERENCES users(id),
    processed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT valid_deletion_status CHECK (status IN ('pending', 'processing', 'completed', 'rejected'))
);
```

#### 10.6.5 Data Breach Notification

**Breach Response Timeline:**

| Timeframe | Action | Responsible |
|-----------|--------|-------------|
| 0-4 hours | Incident detection, initial assessment | Engineering |
| 4-24 hours | Impact analysis, containment | Security + Legal |
| 24-72 hours | Notify Poverenik (Serbian DPA) if required | Legal |
| 24-72 hours | Notify affected users if high risk | Legal + Support |
| 72 hours+ | Remediation, post-mortem | All teams |

**Breach Notification Template:**
```
Obaveštenje o bezbednosnom incidentu

Poštovani [Ime],

Obaveštavamo vas da je [datum] došlo do bezbednosnog incidenta
koji je mogao uticati na vaše podatke.

Šta se desilo:
[Opis incidenta]

Koji podaci su mogli biti ugroženi:
[Lista tipova podataka]

Šta smo preduzeli:
[Preduzete mere]

Šta vi možete preduzeti:
[Preporuke za korisnika]

Kontakt za dodatna pitanja:
privacy@saldora.rs

S poštovanjem,
Saldora Tim
```

### 10.7 Audit & Logging

**Logged Events:**
- Authentication events (login, logout, failed attempts)
- Data access (read, create, update, delete)
- Administrative actions
- API access
- Security events

**Log Retention:** 12 months minimum (invoice data follows 10-year retention per Serbian Accounting Law)

---

## 11. Deployment Architecture

### 11.1 Production Environment

The full app runs on a **single Hetzner CX32 VPS** behind Caddy. There is no Kubernetes cluster, no managed database, and no horizontal autoscaler. GPU inference is offloaded to **Modal.com** (scale-to-zero). Object storage is **Cloudflare R2**. Cloudflare also provides DNS, edge SSL, CDN, and DDoS protection.

```
                    ┌─────────────┐
                    │ Cloudflare  │
                    │ DNS+SSL+CDN │
                    └──────┬──────┘
                           │ HTTPS
                           ▼
                    ┌──────────────┐
                    │  Hetzner     │
                    │  VPS (CX32)  │
                    └──────┬───────┘
                           │ port 80/443
                           ▼
                    ┌──────────────┐
                    │    Caddy     │
                    │ reverse proxy│
                    └──┬────────┬──┘
                       │        │
       saldora.rs      │        │   api.saldora.rs
                       ▼        ▼
                ┌─────────┐ ┌──────────┐
                │ Next.js │ │ FastAPI  │
                │  :3000  │ │  :8000   │
                └─────────┘ └────┬─────┘
                                 │
                  ┌──────────────┼──────────────┐
                  ▼              ▼              ▼
            ┌──────────┐   ┌────────┐    ┌──────────┐
            │PostgreSQL│   │ Redis  │    │  Celery  │
            │  :5432   │   │ :6379  │    │  Worker  │
            └──────────┘   └────────┘    └─────┬────┘
                                               │ HTTPS
                                               ▼
                                       ┌──────────────┐
                                       │  Modal.com   │
                                       │  dots.ocr    │
                                       │  (A10G GPU)  │
                                       └──────────────┘

Object storage:  Cloudflare R2 (production), MinIO (local dev)
Email:           Resend
LLM:             Anthropic Claude Haiku
```

### 11.2 Production Service Topology

| Service | Container | Purpose |
|---------|-----------|---------|
| **Caddy** | `saldora-caddy` | Reverse proxy: routes `saldora.rs` → web, `api.saldora.rs` → API; Let's Encrypt TLS |
| **Next.js** | `saldora-web` | Frontend (port 3000) |
| **FastAPI** | `saldora-api` | Backend API (port 8000) |
| **PostgreSQL** | `saldora-postgres` | Database |
| **Redis** | `saldora-redis` | Cache + Celery broker |
| **OCR Worker** | `saldora-ocr-worker` | Celery worker; calls Modal for OCR and Claude for extraction |
| **Celery Beat** | `saldora-celery-beat` | Scheduled tasks (NBS rates, retention, backups, monthly archives) |

Compose file: `infra/docker/docker-compose.prod.yml` (env from `infra/docker/.env.prod`).

### 11.3 Scheduled Tasks (Celery Beat)

| Task | Schedule | Purpose |
|------|----------|---------|
| NBS exchange rates | Weekdays 08:30 | Fetch EUR/USD/CHF/GBP rates from NBS |
| Usage aggregation | Daily 02:00 | Reconcile invoice counts per org into `usage_records` |
| Data retention | Daily 03:00 | Clean up expired data per ZZPL |
| Database backup | Daily 04:00 UTC | pg_dump → ZIP with checksums → R2 |
| Monthly archives | 1st of month 06:00 | Generate per-org archive ZIPs and email to billing contact |

### 11.4 Backup & Recovery

- **Automated backups**: daily 04:00 UTC via Celery beat. SQL dump (gzip) + manifest with checksums, stored in R2 at `backups/db/saldora_YYYY-MM-DD.zip`. **30-day retention** (older backups auto-deleted).
- **Manual backup**: Celery task can be triggered on demand from the worker container.
- **Restore**: download the backup ZIP from R2, extract `.sql.gz`, pipe to `psql` against the postgres container.

### 11.5 CI/CD Pipeline

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Commit to  │───▶│ GitHub Acts │───▶│   Tests     │───▶│ SSH deploy  │
│   feature/  │    │  (lint+     │    │  (pytest +  │    │ to Hetzner  │
│   *  branch │    │   build)    │    │   jest)     │    │ via merge   │
└─────────────┘    └─────────────┘    └─────────────┘    └──────┬──────┘
                                                                │
                                                                ▼
                                                    docker compose up -d
                                                    --build (selective)
                                                    alembic upgrade head
```

Production deploys are issued by SSH'ing into the Hetzner VPS, pulling `main`, and rebuilding the affected service via the production compose file (see `docs/DEPLOYMENT.md`). There is no Kubernetes manifest set; staging is a separate VPS or a feature branch run locally.

### 11.6 Monitoring & Logging

Logging is currently container-stdout based (read via `docker logs`). Error tracking via Sentry is in place for the Next.js and FastAPI services. A full Prometheus/Grafana/Loki/Jaeger stack is **not deployed** at this scale; introduce only when the metrics they would surface justify the operational cost.

**Key signals tracked today:**
- Application errors via Sentry (frontend + backend).
- Per-task Celery success/failure logs via `docker logs saldora-ocr-worker`.
- Modal app metrics from the Modal dashboard (cold starts, GPU minutes, errors).
- Database backup success via the Celery beat task log.

---

## 12. Third-Party Integrations

### 12.1 APR Integration (Serbian Business Registry)

**Endpoint:** APR Public API

**Usage:**
- PIB verification
- Company information lookup
- Business status validation

**Caching Strategy:**
- Cache responses for 24 hours
- Background refresh for frequently accessed PIBs

### 12.2 Payment Integration (Paddle)

**Why Paddle:** Paddle operates as a Merchant of Record (MoR), meaning Paddle manages all payment transactions, VAT obligations, and tax compliance globally on behalf of Saldora. This is critical for the Serbian market because:
- Paddle assumes responsibility for calculating and collecting VAT in all jurisdictions
- No need for Saldora to register for VAT in individual countries
- Simplified financial reporting - one payout from Paddle instead of thousands of individual transactions

**Features Used:**
- Paddle Checkout for subscriptions
- Paddle Billing for subscription and billing management
- Webhooks for subscription events

**Webhook Events:**
- `subscription.created`
- `subscription.updated`
- `subscription.canceled`
- `transaction.completed`
- `transaction.payment_failed`

### 12.3 Email Service (Resend)

**Provider:** Resend is the sole transactional email provider in production. SendGrid is **not** used.

**Transactional Emails:**
- Welcome email
- Password reset
- New-registration admin notification (to `ADMIN_EMAIL`)
- Approval notification (when an admin flips an org from `pending` to `active`/`trial`)
- Monthly archive delivery (FR-4.7.5)
- Subscription notifications via Paddle (forwarded as needed)

### 12.4 Storage (Cloudflare R2)

**Production:** Cloudflare R2 (S3-compatible). **Local dev:** MinIO running in the dev compose. AWS S3 is supported by the storage service abstraction but is not the production target.

**Buckets:**
- `saldora-documents` — uploaded invoice documents
- `saldora-exports` — generated exports and monthly archive ZIPs
- `saldora-backups` — database backups (`backups/db/saldora_YYYY-MM-DD.zip`)

**Object Key Convention:**
Documents are namespaced by organization for multi-tenant isolation:
```
organizations/{organization_id}/invoices/{invoice_id}/original.{ext}
```

**Storage function policy:** R2/S3 calls are made through `boto3` and are therefore **synchronous**. Async code paths must wrap them with `asyncio.to_thread()` (see CLAUDE.md).

**Lifecycle Rules:**
- Documents: retained for the subscription period; **long-term retention responsibility is shifted to the customer** via the monthly archive ZIPs (FR-4.7.5). Customers must save those archives to comply with the 10-year retention under Zakon o računovodstvu.
- Exports: 30 days auto-delete
- Backups: **30 days retention** (auto-deleted by the backup task)

### 12.5 MiniMax Integration

MiniMax (minimax.rs) is the most widely used cloud accounting software in Serbia. Saldora integrates with MiniMax via both XML file export and direct REST API push.

#### 12.5.1 MiniMax XML Export

Generates an XML file compatible with MiniMax's import tool:
- **Stranke** (Partners): Deduplicated sellers by PIB — Sifra (PIB), Naziv, DavcnaStevilka, Naslov, Posta
- **Temeljnice** (Journal Entries): Generated from `accounting_intent.suggested_konta` — GlavaTemeljnice (date, partner, reference), VrsticeTemeljnice (konto + debit/credit amounts), DDV (VAT entries)

Available as `minimax_xml` format option in POST `/api/v1/export`.

#### 12.5.2 MiniMax REST API Integration

Direct push of invoices to MiniMax via their REST API:
- **Authentication:** OAuth 2.0 — POST `https://moj.minimax.rs/RS/AUT/OAuth20/Token`
- **Push received invoices:** POST `/api/orgs/{orgId}/receivedinvoices`
- **Customer management:** Find by PIB, create if not found
- **Currency lookup:** Get currency ID by ISO code
- Token caching with automatic refresh on 401

#### 12.5.3 Configuration

Per-organization credentials stored in `minimax_configs` table:
- `client_id`, `client_secret` — OAuth application credentials
- `username`, `password` — MiniMax user credentials
- `minimax_org_id` — MiniMax organization ID (integer)
- `is_active` — Enable/disable integration
- `last_sync_at` — Timestamp of last successful push

**API endpoints:** GET/PUT/PATCH `/api/v1/export/minimax/config`

#### 12.5.4 MiniMax API Field Reference (RS)

Field names and IDs validated against the MiniMax RS Swagger API spec:

**Country & Currency (Serbia):**
- Country ID: 3 (Code: "RS", Name: "Republika Srbija")
- Currency ID: 2 (Code: "RSD")

**ReceivedInvoice required fields:**
| API Field | Source | Notes |
|-----------|--------|-------|
| DocumentReference | invoice_number | Original invoice number (NOT InvoiceNumber) |
| Customer | {ID: customer_id} | FK reference |
| Currency | {ID: 2} | RSD default |
| PaymentType | "N" | N=Neplaćen, D=Dospeo, Z=Zatvoreno, P=Plaćen, R=Rata |
| DateIssued | invoice_date | ISO datetime |
| DateTransaction | invoice_date | |
| DateDue | due_date | |
| DateReceived | invoice_date | |
| InvoiceAmount | total_amount | Rounded to 2 decimals |
| InvoiceAmountDomesticCurrency | total_amount | Must equal InvoiceAmount for RSD |

**Customer creation required fields:**
| Field | Value |
|-------|-------|
| Country | {ID: 3} |
| CountryName | "Republika Srbija" |
| Currency | {ID: 2} |
| SubjectToVAT | "D" (not "Y") |
| PostalCode | Required, non-empty |

**VAT Rate mapping:**
| Serbian rate | MiniMax VatRateId | Code |
|-------------|-------------------|------|
| 20% | 4 | S |
| 10% | 5 | Z |
| 8% | 3 | P |
| 0% | 1 | N |

### 12.6 SEF Integration (eFaktura) — deprioritized

> **Status (April 2026):** SEF integration is **deprioritized** and is **not** part of any active milestone. Hospitality agencies report that the invoices they actually struggle with — paper deliveries from beverage distributors, small producers, fiscal receipts, and invoices from suppliers outside the VAT system — are precisely the ones SEF does not and probably will not soon cover. SEF as a secondary read-only data source remains as out-of-milestone ongoing work and may be revisited if a paying agency requests it.

The previous detailed SEF specification (connection setup, inbound sync, outbound push, status polling, OCR-hybrid merge, inbox UI, and error handling) has been removed from this revision of the SRS. If SEF work resumes, the spec will be reintroduced from version control history (SRS v3.2 and earlier) rather than maintained as dead text here.

#### 12.6.1 Removed sub-sections (for reference)

The removed sub-sections (preserved in version control under SRS v3.2) included: SEF Connection Setup, Inbound Invoice Sync (SEF → Saldora), Outbound Invoice Push (Saldora → SEF), SEF Status Polling (SEF has no native webhooks), SEF-OCR Hybrid Processing (UBL/XML data merged with OCR for accuracy), SEF Inbox UI, and SEF Error Handling. The associated `sef_connections` and `sef_invoices` tables were never built and are not present in the schema.

### 12.7 NBS Integration (National Bank of Serbia)

The system SHOULD integrate the NBS exchange rate list for foreign currency conversion to RSD.

#### 12.7.1 Overview

NBS publishes a daily middle exchange rate for all currencies traded on the foreign exchange market. The rate list is updated every business day and is available via a public API.

**Usage:**
- Display RSD equivalent for invoices in foreign currencies (EUR, USD, CHF, GBP)
- Convert invoice amounts denominated in foreign currency to RSD
- Use the NBS middle rate on the invoice date
- Archive the rate used for conversion for audit purposes

#### 12.7.2 API Access

**API endpoint:** `https://nbs.rs/kursnaListaMod498/kursnaLista`

**Note:** NBS provides a public, free-to-use API for the exchange rate list. The API returns the rate list in XML or JSON format.

**Configuration:**

```json
{
  "nbs_exchange_rates": {
    "api_url": "https://nbs.rs/kursnaListaMod498/kursnaLista",
    "cache_ttl_hours": 24,
    "default_currency": "RSD",
    "supported_currencies": ["EUR", "USD", "CHF", "GBP"],
    "fallback_on_holiday": true
  }
}
```

#### 12.7.3 Caching Strategy

- Exchange rate list is cached for 24 hours
- For non-business days (weekends, holidays), the last available rate list is used
- Cache is refreshed every business day at 08:30 (NBS publishes the rate list by 08:00)
- In case of NBS API unavailability, the last cached rate list is used

#### 12.7.4 Implementation

**Foreign currency invoice conversion:**

```python
async def get_exchange_rate(currency: str, date: date) -> Decimal:
    """
    Fetch NBS middle rate for the given currency and date.
    """
    # 1. Check cache
    cached_rate = await cache.get(f"nbs_rate:{currency}:{date}")
    if cached_rate:
        return Decimal(cached_rate)

    # 2. Check database
    db_rate = await db.query(
        ExchangeRate,
        where=and_(
            ExchangeRate.currency == currency,
            ExchangeRate.rate_date == date
        )
    )
    if db_rate:
        await cache.set(f"nbs_rate:{currency}:{date}", str(db_rate.middle_rate), ttl=86400)
        return db_rate.middle_rate

    # 3. Fetch from NBS API
    rate = await nbs_api.fetch_rate(currency, date)
    if rate:
        await save_exchange_rate(currency, date, rate)
        return rate.middle_rate

    # 4. Fallback: use last known rate
    latest_rate = await get_latest_known_rate(currency)
    return latest_rate.middle_rate if latest_rate else None


async def convert_to_rsd(amount: Decimal, currency: str, invoice_date: date) -> dict:
    """
    Convert amount from foreign currency to RSD using NBS rate.
    """
    if currency == "RSD":
        return {"rsd_amount": amount, "exchange_rate": Decimal("1"), "rate_date": invoice_date}

    rate = await get_exchange_rate(currency, invoice_date)
    if not rate:
        return {"rsd_amount": None, "exchange_rate": None, "error": "Rate unavailable"}

    rsd_amount = (amount * rate).quantize(Decimal("0.01"))
    return {
        "rsd_amount": rsd_amount,
        "exchange_rate": rate,
        "rate_date": invoice_date,
        "source": "NBS middle rate"
    }
```

#### 12.7.5 Database Schema

```sql
CREATE TABLE exchange_rates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    currency VARCHAR(3) NOT NULL,
    rate_date DATE NOT NULL,

    -- Rates
    buying_rate DECIMAL(15, 6),
    middle_rate DECIMAL(15, 6) NOT NULL,
    selling_rate DECIMAL(15, 6),

    -- Unit (e.g., 1 EUR = X RSD, but 100 JPY = X RSD)
    unit INTEGER NOT NULL DEFAULT 1,

    -- Metadata
    source VARCHAR(20) NOT NULL DEFAULT 'NBS',
    fetched_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT unique_currency_date UNIQUE (currency, rate_date)
);

CREATE INDEX idx_exchange_rates_currency ON exchange_rates(currency);
CREATE INDEX idx_exchange_rates_date ON exchange_rates(rate_date);
CREATE INDEX idx_exchange_rates_lookup ON exchange_rates(currency, rate_date DESC);
```

**Celery periodic task for rate list updates:**

```python
# Celery beat configuration
CELERY_BEAT_SCHEDULE = {
    "fetch-nbs-exchange-rates": {
        "task": "fetch_nbs_exchange_rates",
        "schedule": crontab(hour=8, minute=30, day_of_week="1-5"),  # Business days at 08:30
    },
}

@celery_app.task(name="fetch_nbs_exchange_rates")
async def fetch_nbs_exchange_rates():
    """
    Fetch daily NBS exchange rate list and save to database.
    """
    today = date.today()

    for currency in ["EUR", "USD", "CHF", "GBP"]:
        try:
            rate_data = await nbs_api.fetch_rate(currency, today)
            if rate_data:
                await db.upsert(ExchangeRate(
                    currency=currency,
                    rate_date=today,
                    buying_rate=rate_data.buying_rate,
                    middle_rate=rate_data.middle_rate,
                    selling_rate=rate_data.selling_rate,
                    unit=rate_data.unit,
                    source="NBS"
                ))
                # Update cache
                await cache.set(
                    f"nbs_rate:{currency}:{today}",
                    str(rate_data.middle_rate),
                    ttl=86400
                )
        except Exception as e:
            logger.error(f"Error fetching rate for {currency}: {e}")
```

---

## 13. User Interface Requirements

### 13.1 Design System

**Color Palette:**
- Primary: Violet (#7c3aed)
- Secondary: Indigo (#6366f1)
- Success: Emerald (#10b981)
- Warning: Amber (#f59e0b)
- Error: Red (#ef4444)
- Background: White (#ffffff)
- Text: Gray-900 (#0f172a)

**Typography:**
- Font Family: Inter
- Headings: Bold, tracking-tight
- Body: Regular, text-base

**Spacing:**
- Base unit: 4px
- Consistent padding/margin scale

### 13.2 Key Screens

| Screen | Description |
|--------|-------------|
| Landing Page | Marketing page (saldora.rs) with hospitality-positioned features and pricing |
| Login / Register / Awaiting Approval | Auth screens; new orgs land in `/awaiting-approval` until admin approval (FR-4.1.5) |
| **Pregled portfelja** (`/pregled`) | Default home for agency users — grid of clients with health indicators (FR-4.18.1) |
| **Klijent radna tabla** (`/klijenti/{id}`) | Per-client workspace with Hronologija (default), Fakture, Izveštaji, Pravila tabs (FR-4.18.2) |
| Klijenti (`/klijenti`) | Quick-jump list of all clients (CRUD remains here) |
| Pravila (org-wide) | Editor for agency-wide automation rules + browser of per-client scoped rules |
| Arhiviranje | Configure and trigger monthly archive ZIPs (FR-4.7.5) |
| Katalog proizvoda | Canonical products + aliases + merge UI |
| Dashboard | Global org stats (kept for the moment, may be folded into Pregled later) |
| Upload | Drag & drop upload interface (within Fakture tab) |
| Invoice Detail | Side-by-side document and data, EditableField with confidence badges, line items + tax groups editing |
| Export | Format selection, field mapping (XLSX, CSV, JSON, MiniMax XML, MiniMax REST push) |
| Settings | Profile, team, API keys, MiniMax credentials |
| Billing | Plan selection, usage, invoices |

### 13.3 Responsive Breakpoints

| Breakpoint | Width | Target |
|------------|-------|--------|
| sm | 640px | Mobile landscape |
| md | 768px | Tablet |
| lg | 1024px | Desktop |
| xl | 1280px | Large desktop |
| 2xl | 1536px | Extra large |

### 13.4 Accessibility

- WCAG 2.1 AA compliance
- Keyboard navigation support
- Screen reader compatibility
- Sufficient color contrast
- Focus indicators
- Alt text for images

### 13.5 Cyrillic & Latin Script Support

Serbian language uses two scripts — Cyrillic and Latin. The system MUST fully support both scripts to serve all users.

- The system MUST support displaying the interface in both scripts (Cyrillic and Latin)
- Users can select their preferred script in profile settings
- OCR must recognize both scripts on invoices
- All reports and exports must support both scripts
- Default script: Latin
- A script switch button must be available in the application header

| Requirement | Specification |
|-------------|---------------|
| Default script | Latin (wider user coverage) |
| Switch option | Visible toggle in the application header |
| Preference persistence | Save user's choice in profile settings |
| Scope | All UI elements, error messages, helper texts |
| OCR support | Recognition of both scripts on input invoices |
| Reports & exports | Generated in the selected script |
| Exception | Technical terms (API, URL, etc.) remain in Latin script |

---

## 14. Testing Requirements

### 14.1 Testing Strategy

| Test Type | Coverage Target | Tools |
|-----------|-----------------|-------|
| Unit Tests | 80% | Jest, Pytest |
| Integration Tests | 70% | Pytest, Supertest |
| E2E Tests | Critical paths | Playwright |
| Performance Tests | Key endpoints | k6 |
| Security Tests | OWASP Top 10 | OWASP ZAP |

### 14.2 Test Cases Categories

**Authentication Tests:**
- Registration flow
- Login with valid/invalid credentials
- Password reset
- Token refresh
- Session expiration

**Invoice Processing Tests:**
- Upload various formats
- OCR accuracy validation
- Field extraction accuracy
- Batch processing
- Error handling

**Integration Tests:**
- APR API integration
- Paddle webhook handling
- Email delivery
- File storage operations

### 14.3 Performance Benchmarks

| Scenario | Target | Threshold |
|----------|--------|-----------|
| Page load (LCP) | < 2s | < 4s |
| Single invoice OCR | < 5s | < 10s |
| Batch (50 docs) | < 2min | < 5min |
| API response | < 200ms | < 500ms |
| Search query | < 500ms | < 1s |

---

## 15. Appendices

### 15.1 Glossary

| Term | Definition |
|------|------------|
| APR | Agencija za Privredne Registre - Serbian Business Registers Agency |
| PIB | Poreski Identifikacioni Broj - Tax Identification Number (Serbia: 9 digits, Montenegro: 8 digits) |
| OIB | Osobni Identifikacijski Broj - Personal Identification Number (Croatia: 11 digits) |
| JIB | Jedinstveni Identifikacioni Broj - Unique Identification Number (Bosnia & Herzegovina: 13 digits) |
| PDV | Porez na Dodatu Vrednost - Value Added Tax |
| OCR | Optical Character Recognition |
| NER | Named Entity Recognition |
| JWT | JSON Web Token |

### 15.2 Serbian Invoice Standards

**Required Invoice Fields (per Serbian law):**
- Invoice number and date
- Seller name, address, PIB, MB
- Buyer name, address, PIB (if applicable)
- Description of goods/services
- Quantity and unit price
- Tax base, tax rate, tax amount
- Total amount
- Payment terms

**VAT Rates:**
- Standard rate: 20%
- Reduced rate: 10%
- Exempt: 0%

### 15.3 Sample Invoice Structure

```
┌────────────────────────────────────────────────────────────┐
│                      ФАКТУРА / FAKTURA                      │
│                         Br: 2025-042                        │
├────────────────────────────────────────────────────────────┤
│ Datum: 15.01.2025                                          │
│ Valuta: 15.02.2025                                         │
├────────────────────────────────────────────────────────────┤
│ ПРОДАВАЦ / PRODAVAC:          │ КУПАЦ / KUPAC:            │
│ Firma ABC d.o.o.              │ Kompanija XYZ d.o.o.      │
│ Bulevar Kralja Aleksandra 1   │ Cara Dušana 15            │
│ 11000 Beograd                 │ 21000 Novi Sad            │
│ PIB: 123456789                │ PIB: 987654321            │
│ MB: 12345678                  │ MB: 87654321              │
├────────────────────────────────────────────────────────────┤
│ R.br │ Opis                    │ Kol. │ Cena   │ Iznos    │
├──────┼─────────────────────────┼──────┼────────┼──────────┤
│ 1    │ Usluge konsaltinga     │ 10   │ 5.000  │ 50.000   │
│ 2    │ Izrada dokumentacije   │ 1    │ 10.000 │ 10.000   │
├────────────────────────────────────────────────────────────┤
│                                  Osnovica:      60.000 RSD │
│                                  PDV (20%):     12.000 RSD │
│                                  ─────────────────────────│
│                                  UKUPNO:        72.000 RSD │
└────────────────────────────────────────────────────────────┘
```

### 15.4 References

1. Serbian Law on Accounting (Zakon o računovodstvu)
2. Serbian VAT Law (Zakon o PDV-u)
3. ZZPL - Serbian Law on Personal Data Protection (Zakon o zaštiti podataka o ličnosti)
4. GDPR - General Data Protection Regulation (reference framework)
5. APR API Documentation
6. NBS Exchange Rate API (Kursna lista Narodne banke Srbije)
7. dots.ocr Documentation (Vision-Language Model) — https://github.com/rednote-hilab/dots.ocr
8. vLLM Documentation (Model Inference Server) — https://docs.vllm.ai
9. Anthropic Claude API Documentation — https://docs.anthropic.com
10. FastAPI Documentation
11. Next.js Documentation
12. Paddle Documentation (Payment Processing)

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | January 2025 | Saldora Team | Initial release |
| 1.1 | January 2025 | Saldora Team | Added: Business Logic & Validation Rules (4.9), Human-in-the-Loop & Feedback System (9.9), Legal & Compliance Flows (10.6) |
| 1.2 | January 2025 | Saldora Team | Added: Accounting Intent Layer (4.10), Automation Rules Engine (4.11), SEF Integration (12.5), Expanded Feedback Loop Implementation (9.9.7) |
| 1.3 | January 2025 | Saldora Team | Updated OCR stack: dots.ocr (VLM) as primary engine with unified layout+OCR, EasyOCR as fallback, removed separate LayoutParser (Tesseract removed) |
| 2.0 | February 2026 | Saldora Team | Serbian market alignment: removed model training/retraining (pre-trained models only), ZZPL as primary data protection law (GDPR as reference), Paddle instead of Stripe, KPR/KIR terminology, SEF polling instead of webhooks, NBS exchange rate integration, Cyrillic/Latin script support, PIB constraint for foreign entities, 10-year document retention |
| 2.1 | February 2026 | Saldora Team | dots.ocr architecture: vLLM HTTP server sidecar (GPU) + lightweight OCR worker (CPU, OpenAI client), removed EasyOCR fallback (manual review instead), skip preprocessing for VLM |
| 2.2 | February 2026 | Saldora Team | LLM-based field extraction (Anthropic Claude) as primary method with regex fallback. Added `tax_groups` for multi-rate PDV breakdowns (per-section, not merged). Updated data model: inline JSON columns for seller/buyer/line_items/tax_groups (removed companies/documents FK tables). Added `raw_llm_output` for debugging. Per-field confidence scoring with `needs_review` flag. Enhanced math validation: tax groups consistency check, tax amount not recomputed from rate. Updated invoice detail UI: EditableField with confidence badges, line items editing, tax groups editing, field-level validation warnings, Toast feedback. |
| 2.3 | March 2026 | Saldora Team | Added fiscal receipt PIB extraction rules (4.9.2a): buyer ID type-code prefix handling, store/branch number disambiguation, post-extraction sanitization. Added multi-country tax ID validation spec (4.9.2b): OIB (Croatia), JIB (BiH), Montenegro PIB, EDB (North Macedonia), Slovenian Davčna, EU VAT IDs. Updated glossary with OIB and JIB terms. |
| 2.4 | March 2026 | Saldora Team | Added Invoice Template Learning & LLM Cost Optimization spec (9.9): layout fingerprinting, template storage model, template-based field extraction with three-tier fallback chain, automatic template learning from LLM extractions, cost tracking metrics. |
| 2.5 | March 2026 | Saldora Team | Added Client Management for Agency plan (4.12): client CRUD with soft-delete, auto-assignment of invoices to clients via PIB matching after OCR, invoice scoping by client_id, sidebar client selector. Added clients table (7.2.4), client_id FK on invoices. Feature gated via CLIENT_MANAGEMENT flag. |
| 2.6 | March 2026 | Saldora Team | Replaced PDV book generation (KPR/KIR, M13) with Invoice Reports feature (4.13): denormalized invoice_line_items table populated at OCR completion and on edits; five pre-built report templates (received goods, spending by supplier, monthly breakdown, price comparison, expense summary) at /api/v1/reports/; zero LLM cost; CSV export; frontend page at /{orgSlug}/izvestaji; PRO plan feature gate. |
| 2.7 | March 2026 | Saldora Team | Added line item discount/tax_base fields. Added invoice_line_items to DB schema (7.2.5). Updated duplicate detection to hard block (4.4.3). Added Email Ingestion Pipeline spec (4.14): dedicated inbound address per org, attachment extraction, auto-processing, Postmark webhook, security controls, confirmation emails. Rebranded Saldora → Saldora. |
| 2.8 | March 2026 | Saldora Team | Added Product Catalog spec (4.15): canonical product names, aliases (JSONB), categories, selling prices, margins, pg_trgm fuzzy matching, product_id FK on invoice_line_items, CRUD + merge API at /api/v1/products/. Added four procurement intelligence report endpoints (4.13.2.6–4.13.2.9): /kalkulacija, /ruc, /spending-by-category, /dpu (dnevna evidencija robe). Updated /izvestaji frontend to unified page with three group pills (Opšti, Nabavka i prodaja, Upravljanje); removed separate /katalog and /dpu routes. Added product_catalog to DB schema (7.2.6). Renamed "Šank lista" → "Dnevna evidencija robe"; renamed "Ugostiteljstvo" → "Nabavka i prodaja". Bug fixes: line items now sync on invoice verification; batch delete cascades to correction_logs and line_items; monthly breakdown shows PDV % and PDV iznos columns; verification error messages translated to Serbian. |
| 2.9 | March 2026 | Saldora Team | Added In-App Support System spec (4.16). Updated MiniMax API field reference (12.5.4). Updated security hardening details (10.1, 10.3). Added serverless GPU deployment options (9.7). Updated confidence display from percentages to text labels (4.3.3). |
| 3.0 | March 2026 | Saldora Team | Client management: replaced soft-delete with hard DELETE (unlinks invoices); added toggle-active endpoint (4.12.1); added retroactive PIB assignment on client creation (4.12.2). Reports: added client_id filter to all report endpoints and query parameter table (4.13.2); added client_id FK to invoice_line_items schema (4.13.1, 7.2.5, migration 0008). Billing: documented write-only usage_records counter for plan limit checks; deleting invoices no longer resets monthly usage (4.7.2). Duplicate detection: clarified 409 response, verified/exported-only scope, and ?force=true admin override (4.4.3). |

| 3.1 | April 2026 | Saldora Team | Added payment tracking (FR-4.7.4): payment_status, paid_amount, paid_date fields on invoices; single and batch payment endpoints; payment_status filter on invoice list; open items and aging reports under /reports/. Added automated archive export spec (FR-4.7.5): monthly ZIP delivery via email with data retention responsibility shifted to end user. |
| 3.2 | April 2026 | Saldora Team | Removed payment tracking (FR-4.7.4) — Saldora is intelligence-only. Deprioritized webhooks (FR-4.8.2) and SEF integration (12.6). Replaced PDV books (KPR/KIR) with intelligence reports (FR-4.13). Consolidated archive export tables (audit_exports → scheduled_export_logs). Rebrand: Saldora → Saldora. |
| 4.0 | 2026-04-29 | Saldora Team | **Hospitality pivot.** Repositioned the document as the source-of-truth for the post-pivot product (intelligence layer for Serbian accounting agencies handling hospitality clients). New top matter ("current thesis"). Updated personas (1.4, 2.3) — agency owners and bookkeepers as primary; paušalci dropped as a persona. Added FR-4.1.5 manual approval gate (subscription_status, /awaiting-approval, admin_orgs.py) and FR-4.1.6 invitations/join requests. Expanded Section 4.12 with FR-4.12.5 client_events log and FR-4.12.6 rule_client_associations; removed sidebar selector in favor of client-first UI. Added Section 4.17 (Out of Scope / Dropped) consolidating dropped features: paušal module, client portal, compliance watchdog, foreign reverse-charge module, payment tracking, webhooks, EasyOCR fallback, Stripe, image preprocessing for VLM. Added Section 4.18 (Client-First UI / M19) documenting `/pregled`, `/klijenti/{id}`, Hronologija/Fakture/Izveštaji/Pravila tabs, sidebar restructure. Added Section 4.19 (Hospitality Legal Forms / M20) marked deferred until accountant meeting; documented kalkulacije, šank lista, cenovnik, KEP, popis as the next layer with data foundation in place. Marked Section 4.14 (email ingestion) and 4.16 (in-app support) as planned/not yet wired. Updated tech stack (Section 6) to Modal-hosted dots.ocr (replacing vLLM container), Hetzner CX32 single-VPS docker-compose (replacing k8s), Cloudflare R2 (prod) + MinIO (dev), Resend (only). Replaced Section 11 deployment architecture with single-host Caddy/FastAPI/Next.js/PostgreSQL/Redis/Celery topology. Removed all SEF integration sub-sections (12.6.2–12.6.8) — kept a stub noting deprioritization and pointing to v3.2 for the prior spec. Added 7.2.7 (client_events) and 7.2.8 (rule_client_associations) DB schemas; documented subscription_status semantics on organizations (7.2.2). Updated UI key screens (13.2). Various stale-reference cleanup (fakturaai.rs → saldora.rs, fakturaai DB column names → saldora). |

---

**End of Document**
