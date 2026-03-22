# Software Requirements Specification (SRS)
# Saldora - AI-Powered Invoice Processing Platform

**Version:** 2.7
**Date:** March 2026
**Status:** Draft

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Overall Description](#2-overall-description)
3. [System Architecture](#3-system-architecture)
4. [Functional Requirements](#4-functional-requirements)
   - 4.9 [Business Logic & Validation Rules](#49-business-logic--validation-rules)
   - 4.10 [Accounting Intent Layer](#410-accounting-intent-layer)
   - 4.11 [Automation Rules Engine](#411-automation-rules-engine)
   - 4.12 [Client Management (Agency)](#412-client-management-agency)
   - 4.13 [Invoice Reports (Izveštaji)](#413-invoice-reports-izveštaji)
   - 4.14 [Email Ingestion Pipeline](#414-email-ingestion-pipeline)
5. [Non-Functional Requirements](#5-non-functional-requirements)
6. [Tech Stack](#6-tech-stack)
7. [Database Design](#7-database-design)
8. [API Specification](#8-api-specification)
9. [AI/ML Components](#9-aiml-components)
   - 9.9 [Human-in-the-Loop & Feedback System](#99-human-in-the-loop--feedback-system)
10. [Security Requirements](#10-security-requirements)
    - 10.6 [Legal & Compliance Flows](#106-legal--compliance-flows)
11. [Deployment Architecture](#11-deployment-architecture)
12. [Third-Party Integrations](#12-third-party-integrations)
    - 12.5 [SEF Integration (eFaktura)](#125-sef-integration-efaktura)
13. [User Interface Requirements](#13-user-interface-requirements)
14. [Testing Requirements](#14-testing-requirements)
15. [Appendices](#15-appendices)

---

## 1. Introduction

### 1.1 Purpose

This Software Requirements Specification (SRS) document provides a comprehensive description of the Saldora platform (formerly FakturaAI) - an AI-powered invoice processing system designed specifically for the Serbian market. The document outlines functional and non-functional requirements, system architecture, and technical specifications.

### 1.2 Scope

FakturaAI is a SaaS platform that enables accountants, accounting agencies, and businesses in Serbia to:

- Automatically extract data from invoices using AI-powered OCR
- Process both Cyrillic and Latin script documents
- Verify business entities through APR (Serbian Business Registers Agency) integration
- Export structured data to various formats (Excel, CSV, JSON)
- Manage and organize invoice data efficiently

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

- Independent accountants
- Accounting agencies
- Small and medium enterprises (SMEs)
- Large corporations with high invoice volumes
- Financial departments

### 1.5 Document Conventions

- **MUST** - Mandatory requirement
- **SHOULD** - Recommended requirement
- **MAY** - Optional requirement

---

## 2. Overall Description

### 2.1 Product Perspective

FakturaAI operates as a standalone web application with the following integration points:

```
┌─────────────────────────────────────────────────────────────────┐
│                        FakturaAI Platform                        │
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

| Feature | Description | Priority |
|---------|-------------|----------|
| Invoice Upload | Multi-format document upload (PDF, JPG, PNG, TIFF) | P0 |
| AI Data Extraction | Automatic extraction of invoice fields | P0 |
| Cyrillic/Latin Support | Full support for Serbian scripts | P0 |
| PIB Verification | Real-time verification against APR database | P0 |
| Data Export | Export to Excel, CSV, JSON formats | P0 |
| Batch Processing | Process multiple invoices simultaneously | P1 |
| User Management | Multi-user accounts with role-based access | P1 |
| Dashboard & Analytics | Usage statistics and processing history | P1 |
| Client Management | Manage clients and scope invoices per client (Agency plan) | P1 |
| API Access | RESTful API for third-party integrations | P2 |
| Custom Integrations | Webhooks and custom export templates | P2 |

### 2.3 User Classes and Characteristics

#### 2.3.1 Individual Accountant
- Processes 50-200 invoices/month
- Needs simple, intuitive interface
- Price-sensitive
- Limited technical knowledge

#### 2.3.2 Accounting Agency
- Processes 500-5000 invoices/month
- Manages multiple clients via Client Management (create, update, soft-delete)
- Invoices auto-assigned to clients via PIB matching after OCR
- Sidebar client selector for context-based invoice scoping
- Requires batch processing
- Needs API access for integration

#### 2.3.3 Enterprise User
- Processes 5000+ invoices/month
- Requires custom integrations
- Needs SLA guarantees
- Dedicated support required

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
- Invoice documents are legible (not severely damaged or blurred)
- APR API remains available and maintains current data format

**Dependencies:**
- APR for PIB verification (requires commercial contract or licensed intermediary)
- Cloud storage provider (AWS S3 or Cloudflare R2)
- Payment processor (Paddle) as Merchant of Record

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
│  │ vLLM Server   │  │ │  │ PostgreSQL │  │ │  │   S3/R2        │  │
│  │ - dots.ocr VLM│  │ │  │            │  │ │  │   Compatible   │  │
│  │ (GPU sidecar) │  │ │  └────────────┘  │ │  └────────────────┘  │
│  └────────────────┘  │ │  ┌────────────┐  │ └──────────────────────┘
│  ┌────────────────┐  │ │  │   Redis    │  │
│  │ OCR Worker     │  │ │  │  (Cache)   │  │
│  │(Celery+OpenAI) │  │ │  └────────────┘  │
│  └────────────────┘  │ └──────────────────┘
│  ┌────────────────┐  │
│  │ LLM Extractor  │  │
│  │ (Claude API)   │  │
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
│  │ Billing Service │    │  Queue Service  │    │ Webhook Service │  │
│  │  - Paddle int.  │    │ - Celery tasks  │    │  - Notifications│  │
│  │  - Usage track  │    │ - Job status    │    │  - Callbacks    │  │
│  │  - Invoicing    │    │ - Retry logic   │    │  - Events       │  │
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
| **Description** | System MUST allow users to register using email and password |
| **Input** | Email, password, company name (optional) |
| **Output** | User account created, verification email sent |
| **Validation** | Email format, password strength (min 8 chars, 1 uppercase, 1 number) |

#### FR-4.1.2 User Login
| ID | FR-4.1.2 |
|----|----------|
| **Description** | System MUST authenticate users via email/password or OAuth |
| **Input** | Email, password OR OAuth token |
| **Output** | JWT access token, refresh token |
| **Session** | Access token expires in 1 hour, refresh token in 7 days |

#### FR-4.1.3 Password Reset
| ID | FR-4.1.3 |
|----|----------|
| **Description** | System MUST allow password reset via email |
| **Flow** | Request reset → Email with link → New password form → Confirmation |

#### FR-4.1.4 Role-Based Access Control
| ID | FR-4.1.4 |
|----|----------|
| **Description** | System MUST support multiple user roles |
| **Roles** | Admin, Manager, Operator, Viewer |

| Role | Permissions |
|------|-------------|
| Admin | Full access, billing, team management |
| Manager | Invoice processing, export, team view |
| Operator | Invoice processing, export |
| Viewer | Read-only access to processed invoices |

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
| **Display** | Per-field confidence badges (color coded: green > 80%, yellow 60-80%, red < 60%) |
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
| **Description** | System MUST detect and block duplicate invoices |
| **Criteria** | Same invoice number + seller PIB within the same organization |
| **Action** | 🚫 Block upload with "Faktura sa ovim brojem od ovog dobavljača već postoji" |
| **Override** | Admin can force-process with explicit confirmation |

**Duplicate Detection Logic:**
```
DUPLICATE_CHECK(invoice, organization_id):
  IF EXISTS(
    invoice_number == invoice.invoice_number
    AND seller_pib == invoice.seller.pib
    AND organization_id == organization_id
    AND status != 'error'
  ):
    BLOCK("Faktura sa ovim brojem od ovog dobavljača već postoji")
    SHOW_LINK_TO_EXISTING(existing_invoice_id)
    ALLOW_ADMIN_OVERRIDE("Ipak obradi")
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

#### FR-4.7.3 Processing History
| ID | FR-4.7.3 |
|----|----------|
| **Description** | System MUST maintain searchable processing history |
| **Search** | By date, invoice number, seller/buyer, amount |
| **Retention** | Minimum 10 years (per Serbian Accounting Law) |

### 4.8 API Access

#### FR-4.8.1 REST API
| ID | FR-4.8.1 |
|----|----------|
| **Description** | System MUST provide REST API for programmatic access |
| **Authentication** | API key or OAuth 2.0 |
| **Rate Limiting** | Based on subscription tier |

#### FR-4.8.2 Webhook Notifications
| ID | FR-4.8.2 |
|----|----------|
| **Description** | System SHOULD support webhook callbacks |
| **Events** | Processing complete, error occurred, export ready |
| **Retry** | 3 retries with exponential backoff |

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

This section defines the **AccountingIntent** - a critical domain model that sits between raw invoice extraction and accounting system export. This transforms FakturaAI from an "OCR tool" into an "accounting intelligence platform".

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

This section defines the Client Management feature available exclusively to organizations on the Agency plan. It enables accounting agencies to manage their client companies and scope invoices per client.

**Feature Gate:** The entire Client Management feature is gated behind the `CLIENT_MANAGEMENT` feature flag, which MUST be enabled only for the Agency plan.

#### FR-4.12.1 Client CRUD
| ID | FR-4.12.1 |
|----|-----------|
| **Description** | System MUST allow Agency-plan users to create, list, update, and soft-delete clients |
| **Create** | Name (required), PIB (required, unique per organization, validated format), contact email, address, notes |
| **List** | Paginated list with search by name or PIB; supports `?search=` and `?page=`/`?page_size=` query params |
| **Update** | All client fields except `organization_id` and `id` |
| **Soft-Delete** | Sets `is_active = false`; client data retained for audit; invoices remain linked |
| **Authorization** | Only users in organizations with `CLIENT_MANAGEMENT` feature flag enabled |

#### FR-4.12.2 Invoice Auto-Assignment via PIB Matching
| ID | FR-4.12.2 |
|----|-----------|
| **Description** | After OCR extraction, the system MUST automatically assign an invoice to the matching client based on the seller PIB |
| **Matching Logic** | Compare extracted `seller.pib` against all active clients' PIBs within the same organization |
| **Match Found** | Set `invoice.client_id` to the matched client's ID |
| **No Match** | Leave `invoice.client_id` as NULL; invoice remains unassigned |
| **Timing** | Assignment occurs during the post-OCR processing pipeline, before the invoice is saved |

#### FR-4.12.3 Invoice Scoping by Client
| ID | FR-4.12.3 |
|----|-----------|
| **Description** | System MUST support filtering invoices by `client_id` |
| **Query Parameter** | `GET /invoices?client_id={uuid}` returns only invoices assigned to that client |
| **No Filter** | When `client_id` is omitted, all organization invoices are returned |
| **Authorization** | Client MUST belong to the requesting user's organization |

#### FR-4.12.4 Client Selector in Sidebar
| ID | FR-4.12.4 |
|----|-----------|
| **Description** | System MUST provide a client selector in the sidebar for Agency-plan users |
| **Behavior** | Selecting a client filters the invoice list and dashboard to that client's invoices |
| **Default** | "Svi klijenti" (All clients) shows all invoices across all clients |
| **Visibility** | The selector is only visible when `CLIENT_MANAGEMENT` feature flag is enabled |

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
```

#### 4.13.2 Report Templates

All five report endpoints live under `/api/v1/reports/` and accept a common set of query parameters:

| Parameter | Type | Description |
|-----------|------|-------------|
| `date_from` | `YYYY-MM-DD` | Start of reporting period (required) |
| `date_to` | `YYYY-MM-DD` | End of reporting period (required) |
| `supplier_pib` | String | Optional — filter to a single supplier |
| `search` | String | Optional — keyword filter on item description (case-insensitive) |

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

#### 4.13.3 CSV Export

Every report endpoint accepts an `Accept: text/csv` header (or `?format=csv` query parameter) and returns a UTF-8 BOM CSV with:

- Semicolon delimiter
- Comma as decimal separator (Serbian locale)
- Serbian column headers
- Filename: `izvestaj_{report_type}_{date_from}_{date_to}.csv`

#### 4.13.4 Frontend Page

| Requirement | Detail |
|-------------|--------|
| **Route** | `/{orgSlug}/izvestaji` |
| **Template selection** | Card-based UI — one card per report template |
| **Filters** | Date range picker, optional supplier PIB/name field, optional keyword search |
| **Results** | Rendered in a sortable table below the filter bar |
| **Export** | "Izvezi CSV" button — triggers browser file download |
| **Plan gate** | Non-PRO users see an upgrade modal instead of the filter form |

---

### 4.14 Email Ingestion Pipeline

This section defines the Email Ingestion feature, which allows organizations to receive invoices via a dedicated email address and automatically route them into the processing pipeline — eliminating manual upload for the majority of invoices.

**Feature Gate:** Email Ingestion is available on Professional and Agency plans.

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
| **Model Server** | vLLM | latest | OpenAI-compatible inference server for dots.ocr (GPU sidecar) |
| **Document AI** | dots.ocr | latest | Vision-language model for unified layout detection + OCR (~100 languages, Cyrillic/Latin) |
| **OCR Client** | openai (Python) | 1.x | OpenAI-compatible client for calling vLLM server |
| **LLM Extraction** | anthropic (Python) | latest | Anthropic Claude API client for structured field extraction from OCR text |
| **LLM Model** | Claude (Haiku/Sonnet) | configurable | Primary field extraction — converts raw OCR text to structured JSON |
| **PDF Processing** | PyMuPDF | 1.24.x | PDF parsing |
| **Image Processing** | Pillow | 10.x | Image manipulation |
| **OpenCV** | opencv-python | 4.9.x | Computer vision |
| **NumPy** | numpy | 1.26.x | Numerical computing |

### 6.4 Database

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| **Primary DB** | PostgreSQL | 16.x | Relational database |
| **Cache** | Redis | 7.x | Caching, sessions |
| **Search** | PostgreSQL FTS | - | Full-text search |

### 6.5 Infrastructure

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Container Runtime** | Docker | Containerization |
| **Orchestration** | Kubernetes | Container orchestration |
| **Cloud Provider** | AWS / Hetzner | Infrastructure |
| **Object Storage** | S3 / Cloudflare R2 | Document storage |
| **CDN** | Cloudflare | Static assets, DDoS protection |
| **SSL** | Let's Encrypt | TLS certificates |
| **DNS** | Cloudflare | DNS management |

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

┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│  audit_logs     │       │  usage_records  │       │    webhooks     │
├─────────────────┤       ├─────────────────┤       ├─────────────────┤
│ id (PK)         │       │ id (PK)         │       │ id (PK)         │
│ organization_id │       │ organization_id │       │ organization_id │
│ user_id (FK)    │       │ period_start    │       │ url             │
│ action          │       │ period_end      │       │ events (JSON)   │
│ entity_type     │       │ invoices_count  │       │ secret          │
│ entity_id       │       │ api_calls_count │       │ is_active       │
│ old_values      │       │ storage_bytes   │       │ created_at      │
│ new_values      │       └─────────────────┘       └─────────────────┘
│ ip_address      │
│ user_agent      │
│ created_at      │
└─────────────────┘
```

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
    payment_provider_customer_id VARCHAR(255),
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_organizations_slug ON organizations(slug);
```

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
```

---

## 8. API Specification

### 8.1 API Overview

**Base URL:** `https://api.fakturaai.rs/v1`

**Authentication:** Bearer token (JWT) or API key

**Content Type:** `application/json`

**Rate Limits:**

| Plan | Requests/minute | Requests/day |
|------|-----------------|--------------|
| Starter | 30 | 1,000 |
| Professional | 100 | 10,000 |
| Enterprise | 500 | Unlimited |

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
  "document_url": "https://storage.fakturaai.rs/docs/...",
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
  "download_url": "https://storage.fakturaai.rs/exports/audit/...",
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

dots.ocr is a vision-language model (VLM) that performs **unified layout detection and text extraction** in a single pass. It runs as a **vLLM HTTP server** (GPU sidecar container), called by a lightweight OCR worker via the OpenAI-compatible chat completions API.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        OCR Processing Pipeline                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────┐    ┌─────────────────────────────────────────────┐  │
│  │   Input     │    │          vLLM Server (GPU sidecar)          │  │
│  │  Document   │    │  ┌───────────────────────────────────────┐  │  │
│  │ (PDF/Image) │    │  │  dots.ocr Vision-Language Model       │  │  │
│  └──────┬──────┘    │  │  (rednote-hilab/dots.ocr, 1.7B)      │  │  │
│         │           │  └───────────────────────────────────────┘  │  │
│         ▼           │  OpenAI-compatible API (:8000/v1)           │  │
│  ┌─────────────┐    └──────────────────────┬──────────────────────┘  │
│  │ OCR Worker  │                           │                         │
│  │ (Celery,    │    HTTP POST              │ Structured              │
│  │  no GPU)    │───▶/v1/chat/completions   │ JSON Output             │
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

**Primary Engine:** dots.ocr (via vLLM server)

dots.ocr is optimized for document understanding and provides superior accuracy on structured documents like invoices, with excellent Cyrillic and Latin script support. It runs as a separate **vLLM HTTP server** (GPU sidecar container) and is called by the OCR worker via the OpenAI-compatible chat completions API.

**Architecture:**
- **dots-ocr-server**: `vllm/vllm-openai:latest` Docker image serving `rednote-hilab/dots.ocr` with `--trust-remote-code --chat-template-content-format string`
- **ocr-worker**: Lightweight Python 3.12 container (no GPU) calling the server via `openai` Python client
- Worker sends base64-encoded images with `<|img|><|imgpad|><|endofimg|>` prompt prefix

**Configuration (environment variables):**
```
DOTS_OCR_SERVER_URL=http://dots-ocr-server:8000/v1
DOTS_OCR_MODEL_NAME=model
OCR_PRIMARY_ENGINE=dots
OCR_FALLBACK_ENGINE=none
```

**Fallback Strategy:** Manual review by user

There is no automated OCR fallback engine. If dots.ocr fails or returns low-confidence results, the invoice is flagged for manual review by the end user. This design decision was made because alternative OCR engines (e.g., EasyOCR) provide insufficient accuracy for Serbian Cyrillic/Latin documents.

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

| Component | GPU Memory | Instances | Notes |
|-----------|------------|-----------|-------|
| dots.ocr vLLM server | 6-8 GB | 1-2 | GPU sidecar running rednote-hilab/dots.ocr (1.7B params) |
| OCR Worker | 0 (CPU only) | 1-2 | Lightweight Celery worker calling vLLM server and Claude API |
| LLM Extraction (Claude) | 0 (API call) | N/A | Anthropic Claude API for structured field extraction from OCR text |

**Note:** dots.ocr replaces the need for separate Layout Parser + OCR Engine, reducing infrastructure complexity. Field extraction is performed by Claude LLM via API call (no local GPU needed). If dots.ocr fails, the invoice is flagged for manual review by the user.

**Model Serving:**
- **vLLM** (`vllm/vllm-openai:latest`) — OpenAI-compatible inference server for dots.ocr
- Server flags: `--trust-remote-code --chat-template-content-format string --gpu-memory-utilization 0.90 --max-model-len 8192`
- HuggingFace model cache persisted via Docker volume (`huggingface_cache`)

**Model Note:** The system uses pre-trained models (dots.ocr for OCR, Claude for field extraction) without additional training on user data. This approach eliminates the need for training data collection, consent management, and complex MLOps infrastructure, while ensuring user privacy protection.

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
| JWT Tokens | RS256 signing, 1-hour expiry |
| Refresh Tokens | Secure HTTP-only cookies, 7-day expiry |
| MFA | TOTP-based 2FA (optional) |
| Session Management | Redis-backed sessions |
| Brute Force Protection | Rate limiting, account lockout |

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
    signed_by_fakturaai VARCHAR(255),
    signed_by_fakturaai_at TIMESTAMP WITH TIME ZONE,
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
<RegistarFaktura xmlns="urn:fakturaai:export:v1">
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
privacy@fakturaai.rs

S poštovanjem,
FakturaAI Tim
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

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Internet                                     │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Cloudflare (CDN + WAF)                         │
│  - DDoS protection                                                   │
│  - SSL termination                                                   │
│  - Static asset caching                                             │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Load Balancer (nginx/HAProxy)                    │
└─────────────┬─────────────────┬─────────────────┬───────────────────┘
              │                 │                 │
              ▼                 ▼                 ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────────────────┐
│   Web App       │ │   API Server    │ │   ML Workers                │
│   (Next.js)     │ │   (FastAPI)     │ │   (Celery + GPU)            │
│   Replicas: 2-4 │ │   Replicas: 2-4 │ │   Replicas: 2-4             │
└─────────────────┘ └────────┬────────┘ └──────────────┬──────────────┘
                             │                         │
              ┌──────────────┴──────────────┬──────────┴──────────┐
              ▼                             ▼                      ▼
┌─────────────────────┐     ┌─────────────────────┐  ┌────────────────┐
│     PostgreSQL      │     │       Redis         │  │   S3/R2        │
│   Primary + Replica │     │  Cluster (3 nodes)  │  │   Storage      │
└─────────────────────┘     └─────────────────────┘  └────────────────┘
```

### 11.2 Kubernetes Deployment

**Namespaces:**
- `fakturaai-prod` - Production workloads
- `fakturaai-staging` - Staging environment
- `fakturaai-monitoring` - Prometheus, Grafana

**Key Resources:**

```yaml
# Web Application Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
  namespace: fakturaai-prod
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web-app
  template:
    spec:
      containers:
      - name: web-app
        image: ghcr.io/fakturaai/web:latest
        resources:
          requests:
            memory: "256Mi"
            cpu: "200m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        ports:
        - containerPort: 3000

---
# ML Worker Deployment (with GPU)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ml-worker
  namespace: fakturaai-prod
spec:
  replicas: 2
  template:
    spec:
      containers:
      - name: ml-worker
        image: ghcr.io/fakturaai/ml-worker:latest
        resources:
          limits:
            nvidia.com/gpu: 1
            memory: "8Gi"
          requests:
            memory: "4Gi"
```

### 11.3 CI/CD Pipeline

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Commit    │───▶│    Build    │───▶│    Test     │───▶│   Deploy    │
│   to main   │    │   & Lint    │    │   Suite     │    │  Staging    │
└─────────────┘    └─────────────┘    └─────────────┘    └──────┬──────┘
                                                                │
                                                                ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Monitor    │◀───│   Deploy    │◀───│   Approve   │◀───│  E2E Tests  │
│  & Alert    │    │    Prod     │    │  (Manual)   │    │  (Staging)  │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

**GitHub Actions Workflow:**

```yaml
name: Deploy
on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build and push Docker images
        run: |
          docker build -t ghcr.io/fakturaai/web:${{ github.sha }} ./web
          docker push ghcr.io/fakturaai/web:${{ github.sha }}

  test:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: Run tests
        run: |
          npm test
          pytest tests/

  deploy-staging:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to staging
        run: kubectl apply -f k8s/staging/

  deploy-prod:
    needs: deploy-staging
    runs-on: ubuntu-latest
    environment: production
    steps:
      - name: Deploy to production
        run: kubectl apply -f k8s/prod/
```

### 11.4 Monitoring Stack

| Component | Tool | Purpose |
|-----------|------|---------|
| Metrics | Prometheus | Time-series metrics |
| Dashboards | Grafana | Visualization |
| Logging | Loki | Log aggregation |
| Tracing | Jaeger | Distributed tracing |
| Alerting | Alertmanager | Alert routing |
| Error Tracking | Sentry | Error monitoring |

**Key Metrics:**
- Request latency (p50, p95, p99)
- Error rate
- OCR processing time
- Queue depth
- GPU utilization
- Database connection pool

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

**Why Paddle:** Paddle operates as a Merchant of Record (MoR), meaning Paddle manages all payment transactions, VAT obligations, and tax compliance globally on behalf of FakturaAI. This is critical for the Serbian market because:
- Paddle assumes responsibility for calculating and collecting VAT in all jurisdictions
- No need for FakturaAI to register for VAT in individual countries
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

### 12.3 Email Service (SendGrid/Resend)

**Transactional Emails:**
- Welcome email
- Email verification
- Password reset
- Invoice processing complete
- Subscription notifications

### 12.4 Storage (Cloudflare R2 / AWS S3)

**Buckets:**
- `fakturaai-documents` - Uploaded invoices
- `fakturaai-exports` - Generated exports
- `fakturaai-backups` - Database backups

**Object Key Convention:**
Documents are namespaced by organization for multi-tenant isolation:
```
organizations/{organization_id}/invoices/{invoice_id}/original.{ext}
```

**Lifecycle Rules:**
- Documents: 10 years retention (per Serbian Accounting Law, Sl. glasnik RS, br. 73/2019)
- Exports: 30 days auto-delete
- Backups: 90 days retention

### 12.5 MiniMax Integration

MiniMax (minimax.rs) is the most widely used cloud accounting software in Serbia. FakturaAI integrates with MiniMax via both XML file export and direct REST API push.

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

### 12.6 SEF Integration (eFaktura)

The Serbian E-Invoice System (Sistem Elektronskih Faktura - SEF) is mandatory for B2G and B2B transactions in Serbia. FakturaAI MUST integrate with SEF as a **first-class input source**, not just an export format.

#### 12.7.1 Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    SEF Integration Architecture                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────┐         ┌─────────────┐         ┌─────────────┐   │
│  │    SEF      │◀───────▶│  FakturaAI  │◀───────▶│  User       │   │
│  │   Portal    │   API   │   Backend   │   Web   │  Interface  │   │
│  │  (eFaktura) │         │             │         │             │   │
│  └─────────────┘         └──────┬──────┘         └─────────────┘   │
│                                 │                                   │
│                    ┌────────────┼────────────┐                      │
│                    ▼            ▼            ▼                      │
│             ┌───────────┐ ┌───────────┐ ┌───────────┐              │
│             │  Inbound  │ │  Outbound │ │  Status   │              │
│             │  Invoices │ │  Invoices │ │  Sync     │              │
│             │  (Pull)   │ │  (Push)   │ │  (Polling)│              │
│             └───────────┘ └───────────┘ └───────────┘              │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

#### 12.6.2 SEF Connection Setup

**Authentication:**

| Method | Description | Use Case |
|--------|-------------|----------|
| API Key | Organization-level SEF API key | Production |
| Certificate | Qualified electronic certificate | High-security organizations |
| OAuth 2.0 | User-delegated access | Multi-tenant scenarios |

**Connection Configuration:**

```json
{
  "sef_connection": {
    "environment": "production",  // "production" | "test"
    "api_base_url": "https://efaktura.mfin.gov.rs/api/v1",
    "organization_pib": "123456789",
    "api_key": "encrypted:xxx",
    "certificate_path": "/secrets/sef-cert.p12",
    "sync_enabled": true,
    "sync_interval_minutes": 15
  }
}
```

**Database Schema:**

```sql
CREATE TABLE sef_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),

    -- Connection settings
    environment VARCHAR(20) NOT NULL DEFAULT 'production',
    api_key_encrypted TEXT,
    certificate_path VARCHAR(500),
    pib VARCHAR(9) NOT NULL,

    -- Sync settings
    sync_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    sync_interval_minutes INTEGER DEFAULT 15,
    last_sync_at TIMESTAMP WITH TIME ZONE,
    last_sync_status VARCHAR(20),
    last_sync_error TEXT,

    -- Statistics
    total_invoices_synced INTEGER DEFAULT 0,
    invoices_synced_today INTEGER DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT unique_sef_per_org UNIQUE (organization_id),
    CONSTRAINT valid_environment CHECK (environment IN ('production', 'test'))
);
```

#### 12.6.3 Inbound Invoice Sync (SEF → FakturaAI)

The system MUST pull invoices from SEF and process them through the FakturaAI pipeline.

**Sync Flow:**

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Inbound Invoice Sync Flow                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  1. Poll SEF API (every 15 minutes)                                 │
│     │                                                                │
│     ▼                                                                │
│  2. Fetch new/updated invoices since last sync                      │
│     GET /api/v1/purchase-invoices?from={last_sync}&status=DELIVERED │
│     │                                                                │
│     ▼                                                                │
│  3. For each invoice:                                               │
│     ┌─────────────────────────────────────────────────────────────┐ │
│     │ a. Check if already exists (by SEF ID)                      │ │
│     │ b. Download XML + PDF attachment                            │ │
│     │ c. Parse UBL/XML structured data                            │ │
│     │ d. Store PDF in document storage                            │ │
│     │ e. Create invoice record with SEF metadata                  │ │
│     │ f. Run OCR on PDF (for additional data/validation)          │ │
│     │ g. Generate AccountingIntent                                │ │
│     │ h. Apply automation rules                                   │ │
│     └─────────────────────────────────────────────────────────────┘ │
│     │                                                                │
│     ▼                                                                │
│  4. Update last_sync_at timestamp                                   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

**SEF Invoice Statuses:**

| SEF Status | Serbian | FakturaAI Action |
|------------|---------|------------------|
| `SENT` | Poslata | N/A (outbound only) |
| `DELIVERED` | Isporučena | Import & process |
| `SEEN` | Viđena | Update status |
| `APPROVED` | Odobrena | Mark as accepted |
| `REJECTED` | Odbijena | Flag for attention |
| `CANCELLED` | Stornirana | Handle cancellation |
| `PAID` | Plaćena | Update payment status |

**SEF Invoice Data Structure (from UBL):**

```json
{
  "sef_invoice": {
    "sef_id": "12345678-1234-1234-1234-123456789012",
    "sef_status": "DELIVERED",
    "invoice_number": "2025-0001",
    "invoice_date": "2025-01-15",
    "due_date": "2025-02-15",

    "seller": {
      "pib": "123456789",
      "name": "Dobavljač d.o.o.",
      "address": "Ulica 1, Beograd",
      "mb": "12345678",
      "jbkjs": null  // For budget users
    },

    "buyer": {
      "pib": "987654321",
      "name": "Kupac d.o.o.",
      "address": "Ulica 2, Novi Sad",
      "mb": "87654321"
    },

    "line_items": [
      {
        "description": "Usluge konsaltinga",
        "quantity": 10,
        "unit": "HUR",  // UN/CEFACT unit code
        "unit_price": 5000.00,
        "discount": null,
        "tax_base": null,
        "total": 50000.00,
        "vat_rate": 20.00,
        "vat_amount": 10000.00
      }
    ],

    "monetary_totals": {
      "line_extension_amount": 50000.00,
      "tax_exclusive_amount": 50000.00,
      "tax_inclusive_amount": 60000.00,
      "payable_amount": 60000.00
    },

    "vat_breakdown": [
      {
        "taxable_amount": 50000.00,
        "tax_amount": 10000.00,
        "tax_category": "S",  // Standard rate
        "percent": 20.00
      }
    ],

    "attachments": [
      {
        "filename": "faktura-2025-0001.pdf",
        "mime_type": "application/pdf",
        "embedded": true  // Base64 in XML or separate download
      }
    ],

    "sef_metadata": {
      "creation_date": "2025-01-15T10:30:00Z",
      "delivery_date": "2025-01-15T10:30:05Z",
      "cir_invoice_id": null,  // Central Invoice Registry ID
      "is_government": false
    }
  }
}
```

**Database Schema - SEF Invoice Mapping:**

```sql
CREATE TABLE sef_invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    invoice_id UUID REFERENCES invoices(id),  -- FakturaAI invoice

    -- SEF identifiers
    sef_id VARCHAR(100) NOT NULL,
    sef_internal_id VARCHAR(100),
    cir_invoice_id VARCHAR(100),

    -- SEF status tracking
    sef_status VARCHAR(30) NOT NULL,
    sef_status_updated_at TIMESTAMP WITH TIME ZONE,

    -- Direction
    direction VARCHAR(10) NOT NULL,  -- 'INBOUND' | 'OUTBOUND'

    -- Raw SEF data
    ubl_xml TEXT,
    sef_response_json JSONB,

    -- PDF attachment
    pdf_document_id UUID REFERENCES documents(id),

    -- Sync metadata
    synced_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE,
    processing_error TEXT,

    -- User actions
    user_accepted BOOLEAN,
    user_accepted_at TIMESTAMP WITH TIME ZONE,
    user_accepted_by UUID REFERENCES users(id),
    rejection_reason TEXT,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT unique_sef_id UNIQUE (organization_id, sef_id),
    CONSTRAINT valid_direction CHECK (direction IN ('INBOUND', 'OUTBOUND')),
    CONSTRAINT valid_sef_status CHECK (sef_status IN (
        'SENT', 'DELIVERED', 'SEEN', 'APPROVED', 'REJECTED',
        'CANCELLED', 'PAID', 'STORNO', 'ERROR'
    ))
);

CREATE INDEX idx_sef_invoices_org ON sef_invoices(organization_id);
CREATE INDEX idx_sef_invoices_status ON sef_invoices(sef_status);
CREATE INDEX idx_sef_invoices_invoice ON sef_invoices(invoice_id);
CREATE INDEX idx_sef_invoices_synced ON sef_invoices(synced_at);
```

#### 12.6.4 Outbound Invoice Push (FakturaAI → SEF)

The system SHOULD support sending invoices to SEF (for organizations that issue invoices).

**Push Flow:**

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Outbound Invoice Push Flow                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  1. User creates/uploads outbound invoice in FakturaAI              │
│     │                                                                │
│     ▼                                                                │
│  2. System validates:                                               │
│     • All required UBL fields present                               │
│     • Buyer PIB valid in APR                                        │
│     • Mathematical accuracy                                         │
│     • VAT calculation correct                                       │
│     │                                                                │
│     ▼                                                                │
│  3. Generate UBL 2.1 XML                                            │
│     │                                                                │
│     ▼                                                                │
│  4. User clicks "Pošalji na SEF"                                    │
│     │                                                                │
│     ▼                                                                │
│  5. POST to SEF API                                                 │
│     │                                                                │
│     ├──▶ Success: Store SEF ID, update status                       │
│     │                                                                │
│     └──▶ Error: Log error, notify user, allow retry                 │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

**UBL Generation Requirements:**

| UBL Field | Source | Validation |
|-----------|--------|------------|
| `ID` | invoice.invoice_number | Required |
| `IssueDate` | invoice.invoice_date | Required, format YYYY-MM-DD |
| `DueDate` | invoice.due_date | Required |
| `InvoiceTypeCode` | accounting_intent.document_type | 380 = Invoice, 381 = Credit Note |
| `DocumentCurrencyCode` | invoice.currency | Must be RSD for domestic |
| `AccountingSupplierParty` | seller.* | PIB, name, address required |
| `AccountingCustomerParty` | buyer.* | PIB, name, address required |
| `TaxTotal` | Calculated | VAT breakdown per rate |
| `LegalMonetaryTotal` | invoice.* | All totals |
| `InvoiceLine` | line_items[] | Description, quantity, price, VAT |

#### 12.6.5 SEF Status Polling

SEF does not support native webhooks. The system MUST poll the SEF API to detect invoice status changes.

**Polling Strategy:**

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Default interval | 15 minutes | Balance between timeliness and API limits |
| Business hours boost | 5 minutes (8:00-17:00) | Faster updates during work hours |
| Off-hours interval | 30 minutes | Reduce unnecessary API calls |
| Rate limit | Max 100 requests/hour per org | Respect SEF API limits |

**Polling Implementation:**

```python
async def poll_sef_status_changes(org_id: UUID):
    """
    Poll SEF API for invoice status changes.
    Runs on scheduled interval per organization.
    """
    connection = await get_sef_connection(org_id)
    if not connection or not connection.sync_enabled:
        return

    # 1. Get last sync timestamp
    last_sync = connection.last_sync_at or datetime.min

    # 2. Query SEF for status changes since last sync
    changed_invoices = await sef_client.get_status_changes(
        pib=connection.organization_pib,
        since=last_sync,
        api_key=decrypt(connection.api_key_encrypted)
    )

    # 3. Process each status change
    for change in changed_invoices:
        sef_invoice = await get_sef_invoice(org_id, change.sef_id)
        if not sef_invoice:
            logger.warning(f"Unknown SEF invoice: {change.sef_id}")
            continue

        old_status = sef_invoice.sef_status
        if old_status == change.new_status:
            continue  # No actual change

        sef_invoice.sef_status = change.new_status
        sef_invoice.sef_status_updated_at = change.timestamp

        # 4. Handle specific status transitions
        match change.new_status:
            case "APPROVED":
                await mark_invoice_accepted(sef_invoice.invoice_id)
                await notify_user(sef_invoice, "Faktura odobrena od strane kupca")
            case "REJECTED":
                await flag_invoice_for_review(
                    sef_invoice.invoice_id,
                    reason=f"Odbijena na SEF: {change.rejection_reason}"
                )
                await notify_user(sef_invoice, "Faktura odbijena!", priority="high")
            case "CANCELLED":
                if sef_invoice.invoice.status == "exported":
                    await create_cancellation_record(sef_invoice.invoice_id)
            case "PAID":
                await update_payment_status(sef_invoice.invoice_id, paid=True)

        await log_sef_status_change(sef_invoice, old_status, change)

    # 5. Update last sync timestamp
    connection.last_sync_at = datetime.now(timezone.utc)
    await db.save(connection)
```

#### 12.6.6 SEF-OCR Hybrid Processing

When receiving invoices from SEF, the system uses both structured UBL data AND OCR for maximum accuracy:

```
┌─────────────────────────────────────────────────────────────────────┐
│                   SEF-OCR Hybrid Processing                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    SEF UBL/XML Data                          │   │
│  │  • Structured, machine-readable                              │   │
│  │  • Seller/Buyer PIB guaranteed accurate                      │   │
│  │  • Amounts from issuer's system                              │   │
│  │  • Line items may be summarized                              │   │
│  └──────────────────────────────┬───────────────────────────────┘   │
│                                 │                                    │
│                                 ▼                                    │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    Merge Strategy                            │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                 │                                    │
│  ┌──────────────────────────────┴───────────────────────────────┐   │
│  │                   PDF/OCR Data                               │   │
│  │  • Visual representation                                     │   │
│  │  • May have more detailed line items                         │   │
│  │  • Additional notes/terms                                    │   │
│  │  • Signatures, stamps (visual verification)                  │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  Merge Rules:                                                       │
│  ─────────────────────────────────────────────────────────────────  │
│  • PIB, MB: Always use SEF (authoritative)                         │
│  • Amounts: Use SEF, flag if OCR differs by > 1%                   │
│  • Invoice number: Use SEF                                         │
│  • Line items: Merge - prefer SEF structure, OCR for detail        │
│  • Payment terms: OCR may have more detail                         │
│  • Attachments: Store PDF from SEF                                 │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

**Discrepancy Handling:**

| Field | SEF Value | OCR Value | Action |
|-------|-----------|-----------|--------|
| total_amount | 60000.00 | 60000.00 | ✅ Match - proceed |
| total_amount | 60000.00 | 59999.50 | ✅ Within tolerance (0.01%) |
| total_amount | 60000.00 | 58000.00 | ⚠️ Flag for review (>1% diff) |
| line_items | 3 items | 5 items | ⚠️ OCR found more detail - review |
| seller_pib | 123456789 | 123456780 | ✅ Use SEF (authoritative) |

#### 12.6.7 SEF Inbox UI

The system MUST provide a dedicated "SEF Inbox" view for managing incoming eFaktura invoices:

```
┌─────────────────────────────────────────────────────────────────────┐
│  📥 SEF Inbox                                            [↻ Sync]   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Filter: [Sve ▼] [Ovaj mesec ▼]           Search: [____________]   │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │ ☐ │ Status    │ Dobavljač           │ Br. fakture │ Iznos    │ ││
│  ├───┼───────────┼─────────────────────┼─────────────┼──────────┤ ││
│  │ ☑ │ 🆕 Nova    │ Telekom Srbija     │ 2025-001234 │ 4.500 RSD│ ││
│  │ ☐ │ 🆕 Nova    │ EPS Snabdevanje    │ 01-25-98765 │ 12.340 RSD││
│  │ ☐ │ ⏳ Na čekanju│ Dobavljač XYZ    │ F-2025-042  │ 156.000 RSD││
│  │ ☐ │ ✅ Obrađeno │ Partner ABC       │ 2025/0015   │ 45.000 RSD││
│  │ ☐ │ ❌ Odbijeno │ Nepoznat d.o.o.   │ INV-999     │ 8.000 RSD ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                      │
│  Izabrano: 1                     [Obradi izabrane] [Odbij] [Arhiviraj]│
│                                                                      │
│  Poslednja sinhronizacija: pre 5 minuta                             │
│  Neobrađenih faktura: 2                                             │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

**SEF Invoice Actions:**

| Action | Description | Result |
|--------|-------------|--------|
| Obradi | Process through FakturaAI pipeline | Creates invoice + accounting intent |
| Prihvati na SEF | Send acceptance to SEF | Updates SEF status to APPROVED |
| Odbij | Reject invoice | Sends rejection to SEF with reason |
| Arhiviraj | Archive without processing | Stores but doesn't create invoice |

#### 12.6.8 SEF Error Handling

| Error | Cause | Recovery |
|-------|-------|----------|
| `SEF_CONNECTION_FAILED` | Network/API issues | Retry with exponential backoff |
| `SEF_AUTH_EXPIRED` | API key/cert expired | Notify admin, disable sync |
| `SEF_RATE_LIMITED` | Too many requests | Back off, reduce sync frequency |
| `SEF_INVALID_RESPONSE` | Unexpected data format | Log, skip invoice, alert |
| `SEF_DUPLICATE_INVOICE` | Already processed | Skip, update status only |
| `UBL_PARSE_ERROR` | Malformed XML | Log, attempt PDF-only processing |

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
| Landing Page | Marketing page with features, pricing |
| Login/Register | Authentication screens |
| Dashboard | Overview, stats, quick actions |
| Upload | Drag & drop upload interface |
| Processing | Real-time processing status |
| Invoice View | Side-by-side document and data |
| Invoice List | Filterable, sortable table |
| Export | Format selection, field mapping |
| Clients | Client list, create/edit client (Agency plan only) |
| Settings | Profile, team, API keys |
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
| 1.0 | January 2025 | FakturaAI Team | Initial release |
| 1.1 | January 2025 | FakturaAI Team | Added: Business Logic & Validation Rules (4.9), Human-in-the-Loop & Feedback System (9.9), Legal & Compliance Flows (10.6) |
| 1.2 | January 2025 | FakturaAI Team | Added: Accounting Intent Layer (4.10), Automation Rules Engine (4.11), SEF Integration (12.5), Expanded Feedback Loop Implementation (9.9.7) |
| 1.3 | January 2025 | FakturaAI Team | Updated OCR stack: dots.ocr (VLM) as primary engine with unified layout+OCR, EasyOCR as fallback, removed separate LayoutParser (Tesseract removed) |
| 2.0 | February 2026 | FakturaAI Team | Serbian market alignment: removed model training/retraining (pre-trained models only), ZZPL as primary data protection law (GDPR as reference), Paddle instead of Stripe, KPR/KIR terminology, SEF polling instead of webhooks, NBS exchange rate integration, Cyrillic/Latin script support, PIB constraint for foreign entities, 10-year document retention |
| 2.1 | February 2026 | FakturaAI Team | dots.ocr architecture: vLLM HTTP server sidecar (GPU) + lightweight OCR worker (CPU, OpenAI client), removed EasyOCR fallback (manual review instead), skip preprocessing for VLM |
| 2.2 | February 2026 | FakturaAI Team | LLM-based field extraction (Anthropic Claude) as primary method with regex fallback. Added `tax_groups` for multi-rate PDV breakdowns (per-section, not merged). Updated data model: inline JSON columns for seller/buyer/line_items/tax_groups (removed companies/documents FK tables). Added `raw_llm_output` for debugging. Per-field confidence scoring with `needs_review` flag. Enhanced math validation: tax groups consistency check, tax amount not recomputed from rate. Updated invoice detail UI: EditableField with confidence badges, line items editing, tax groups editing, field-level validation warnings, Toast feedback. |
| 2.3 | March 2026 | FakturaAI Team | Added fiscal receipt PIB extraction rules (4.9.2a): buyer ID type-code prefix handling, store/branch number disambiguation, post-extraction sanitization. Added multi-country tax ID validation spec (4.9.2b): OIB (Croatia), JIB (BiH), Montenegro PIB, EDB (North Macedonia), Slovenian Davčna, EU VAT IDs. Updated glossary with OIB and JIB terms. |
| 2.4 | March 2026 | FakturaAI Team | Added Invoice Template Learning & LLM Cost Optimization spec (9.9): layout fingerprinting, template storage model, template-based field extraction with three-tier fallback chain, automatic template learning from LLM extractions, cost tracking metrics. |
| 2.5 | March 2026 | FakturaAI Team | Added Client Management for Agency plan (4.12): client CRUD with soft-delete, auto-assignment of invoices to clients via PIB matching after OCR, invoice scoping by client_id, sidebar client selector. Added clients table (7.2.4), client_id FK on invoices. Feature gated via CLIENT_MANAGEMENT flag. |
| 2.6 | March 2026 | Saldora Team | Replaced PDV book generation (KPR/KIR, M13) with Invoice Reports feature (4.13): denormalized invoice_line_items table populated at OCR completion and on edits; five pre-built report templates (received goods, spending by supplier, monthly breakdown, price comparison, expense summary) at /api/v1/reports/; zero LLM cost; CSV export; frontend page at /{orgSlug}/izvestaji; PRO plan feature gate. |
| 2.7 | March 2026 | Saldora Team | Added line item discount/tax_base fields. Added invoice_line_items to DB schema (7.2.5). Updated duplicate detection to hard block (4.4.3). Added Email Ingestion Pipeline spec (4.14): dedicated inbound address per org, attachment extraction, auto-processing, Postmark webhook, security controls, confirmation emails. Rebranded FakturaAI → Saldora. |

---

**End of Document**
