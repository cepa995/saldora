# Software Requirements Specification (SRS)
# FakturaAI - AI-Powered Invoice Processing Platform

**Version:** 1.0
**Date:** January 2025
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

This Software Requirements Specification (SRS) document provides a comprehensive description of the FakturaAI platform - an AI-powered invoice processing system designed specifically for the Serbian market. The document outlines functional and non-functional requirements, system architecture, and technical specifications.

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
| KPO | Knjiga Primljenih Obračuna (Received Invoice Book) |
| KIO | Knjiga Izdatih Obračuna (Issued Invoice Book) |
| GDPR | General Data Protection Regulation |
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
│  │  APR API    │  │   Storage   │  │    Payment Gateway      │  │
│  │  (Serbia)   │  │   (S3/R2)   │  │    (Stripe)             │  │
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
- Manages multiple clients
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

1. Must comply with Serbian data protection laws and GDPR
2. All data must be stored within EU jurisdiction
3. Must support both Cyrillic and Latin character sets
4. Response time for OCR processing must not exceed 10 seconds per page
5. System must handle concurrent processing of up to 100 documents

### 2.6 Assumptions and Dependencies

**Assumptions:**
- Users have stable internet connection
- Invoice documents are legible (not severely damaged or blurred)
- APR API remains available and maintains current data format

**Dependencies:**
- APR public API for PIB verification
- Cloud storage provider (AWS S3 or Cloudflare R2)
- Payment processor (Stripe) availability in Serbia

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
│  │ PyTorch Models │  │ │  │ PostgreSQL │  │ │  │   S3/R2        │  │
│  │ - dots.ocr VLM │  │ │  │            │  │ │  │   Compatible   │  │
│  │ - NER Model    │  │ │  └────────────┘  │ │  └────────────────┘  │
│  │ - EasyOCR (fb) │  │ │  ┌────────────┐  │ └──────────────────────┘
│  └────────────────┘  │ │  │   Redis    │  │
│  ┌────────────────┐  │ │  │  (Cache)   │  │
│  │  Celery        │  │ │  └────────────┘  │
│  │  (Task Queue)  │  │ └──────────────────┘
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
│  │  - Stripe int.  │    │ - Celery tasks  │    │  - Notifications│  │
│  │  - Usage track  │    │ - Job status    │    │  - Callbacks    │  │
│  │  - Invoicing    │    │ - Retry logic   │    │  - Events       │  │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.3 Data Flow Diagram

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  User    │     │  Upload  │     │   OCR    │     │ Extract  │
│  Uploads │────▶│  Service │────▶│  Engine  │────▶│  Fields  │
│  Invoice │     │          │     │          │     │          │
└──────────┘     └──────────┘     └──────────┘     └──────────┘
                                                         │
                                                         ▼
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  Export  │     │  User    │     │   PIB    │     │  NER     │
│  Data    │◀────│  Review  │◀────│  Verify  │◀────│  Model   │
│          │     │  & Edit  │     │  (APR)   │     │          │
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

**Required Fields:**

| Field | Description | Validation |
|-------|-------------|------------|
| invoice_number | Unique invoice identifier | Alphanumeric |
| invoice_date | Date of invoice issue | Valid date format |
| due_date | Payment due date | Valid date, >= invoice_date |
| seller_name | Seller company name | Non-empty string |
| seller_pib | Seller tax ID (PIB) | 9 digits |
| seller_address | Seller address | Non-empty string |
| buyer_name | Buyer company name | Non-empty string |
| buyer_pib | Buyer tax ID (PIB) | 9 digits |
| buyer_address | Buyer address | Non-empty string |
| subtotal | Amount before tax | Decimal number |
| tax_rate | VAT rate applied | 0%, 10%, or 20% |
| tax_amount | Calculated tax | Decimal number |
| total_amount | Total including tax | Decimal number |
| currency | Currency code | RSD, EUR, USD |
| line_items | Individual items/services | Array of items |

**Line Item Fields:**

| Field | Description |
|-------|-------------|
| description | Item/service description |
| quantity | Number of units |
| unit_price | Price per unit |
| total | Line total |

#### FR-4.3.3 Confidence Scoring
| ID | FR-4.3.3 |
|----|----------|
| **Description** | System MUST provide confidence scores for extracted fields |
| **Scale** | 0-100% confidence |
| **Threshold** | Fields below 80% confidence flagged for manual review |
| **Display** | Visual indication (color coding) of confidence levels |

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
| **Checks** | Subtotal + Tax = Total, Line items sum = Subtotal |
| **Tolerance** | Allow 0.01 RSD rounding difference |

#### FR-4.4.3 Duplicate Detection
| ID | FR-4.4.3 |
|----|----------|
| **Description** | System SHOULD detect duplicate invoices |
| **Criteria** | Same invoice number + seller PIB + date |
| **Action** | Warning prompt, option to skip or process anyway |

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
| **Validation** | Real-time validation on edit |
| **History** | Track changes with timestamps |

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
| **Retention** | Minimum 12 months |

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

#### 4.9.3 VAT Rate Validation

| Extracted Rate | Valid Rates | Action |
|----------------|-------------|--------|
| 0%, 10%, 20% | Standard Serbian rates | ✅ Auto-approve |
| Other value (e.g., 17%, 25%) | Invalid for Serbia | ⚠️ Flag for review |
| Missing/unclear | N/A | ⚠️ Flag for review, suggest 20% |

**Multi-Rate Invoice Handling:**
```
VALIDATE_VAT_RATES(line_items):
  valid_rates = [0, 10, 20]

  FOR EACH item IN line_items:
    IF item.tax_rate NOT IN valid_rates:
      FLAG_FOR_REVIEW(f"Nepoznata stopa PDV: {item.tax_rate}%")

  # Calculate expected totals per rate
  totals_by_rate = GROUP_BY(line_items, tax_rate)
  FOR rate, items IN totals_by_rate:
    expected_tax = SUM(items.subtotal) * rate / 100
    IF ABS(expected_tax - items.tax_amount) > TOLERANCE:
      FLAG_FOR_REVIEW("Neslaganje u obračunu PDV-a")
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

  # Check 2: Tax calculation
  expected_tax = invoice.subtotal * invoice.tax_rate / 100
  IF ABS(expected_tax - invoice.tax_amount) > TOLERANCE:
    FLAG("Obračun PDV-a nije tačan")

  # Check 3: Total = Subtotal + Tax
  expected_total = invoice.subtotal + invoice.tax_amount
  IF ABS(expected_total - invoice.total_amount) > TOLERANCE:
    FLAG("Zbir nije tačan")

  # Check 4: Line item math
  FOR EACH item IN line_items:
    expected = item.quantity * item.unit_price
    IF ABS(expected - item.total) > 1:  # 1 RSD tolerance per line
      FLAG(f"Greška u stavci: {item.description}")
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

**KPO (Knjiga Primljenih Obračuna) - Received Invoices:**

| KPO Field | Source | Calculation |
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

**KIO (Knjiga Izdatih Obračuna) - Issued Invoices:**

| KIO Field | Source |
|-----------|--------|
| Redni broj | Auto-increment |
| Datum fakture | invoice.invoice_date |
| Broj fakture | invoice.invoice_number |
| PIB kupca | buyer.pib |
| Naziv kupca | buyer.name |
| (Same VAT fields as KPO) | |

**PDV-PP Mapping:**

```json
{
  "pdv_book_entries": {
    "book_type": "KPO",
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
| **GDPR** | Full compliance with EU data protection |
| **Data Residency** | All data stored within EU |
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
| **Framework** | PyTorch | 2.2.x | Deep learning framework |
| **Document AI** | dots.ocr | latest | Vision-language model for unified layout detection + OCR (~100 languages, Cyrillic/Latin) |
| **OCR Backup** | EasyOCR | 1.7.x | Fallback OCR when dots.ocr confidence is low |
| **NER** | spaCy | 3.7.x | Named entity recognition (supplementary field extraction) |
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

┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│    invoices     │       │   line_items    │       │   companies     │
├─────────────────┤       ├─────────────────┤       ├─────────────────┤
│ id (PK)         │───────│ id (PK)         │       │ id (PK)         │
│ organization_id │       │ invoice_id (FK) │       │ pib             │
│ user_id (FK)    │       │ description     │       │ name            │
│ document_id(FK) │       │ quantity        │       │ address         │
│ status          │       │ unit_price      │       │ status          │
│ invoice_number  │       │ total           │       │ apr_data (JSON) │
│ invoice_date    │       │ position        │       │ last_verified   │
│ due_date        │       └─────────────────┘       └─────────────────┘
│ seller_id (FK)  │───────────────────────────────────────────┘
│ buyer_id (FK)   │───────────────────────────────────────────┘
│ subtotal        │
│ tax_rate        │       ┌─────────────────┐       ┌─────────────────┐
│ tax_amount      │       │    documents    │       │  api_keys       │
│ total_amount    │       ├─────────────────┤       ├─────────────────┤
│ currency        │       │ id (PK)         │       │ id (PK)         │
│ confidence      │       │ organization_id │       │ organization_id │
│ raw_data (JSON) │       │ original_name   │       │ user_id (FK)    │
│ created_at      │       │ storage_path    │       │ key_hash        │
│ updated_at      │       │ mime_type       │       │ name            │
└─────────────────┘       │ size_bytes      │       │ permissions     │
                          │ page_count      │       │ last_used       │
                          │ created_at      │       │ expires_at      │
                          └─────────────────┘       └─────────────────┘

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
    stripe_customer_id VARCHAR(255),
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_organizations_slug ON organizations(slug);
```

#### 7.2.3 invoices
```sql
CREATE TABLE invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    user_id UUID NOT NULL REFERENCES users(id),
    document_id UUID REFERENCES documents(id),

    status VARCHAR(20) NOT NULL DEFAULT 'processing',

    invoice_number VARCHAR(100),
    invoice_date DATE,
    due_date DATE,

    seller_id UUID REFERENCES companies(id),
    buyer_id UUID REFERENCES companies(id),

    subtotal DECIMAL(15, 2),
    tax_rate DECIMAL(5, 2),
    tax_amount DECIMAL(15, 2),
    total_amount DECIMAL(15, 2),
    currency VARCHAR(3) DEFAULT 'RSD',

    confidence_score DECIMAL(5, 2),
    raw_ocr_data JSONB,
    extracted_data JSONB,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT valid_status CHECK (status IN ('processing', 'review', 'verified', 'exported', 'error'))
);

CREATE INDEX idx_invoices_organization ON invoices(organization_id);
CREATE INDEX idx_invoices_status ON invoices(status);
CREATE INDEX idx_invoices_date ON invoices(invoice_date);
CREATE INDEX idx_invoices_seller ON invoices(seller_id);
CREATE INDEX idx_invoices_buyer ON invoices(buyer_id);
```

#### 7.2.4 companies
```sql
CREATE TABLE companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pib VARCHAR(9) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    address TEXT,
    city VARCHAR(100),
    postal_code VARCHAR(10),
    status VARCHAR(20),
    apr_data JSONB,
    last_verified_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_companies_pib ON companies(pib);
CREATE INDEX idx_companies_name ON companies USING gin(to_tsvector('simple', name));
```

#### 7.2.5 documents
```sql
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    original_filename VARCHAR(255) NOT NULL,
    storage_path VARCHAR(500) NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    size_bytes BIGINT NOT NULL,
    page_count INTEGER DEFAULT 1,
    checksum VARCHAR(64),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_documents_organization ON documents(organization_id);
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
    "name": "Firma ABC d.o.o.",
    "address": "Bulevar Kralja Aleksandra 1, Beograd",
    "verified": true
  },
  "buyer": {
    "pib": "987654321",
    "name": "Kompanija XYZ d.o.o.",
    "address": "Cara Dušana 15, Novi Sad",
    "verified": true
  },
  "line_items": [
    {
      "description": "Usluge konsaltinga",
      "quantity": 10,
      "unit_price": 5000.00,
      "total": 50000.00
    }
  ],
  "subtotal": 50000.00,
  "tax_rate": 20.00,
  "tax_amount": 10000.00,
  "total_amount": 60000.00,
  "currency": "RSD",
  "document_url": "https://storage.fakturaai.rs/docs/...",
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
Update invoice data.

**Request:**
```json
{
  "invoice_number": "2025-00042-A",
  "total_amount": 61000.00
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
```json
{
  "download_url": "https://storage.fakturaai.rs/exports/...",
  "expires_at": "2025-01-15T11:30:00Z",
  "file_size": 15420
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

dots.ocr is a vision-language model (VLM) that performs **unified layout detection and text extraction** in a single pass. This significantly simplifies the pipeline compared to traditional multi-stage approaches.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        OCR Processing Pipeline                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────────┐  │
│  │   Input     │    │   Image     │    │       dots.ocr          │  │
│  │  Document   │───▶│ Preprocessing│───▶│   (Vision-Language     │  │
│  │ (PDF/Image) │    │             │    │        Model)           │  │
│  └─────────────┘    └─────────────┘    └───────────┬─────────────┘  │
│                                                     │                │
│                                                     │ Structured     │
│                                                     │ JSON Output    │
│                                                     │ (layout +      │
│                                                     │  text + bbox)  │
│                           ┌─────────────────────────┘                │
│                           ▼                                          │
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
│  │              Field Extraction & NER (Optional)               │    │
│  │           (Pattern matching + spaCy for edge cases)          │    │
│  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────────┐ │    │
│  │  │ PIB  │ │ Date │ │Amount│ │ Name │ │Address│ │ Inv. No. │ │    │
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
│  │      If dots.ocr confidence < threshold → EasyOCR fallback   │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

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

**Primary Engine:** dots.ocr

dots.ocr is optimized for document understanding and provides superior accuracy on structured documents like invoices, with excellent Cyrillic and Latin script support.

**Configuration:**
```python
DOTS_OCR_CONFIG = {
    "model": "dots.ocr",
    "languages": ["sr_cyrl", "sr_latn", "en"],
    "gpu": True,
    "model_storage_directory": "/models/dots",
    "document_type": "invoice",
    "output_format": "structured",
    "confidence_threshold": 0.7,
}
```

**Fallback Engine:** EasyOCR

EasyOCR is used as a fallback when dots.ocr confidence is below threshold or when processing fails. It provides good Cyrillic support and is well-tested.

```python
EASYOCR_CONFIG = {
    "languages": ["sr_cyrl", "sr_latn", "en"],
    "gpu": True,
    "model_storage_directory": "/models/easyocr",
    "download_enabled": False,
    "detector": True,
    "recognizer": True,
    "batch_size": 16,
    "text_threshold": 0.7,
}
```

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

### 9.5 Named Entity Recognition

**Model:** Custom spaCy NER model trained on Serbian invoices

**Entity Types:**

| Entity | Pattern Examples | Validation |
|--------|------------------|------------|
| PIB | `PIB: 123456789`, `ПИБ: 123456789` | 9-digit number |
| MB | `МБ: 12345678`, `MB: 12345678` | 8-digit number |
| DATE | `15.01.2025`, `15/01/2025` | Valid date |
| AMOUNT | `45.000,00 RSD`, `45000.00` | Decimal number |
| INVOICE_NUM | `Faktura br: 2025-042` | Alphanumeric |
| COMPANY | `Firma ABC d.o.o.` | Company name |
| ADDRESS | `Bulevar Kralja Aleksandra 1` | Address string |
| TAX_RATE | `PDV 20%`, `ПДВ 20%` | 0%, 10%, 20% |

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

### 9.7 Model Training & Updates

**Training Data Requirements:**
- Minimum 10,000 annotated invoice images
- Mix of Cyrillic and Latin documents
- Various invoice formats and layouts
- Quality annotations with bounding boxes

**Model Update Process:**
1. Collect anonymized documents with user consent
2. Annotate using Label Studio
3. Train/fine-tune models weekly
4. A/B test new models
5. Gradual rollout with monitoring

### 9.8 ML Infrastructure

**GPU Requirements:**

| Component | GPU Memory | Instances | Notes |
|-----------|------------|-----------|-------|
| dots.ocr (VLM) | 4-6 GB | 2-4 | Unified layout + OCR, 1.7B params |
| EasyOCR (fallback) | 2 GB | 1-2 | Only used when dots.ocr confidence is low |
| NER Model (optional) | 2 GB | 1-2 | For supplementary field extraction |

**Note:** dots.ocr replaces the need for separate Layout Parser + OCR Engine, reducing infrastructure complexity.

**Model Serving:**
- TorchServe for PyTorch models
- Triton Inference Server (optional)
- Model versioning with MLflow

### 9.9 Human-in-the-Loop & Feedback System

This section defines the feedback loop between human corrections and model improvement.

#### 9.9.1 Correction Tracking

**Every human correction MUST be logged:**

```python
class CorrectionLog:
    """
    Tracks every field correction made by users.
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
    document_region: dict     # Bounding box of the field in document
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
    document_region JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_corrections_field ON correction_logs(field_name);
CREATE INDEX idx_corrections_date ON correction_logs(created_at);
```

#### 9.9.2 Disagreement Tracking & Analysis

**Model vs Human Disagreement Metrics:**

| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| Field Error Rate | % of invoices requiring correction per field | > 15% |
| High Confidence Errors | Corrections where model confidence > 90% | > 5% |
| Repeat Errors | Same error pattern across documents | > 10 occurrences |
| User Override Rate | % flagged items users override vs confirm | < 50% flags correct |

**Disagreement Analysis Dashboard:**
```
┌─────────────────────────────────────────────────────────────────────┐
│                    Model Performance Dashboard                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Field Accuracy (Last 30 Days)                                      │
│  ───────────────────────────────────────────────────────────────    │
│  seller_pib     ████████████████████████████████████░░░░  92.3%    │
│  buyer_pib      █████████████████████████████████░░░░░░░  88.1%    │
│  total_amount   ████████████████████████████████████████  97.5%    │
│  invoice_date   ██████████████████████████████████████░░  95.2%    │
│  line_items     ████████████████████████████░░░░░░░░░░░░  78.4% ⚠️ │
│                                                                      │
│  High Confidence Errors (model said >90%, user corrected)          │
│  ───────────────────────────────────────────────────────────────    │
│  • buyer_pib: 23 errors (pattern: last digit OCR confusion 6↔8)    │
│  • invoice_number: 18 errors (pattern: prefix "BR" vs "Br")        │
│                                                                      │
│  Recommended Actions:                                               │
│  • [Retrain] buyer_pib NER with 23 new samples                     │
│  • [Adjust] invoice_number pattern matching rules                   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

#### 9.9.3 Feedback Loop for Model Retraining

**Training Data Pipeline:**

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   User      │    │  Anonymize  │    │   Queue     │    │  Training   │
│ Corrections │───▶│   & Filter  │───▶│   Dataset   │───▶│   Pipeline  │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
                          │                                      │
                          ▼                                      ▼
                   ┌─────────────┐                       ┌─────────────┐
                   │  Require    │                       │  A/B Test   │
                   │  Consent    │                       │  New Model  │
                   └─────────────┘                       └─────────────┘
```

**Retraining Triggers:**
1. **Threshold-based**: When field error rate exceeds 10% over 7 days
2. **Volume-based**: Accumulated 1,000+ new corrections
3. **Scheduled**: Weekly incremental training
4. **Manual**: Admin-triggered for specific issues

**Training Data Requirements:**
```python
def prepare_training_sample(correction: CorrectionLog) -> TrainingSample | None:
    """
    Convert user correction to training data.
    """
    # Only use if user consented to training
    if not correction.invoice.organization.training_consent:
        return None

    # Anonymize sensitive data
    anonymized_doc = anonymize_document(correction.invoice.document)

    # Create training sample
    return TrainingSample(
        document_image=anonymized_doc,
        field_name=correction.field_name,
        bounding_box=correction.document_region,
        label=correction.corrected_value,
        original_prediction=correction.original_value,
        error_type=correction.correction_type
    )
```

#### 9.9.4 Model Version Management

**Version Tracking:**
```sql
CREATE TABLE model_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_type VARCHAR(50) NOT NULL,  -- "ocr", "ner", "layout"
    version VARCHAR(20) NOT NULL,
    trained_at TIMESTAMP WITH TIME ZONE,
    training_samples_count INTEGER,
    validation_accuracy DECIMAL(5, 2),
    is_active BOOLEAN DEFAULT FALSE,
    rollback_version_id UUID REFERENCES model_versions(id),
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**A/B Testing New Models:**
```python
class ModelABTest:
    """
    Gradual rollout of new model versions.
    """
    control_model: str      # Current production model
    treatment_model: str    # New candidate model
    traffic_split: float    # 0.1 = 10% traffic to treatment
    metrics_to_track: List[str]  # ["accuracy", "latency", "user_corrections"]
    min_sample_size: int    # Minimum invoices before evaluation
    success_threshold: float  # Treatment must be X% better to win

# Rollout stages
ROLLOUT_STAGES = [
    {"traffic": 0.05, "duration": "2 days", "metric": "no_regressions"},
    {"traffic": 0.20, "duration": "3 days", "metric": "5%_improvement"},
    {"traffic": 0.50, "duration": "5 days", "metric": "stable"},
    {"traffic": 1.00, "duration": "permanent", "metric": "confirmed_winner"}
]
```

#### 9.9.5 Confidence Threshold Calibration

**Dynamic Threshold Adjustment:**

The system SHOULD automatically adjust confidence thresholds based on actual accuracy:

```python
def calibrate_thresholds(field_name: str, lookback_days: int = 30):
    """
    Adjust confidence thresholds based on real correction rates.

    Goal: Minimize both false positives (unnecessary reviews) and
    false negatives (errors that slip through).
    """
    corrections = get_corrections(field_name, days=lookback_days)

    # Group by confidence bucket
    buckets = {
        "90-100": corrections.filter(confidence >= 0.90),
        "80-90": corrections.filter(confidence >= 0.80),
        "70-80": corrections.filter(confidence >= 0.70),
        "60-70": corrections.filter(confidence >= 0.60),
    }

    # Calculate error rate per bucket
    for bucket, items in buckets.items():
        error_rate = items.corrected_count / items.total_count
        if error_rate > 0.05:  # More than 5% errors in this bucket
            RECOMMEND_LOWER_THRESHOLD(field_name, bucket)
        if error_rate < 0.01:  # Less than 1% errors
            RECOMMEND_HIGHER_THRESHOLD(field_name, bucket)

    return ThresholdRecommendation(
        field=field_name,
        current_threshold=get_current_threshold(field_name),
        recommended_threshold=calculate_optimal_threshold(corrections),
        expected_review_reduction=estimate_reduction()
    )
```

#### 9.9.6 User Feedback Integration

**Explicit Feedback Mechanisms:**

| Feedback Type | UI Element | Usage |
|---------------|------------|-------|
| Confirm correct | ✓ button on field | Positive training signal |
| Mark as incorrect | ✗ button on field | Triggers correction flow |
| Report pattern | "Prijavi problem" link | Escalates to ML team |
| Rate extraction | 1-5 stars after export | Overall quality metric |

**Implicit Feedback Signals:**
- Time spent on review screen (longer = more issues)
- Number of fields edited per invoice
- User immediately re-uploads same document (OCR failure)
- User abandons processing mid-way

#### 9.9.7 Complete Feedback Loop Implementation

This section provides a detailed, step-by-step explanation of how the feedback loop works from user correction to model improvement.

**End-to-End Flow Diagram:**

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                         COMPLETE FEEDBACK LOOP ARCHITECTURE                          │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  PHASE 1: DATA COLLECTION (Real-time)                                               │
│  ════════════════════════════════════                                               │
│                                                                                      │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐  │
│  │ User views  │───▶│ User edits  │───▶│ System logs │───▶│  correction_logs    │  │
│  │ extracted   │    │ field value │    │ correction  │    │  table              │  │
│  │ invoice     │    │             │    │             │    │                     │  │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────────────┘  │
│                                                                    │                 │
│                                                                    ▼                 │
│  PHASE 2: DATA AGGREGATION (Hourly)                     ┌─────────────────────┐     │
│  ══════════════════════════════════                     │  Aggregation Job    │     │
│                                                          │  ─────────────────  │     │
│  ┌─────────────────────────────────────────────────────▶│  • Group by field   │     │
│  │                                                       │  • Calculate rates  │     │
│  │  ┌─────────────────────────────────────────────────┐ │  • Detect patterns  │     │
│  │  │  Metrics Calculated:                            │ │  • Update dashboard │     │
│  │  │  • Error rate per field per day                 │ └──────────┬──────────┘     │
│  │  │  • High-confidence errors (model said >90%)     │            │                 │
│  │  │  • Error patterns (e.g., "6↔8 confusion")       │            ▼                 │
│  │  │  • Correction velocity (corrections per hour)   │  ┌─────────────────────┐    │
│  │  └─────────────────────────────────────────────────┘  │  field_accuracy     │    │
│  │                                                        │  _metrics table     │    │
│  │                                                        └─────────────────────┘    │
│  │                                                                   │               │
│  │  PHASE 3: TRIGGER EVALUATION (Daily)                              ▼               │
│  │  ═══════════════════════════════════                   ┌─────────────────────┐   │
│  │                                                         │  Retraining         │   │
│  │  ┌─────────────────────────────────────────────────────▶│  Trigger Check      │   │
│  │  │                                                      │  ─────────────────  │   │
│  │  │  Trigger Conditions:                                 │  IF error_rate >10% │   │
│  │  │  ☑ Field error rate > 10% for 7 days                │  OR samples > 1000  │   │
│  │  │  ☑ Accumulated corrections > 1,000                  │  OR weekly schedule │   │
│  │  │  ☑ Weekly scheduled retraining                      │  THEN → PHASE 4     │   │
│  │  │  ☑ Manual admin trigger                             └──────────┬──────────┘   │
│  │  └─────────────────────────────────────────────────────────────────┘              │
│  │                                                                    │               │
│  │                                                                    ▼               │
│  │  PHASE 4: TRAINING DATA PREPARATION (On trigger)      ┌─────────────────────┐    │
│  │  ═══════════════════════════════════════════════      │  Training Pipeline  │    │
│  │                                                        │  ─────────────────  │    │
│  │  ┌─────────────────────────────────────────────────────│  Step 1: Filter     │    │
│  │  │                                                     │  Step 2: Consent    │    │
│  │  │  Filter criteria:                                   │  Step 3: Anonymize  │    │
│  │  │  • Only from consented organizations                │  Step 4: Format     │    │
│  │  │  • Correction confidence > 95% (user was sure)     │  Step 5: Validate   │    │
│  │  │  • Not already used in training                    └──────────┬──────────┘    │
│  │  │  • Document quality score > 70%                                │               │
│  │  └────────────────────────────────────────────────────────────────┘               │
│  │                                                                    │               │
│  │                                                                    ▼               │
│  │  PHASE 5: MODEL TRAINING (Triggered)                  ┌─────────────────────┐    │
│  │  ═══════════════════════════════════                  │  Training Job       │    │
│  │                                                        │  (GPU Cluster)      │    │
│  │  ┌─────────────────────────────────────────────────────│  ─────────────────  │    │
│  │  │                                                     │  • Load base model  │    │
│  │  │  Training approach:                                 │  • Fine-tune on new │    │
│  │  │  • Incremental fine-tuning (not full retrain)      │    samples          │    │
│  │  │  • Learning rate: 1e-5 (conservative)              │  • Validate on      │    │
│  │  │  • Epochs: 3-5 max                                 │    holdout set      │    │
│  │  │  • Early stopping if validation degrades           │  • Save checkpoint  │    │
│  │  └─────────────────────────────────────────────────────└──────────┬──────────┘   │
│  │                                                                    │               │
│  │                                                                    ▼               │
│  │  PHASE 6: A/B TESTING & ROLLOUT (Gradual)             ┌─────────────────────┐    │
│  │  ════════════════════════════════════════             │  Model Registry     │    │
│  │                                                        │  ─────────────────  │    │
│  │  ┌─────────────────────────────────────────────────────│  v1.2.0 (prod)     │    │
│  │  │                                                     │  v1.2.1 (candidate)│    │
│  │  │  Rollout stages:                                   └──────────┬──────────┘    │
│  │  │  Stage 1:  5% traffic, 2 days, check no regression            │               │
│  │  │  Stage 2: 20% traffic, 3 days, check 5% improvement           ▼               │
│  │  │  Stage 3: 50% traffic, 5 days, stability check     ┌─────────────────────┐    │
│  │  │  Stage 4: 100% traffic, promote to production      │  Load Balancer      │    │
│  │  │                                                     │  ─────────────────  │    │
│  │  │  Rollback trigger:                                 │  5% → candidate     │    │
│  │  │  • Error rate increases by > 2%                    │  95% → production   │    │
│  │  │  • User corrections increase                       └─────────────────────┘    │
│  │  │  • Latency increases significantly                                             │
│  │  └────────────────────────────────────────────────────────────────────────────────│
│  │                                                                                    │
│  └────────────────────────── LOOP CONTINUES ─────────────────────────────────────────┘
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

**Phase 1: Correction Capture (Code Example)**

```python
# Backend: When user edits a field
async def handle_field_correction(
    invoice_id: UUID,
    user_id: UUID,
    field_name: str,
    original_value: str,
    corrected_value: str,
    model_confidence: float,
    document_region: dict  # Bounding box coordinates
):
    """
    Called when user corrects an extracted field.
    This is the entry point for the feedback loop.
    """
    # 1. Determine correction type based on field and error pattern
    correction_type = classify_correction_type(
        field_name=field_name,
        original=original_value,
        corrected=corrected_value
    )
    # correction_type examples:
    # - "ocr_error": Character-level mistake (e.g., "6" → "8")
    # - "ner_error": Wrong entity extraction (e.g., wrong PIB field)
    # - "layout_error": Field from wrong region
    # - "business_logic": Valid OCR but wrong interpretation

    # 2. Create correction log entry
    correction = CorrectionLog(
        invoice_id=invoice_id,
        user_id=user_id,
        field_name=field_name,
        original_value=original_value,
        corrected_value=corrected_value,
        model_confidence=model_confidence,
        correction_type=correction_type,
        document_region=document_region,
    )
    await db.save(correction)

    # 3. Update real-time metrics (for dashboard)
    await metrics_service.increment_correction_count(field_name)

    # 4. Check if this triggers immediate alerts
    if model_confidence > 0.90:
        # High-confidence error - this is particularly valuable feedback
        await alert_service.log_high_confidence_error(
            field_name=field_name,
            confidence=model_confidence,
            error_pattern=analyze_error_pattern(original_value, corrected_value)
        )

    return correction
```

**Phase 2: Aggregation Job (Scheduled)**

```python
# Scheduled job: Runs every hour
async def aggregate_correction_metrics():
    """
    Aggregate corrections into actionable metrics.
    """
    # 1. Get corrections from last period
    corrections = await db.query(
        CorrectionLog,
        where=CorrectionLog.created_at > datetime.now() - timedelta(hours=1)
    )

    # 2. Calculate metrics per field
    field_metrics = {}
    for correction in corrections:
        field = correction.field_name
        if field not in field_metrics:
            field_metrics[field] = {
                "total_extractions": 0,
                "corrections": 0,
                "high_confidence_errors": 0,
                "error_patterns": defaultdict(int)
            }

        field_metrics[field]["corrections"] += 1

        if correction.model_confidence > 0.90:
            field_metrics[field]["high_confidence_errors"] += 1

        # Classify error pattern
        pattern = classify_error_pattern(
            correction.original_value,
            correction.corrected_value
        )
        field_metrics[field]["error_patterns"][pattern] += 1

    # 3. Get total extractions (not just corrections) from invoice count
    total_invoices = await get_invoice_count_for_period(hours=1)
    for field in field_metrics:
        field_metrics[field]["total_extractions"] = total_invoices
        field_metrics[field]["error_rate"] = (
            field_metrics[field]["corrections"] /
            max(1, field_metrics[field]["total_extractions"])
        )

    # 4. Store aggregated metrics
    for field, metrics in field_metrics.items():
        await db.upsert(FieldAccuracyMetric(
            field_name=field,
            period_start=datetime.now() - timedelta(hours=1),
            period_end=datetime.now(),
            **metrics
        ))

    # 5. Update dashboard cache
    await cache.set("field_metrics_latest", field_metrics, ttl=3600)


def classify_error_pattern(original: str, corrected: str) -> str:
    """
    Classify the type of error for pattern analysis.
    """
    if not original or not corrected:
        return "missing_value"

    # Character confusion patterns
    char_confusion = {
        ("6", "8"): "digit_confusion_6_8",
        ("8", "6"): "digit_confusion_6_8",
        ("0", "O"): "zero_o_confusion",
        ("O", "0"): "zero_o_confusion",
        ("1", "l"): "one_l_confusion",
        ("5", "S"): "five_s_confusion",
    }

    # Check for single character differences
    if len(original) == len(corrected):
        diff_positions = [
            i for i, (a, b) in enumerate(zip(original, corrected))
            if a != b
        ]
        if len(diff_positions) == 1:
            pos = diff_positions[0]
            pair = (original[pos], corrected[pos])
            if pair in char_confusion:
                return char_confusion[pair]

    # Check for transposition
    if len(original) == len(corrected) and len(original) > 1:
        for i in range(len(original) - 1):
            if (original[i] == corrected[i+1] and
                original[i+1] == corrected[i] and
                original[:i] == corrected[:i] and
                original[i+2:] == corrected[i+2:]):
                return "transposition"

    # Check for missing/extra characters
    if abs(len(original) - len(corrected)) == 1:
        return "extra_or_missing_char"

    # Generic
    return "other"
```

**Phase 3: Retraining Trigger Evaluation**

```python
# Scheduled job: Runs daily at 2 AM
async def evaluate_retraining_triggers():
    """
    Check if any retraining triggers have been met.
    """
    triggers_met = []

    # Trigger 1: Field error rate threshold
    THRESHOLD_ERROR_RATE = 0.10  # 10%
    THRESHOLD_DAYS = 7

    for field in TRACKED_FIELDS:
        recent_metrics = await get_field_metrics(
            field_name=field,
            days=THRESHOLD_DAYS
        )
        avg_error_rate = sum(m.error_rate for m in recent_metrics) / len(recent_metrics)

        if avg_error_rate > THRESHOLD_ERROR_RATE:
            triggers_met.append({
                "trigger": "error_rate_threshold",
                "field": field,
                "error_rate": avg_error_rate,
                "threshold": THRESHOLD_ERROR_RATE
            })

    # Trigger 2: Volume threshold
    THRESHOLD_CORRECTIONS = 1000

    pending_corrections = await get_pending_corrections_count()
    if pending_corrections > THRESHOLD_CORRECTIONS:
        triggers_met.append({
            "trigger": "volume_threshold",
            "count": pending_corrections,
            "threshold": THRESHOLD_CORRECTIONS
        })

    # Trigger 3: Weekly scheduled (Sunday 2 AM)
    if datetime.now().weekday() == 6:  # Sunday
        triggers_met.append({
            "trigger": "weekly_schedule",
            "day": "Sunday"
        })

    # If any triggers met, initiate retraining pipeline
    if triggers_met:
        await initiate_training_pipeline(
            triggers=triggers_met,
            priority="normal" if len(triggers_met) == 1 else "high"
        )
        await notify_ml_team(triggers_met)

    return triggers_met
```

**Phase 4: Training Data Preparation**

```python
async def prepare_training_dataset(
    triggers: list,
    max_samples: int = 10000
) -> TrainingDataset:
    """
    Prepare anonymized training data from corrections.
    """
    # 1. Query eligible corrections
    corrections = await db.query(
        CorrectionLog,
        where=and_(
            CorrectionLog.used_for_training == False,
            CorrectionLog.created_at > datetime.now() - timedelta(days=90)
        ),
        limit=max_samples * 2  # Query extra for filtering
    )

    training_samples = []

    for correction in corrections:
        # 2. Check consent
        org = await get_organization(correction.invoice.organization_id)
        if not org.training_consent:
            continue  # Skip - no consent

        # 3. Get document image
        document = await get_document(correction.invoice.document_id)
        if not document:
            continue

        # 4. Extract relevant region from document
        region_image = await extract_document_region(
            document_path=document.storage_path,
            bbox=correction.document_region,
            padding=50  # Add context around the field
        )

        # 5. Anonymize the image
        # Replace sensitive data with synthetic data
        anonymized_image = await anonymize_document_region(
            image=region_image,
            field_type=correction.field_name,
            # Keep the structure but replace actual values
            preserve_layout=True
        )

        # 6. Create training sample
        sample = TrainingSample(
            image=anonymized_image,
            field_name=correction.field_name,
            label=anonymize_value(correction.corrected_value, correction.field_name),
            original_prediction=anonymize_value(correction.original_value, correction.field_name),
            correction_type=correction.correction_type,
            metadata={
                "original_confidence": correction.model_confidence,
                "error_pattern": classify_error_pattern(
                    correction.original_value,
                    correction.corrected_value
                )
            }
        )
        training_samples.append(sample)

        # 7. Mark as used
        correction.used_for_training = True
        await db.save(correction)

        if len(training_samples) >= max_samples:
            break

    # 8. Split into train/validation
    random.shuffle(training_samples)
    split_point = int(len(training_samples) * 0.9)

    return TrainingDataset(
        train_samples=training_samples[:split_point],
        validation_samples=training_samples[split_point:],
        metadata={
            "triggers": triggers,
            "total_samples": len(training_samples),
            "created_at": datetime.now().isoformat()
        }
    )


def anonymize_value(value: str, field_type: str) -> str:
    """
    Replace real values with synthetic equivalents.
    Preserves format and pattern but removes PII.
    """
    if field_type == "seller_pib" or field_type == "buyer_pib":
        # Generate valid-looking but fake PIB
        return generate_synthetic_pib()

    elif field_type == "seller_name" or field_type == "buyer_name":
        # Replace with synthetic company name
        return generate_synthetic_company_name()

    elif field_type in ["total_amount", "subtotal", "tax_amount"]:
        # Randomize the amount while keeping format
        return randomize_amount(value)

    elif field_type == "invoice_number":
        # Keep format, randomize values
        return randomize_invoice_number(value)

    else:
        return value  # Keep other fields as-is
```

**Phase 5 & 6: Training and Deployment**

```python
# Training job (runs on GPU cluster)
async def run_training_job(dataset: TrainingDataset):
    """
    Fine-tune the model on new correction data.
    """
    # 1. Load current production model
    base_model = load_model("dots_ocr_production_latest")

    # 2. Configure fine-tuning
    training_config = {
        "learning_rate": 1e-5,
        "epochs": 5,
        "batch_size": 16,
        "early_stopping_patience": 2,
        "warmup_steps": 100
    }

    # 3. Run training
    trainer = ModelTrainer(
        model=base_model,
        train_data=dataset.train_samples,
        val_data=dataset.validation_samples,
        config=training_config
    )

    training_result = await trainer.train()

    # 4. Evaluate on validation set
    val_metrics = await trainer.evaluate(dataset.validation_samples)

    # 5. Compare to production model
    prod_metrics = await evaluate_production_model(dataset.validation_samples)

    improvement = {
        "accuracy_delta": val_metrics.accuracy - prod_metrics.accuracy,
        "error_rate_delta": prod_metrics.error_rate - val_metrics.error_rate,
        "latency_delta": val_metrics.avg_latency - prod_metrics.avg_latency
    }

    # 6. Save if improved
    if improvement["accuracy_delta"] > 0 and improvement["latency_delta"] < 100:
        new_version = await model_registry.save(
            model=trainer.model,
            version=generate_version(),
            metrics=val_metrics,
            training_metadata=dataset.metadata
        )

        # 7. Start A/B test
        await start_ab_test(
            control_model="dots_ocr_production_latest",
            treatment_model=new_version,
            initial_traffic_split=0.05  # 5% to new model
        )

        return {
            "status": "success",
            "new_version": new_version,
            "improvement": improvement
        }
    else:
        return {
            "status": "no_improvement",
            "metrics": val_metrics,
            "comparison": improvement
        }


# A/B test monitoring (runs continuously)
async def monitor_ab_test(test_id: str):
    """
    Monitor A/B test and auto-promote or rollback.
    """
    test = await get_ab_test(test_id)

    while test.status == "running":
        # Get metrics for both models
        control_metrics = await get_model_metrics(
            test.control_model,
            since=test.started_at
        )
        treatment_metrics = await get_model_metrics(
            test.treatment_model,
            since=test.started_at
        )

        # Check for regression
        if treatment_metrics.error_rate > control_metrics.error_rate * 1.02:  # 2% worse
            await rollback_ab_test(test_id, reason="Error rate regression detected")
            await notify_ml_team(f"A/B test {test_id} rolled back: error regression")
            return

        # Check for promotion criteria
        sample_size = treatment_metrics.total_samples
        stage = get_current_stage(test)

        if sample_size >= stage.min_samples:
            if meets_promotion_criteria(treatment_metrics, control_metrics, stage):
                next_stage = get_next_stage(stage)
                if next_stage:
                    await advance_traffic_split(test_id, next_stage.traffic_split)
                    await notify_ml_team(f"A/B test {test_id} advanced to {next_stage.traffic_split*100}%")
                else:
                    # Final stage - promote to production
                    await promote_model(test.treatment_model)
                    await end_ab_test(test_id, status="promoted")
                    await notify_ml_team(f"Model {test.treatment_model} promoted to production!")
                    return

        await asyncio.sleep(300)  # Check every 5 minutes
```

**Monitoring Dashboard Queries:**

```sql
-- Query: Field accuracy over time (for dashboard chart)
SELECT
    field_name,
    DATE_TRUNC('day', period_start) as day,
    AVG(error_rate) as avg_error_rate,
    SUM(corrections) as total_corrections,
    SUM(high_confidence_errors) as high_confidence_errors
FROM field_accuracy_metrics
WHERE period_start > NOW() - INTERVAL '30 days'
GROUP BY field_name, DATE_TRUNC('day', period_start)
ORDER BY field_name, day;

-- Query: Top error patterns (for ML team)
SELECT
    field_name,
    error_patterns->>'pattern' as pattern,
    COUNT(*) as occurrence_count,
    AVG(model_confidence) as avg_confidence_when_wrong
FROM correction_logs
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY field_name, error_patterns->>'pattern'
ORDER BY occurrence_count DESC
LIMIT 20;

-- Query: Retraining readiness
SELECT
    COUNT(*) FILTER (WHERE used_for_training = FALSE) as pending_samples,
    COUNT(*) FILTER (WHERE used_for_training = TRUE) as used_samples,
    COUNT(DISTINCT organization_id) FILTER (
        WHERE organization_id IN (
            SELECT id FROM organizations WHERE training_consent = TRUE
        )
    ) as consented_org_samples
FROM correction_logs
WHERE created_at > NOW() - INTERVAL '90 days';
```

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
| GDPR | Data processing agreements, DPO, privacy policy |
| Serbian Data Protection | Local compliance requirements (Zakon o zaštiti podataka o ličnosti) |
| PCI DSS | Not storing payment data (Stripe handles) |

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

#### 10.6.2 Consent Management for Model Training

**Consent Types:**

| Consent Type | Scope | Granularity | Revocable |
|--------------|-------|-------------|-----------|
| Basic Processing | Invoice OCR, data extraction | Required | No (service essential) |
| Analytics | Usage patterns, performance metrics | Organization-level | Yes |
| Model Training | Document samples for AI improvement | Organization-level | Yes |
| Marketing | Product updates, newsletters | User-level | Yes |

**Consent Flow:**

```
Organization Settings → Data & Privacy → AI Training Consent
┌─────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  🤖 Učešće u poboljšanju AI modela                                  │
│                                                                      │
│  Dozvoli korišćenje anonimiziranih dokumenata za unapređenje       │
│  tačnosti OCR sistema.                                              │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ ☐ Dozvoljavam korišćenje anonimiziranih faktura             │   │
│  │   za trening AI modela                                       │   │
│  │                                                               │   │
│  │   • Svi podaci se anonimiziraju pre korišćenja              │   │
│  │   • PIB, nazivi firmi i iznosi se maskiraju                 │   │
│  │   • Možete opozvati saglasnost u bilo kom trenutku          │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  Status: ✅ Aktivno (od 15.01.2025)                                 │
│                                                                      │
│  [Opozovi saglasnost]                                               │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

**Consent Database Schema:**
```sql
CREATE TABLE consent_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    user_id UUID NOT NULL REFERENCES users(id),
    consent_type VARCHAR(50) NOT NULL,
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
1. User clicks "Opozovi saglasnost"
2. Confirmation dialog explains implications
3. On confirm: `revoked_at` timestamp set
4. Background job queues anonymization of all their documents in training dataset
5. Within 30 days: all training samples from their documents are removed from active training sets
6. Confirmation email sent to user

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
| Correction logs | 3 years | ML improvement |
| Training data | Until consent revoked | User consent |
| Session data | 30 days | Technical necessity |
| Temporary files | 24 hours | Processing |

**Right to Erasure (GDPR Article 17):**

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

**Log Retention:** 12 months minimum

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

### 12.2 Payment Integration (Stripe)

**Features Used:**
- Stripe Checkout for subscriptions
- Customer Portal for billing management
- Webhooks for subscription events
- Invoice generation

**Webhook Events:**
- `customer.subscription.created`
- `customer.subscription.updated`
- `customer.subscription.deleted`
- `invoice.paid`
- `invoice.payment_failed`

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

**Lifecycle Rules:**
- Documents: 12 months retention
- Exports: 30 days auto-delete
- Backups: 90 days retention

### 12.5 SEF Integration (eFaktura)

The Serbian E-Invoice System (Sistem Elektronskih Faktura - SEF) is mandatory for B2G and B2B transactions in Serbia. FakturaAI MUST integrate with SEF as a **first-class input source**, not just an export format.

#### 12.5.1 Overview

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
│             │  (Pull)   │ │  (Push)   │ │  (Webhook)│              │
│             └───────────┘ └───────────┘ └───────────┘              │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

#### 12.5.2 SEF Connection Setup

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
    "sync_interval_minutes": 15,
    "webhook_url": "https://api.fakturaai.rs/webhooks/sef/{org_id}"
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

#### 12.5.3 Inbound Invoice Sync (SEF → FakturaAI)

The system MUST pull invoices from SEF and process them through the FakturaAI pipeline.

**Sync Flow:**

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Inbound Invoice Sync Flow                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  1. Poll SEF API (every 15 minutes or on webhook)                   │
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

#### 12.5.4 Outbound Invoice Push (FakturaAI → SEF)

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

#### 12.5.5 SEF Status Webhooks

The system SHOULD receive real-time status updates from SEF via webhooks.

**Webhook Endpoint:**

`POST /api/v1/webhooks/sef/{organization_id}`

**Webhook Payload:**

```json
{
  "event_type": "INVOICE_STATUS_CHANGED",
  "sef_id": "12345678-1234-1234-1234-123456789012",
  "old_status": "DELIVERED",
  "new_status": "APPROVED",
  "timestamp": "2025-01-15T14:30:00Z",
  "metadata": {
    "approved_by": "Ime Prezime",
    "approval_note": "Odobreno za plaćanje"
  }
}
```

**Webhook Processing:**

```python
async def handle_sef_webhook(payload: SEFWebhookPayload, org_id: UUID):
    """
    Process SEF status change webhook.
    """
    # 1. Verify webhook signature
    if not verify_sef_signature(payload):
        raise HTTPException(401, "Invalid signature")

    # 2. Find corresponding invoice
    sef_invoice = await get_sef_invoice(org_id, payload.sef_id)
    if not sef_invoice:
        logger.warning(f"Unknown SEF invoice: {payload.sef_id}")
        return {"status": "ignored"}

    # 3. Update status
    old_status = sef_invoice.sef_status
    sef_invoice.sef_status = payload.new_status
    sef_invoice.sef_status_updated_at = payload.timestamp

    # 4. Handle specific status transitions
    match payload.new_status:
        case "APPROVED":
            # Invoice accepted by buyer - safe to book
            await mark_invoice_accepted(sef_invoice.invoice_id)
            await notify_user(sef_invoice, "Faktura odobrena od strane kupca")

        case "REJECTED":
            # Invoice rejected - needs attention
            await flag_invoice_for_review(
                sef_invoice.invoice_id,
                reason=f"Odbijena na SEF: {payload.metadata.get('rejection_reason')}"
            )
            await notify_user(sef_invoice, "Faktura odbijena!", priority="high")

        case "CANCELLED":
            # Invoice cancelled - create reversal if already booked
            if sef_invoice.invoice.status == "exported":
                await create_cancellation_record(sef_invoice.invoice_id)

        case "PAID":
            # Payment recorded in SEF
            await update_payment_status(sef_invoice.invoice_id, paid=True)

    # 5. Log status change
    await log_sef_status_change(sef_invoice, old_status, payload)

    return {"status": "processed"}
```

#### 12.5.6 SEF-OCR Hybrid Processing

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

#### 12.5.7 SEF Inbox UI

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

#### 12.5.8 SEF Error Handling

| Error | Cause | Recovery |
|-------|-------|----------|
| `SEF_CONNECTION_FAILED` | Network/API issues | Retry with exponential backoff |
| `SEF_AUTH_EXPIRED` | API key/cert expired | Notify admin, disable sync |
| `SEF_RATE_LIMITED` | Too many requests | Back off, reduce sync frequency |
| `SEF_INVALID_RESPONSE` | Unexpected data format | Log, skip invoice, alert |
| `SEF_DUPLICATE_INVOICE` | Already processed | Skip, update status only |
| `UBL_PARSE_ERROR` | Malformed XML | Log, attempt PDF-only processing |

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
- Stripe webhook handling
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
| PIB | Poreski Identifikacioni Broj - Tax Identification Number |
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
3. GDPR - General Data Protection Regulation
4. APR API Documentation
5. dots.ocr Documentation (Vision-Language Model)
6. EasyOCR Documentation (fallback OCR)
7. FastAPI Documentation
8. Next.js Documentation

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | January 2025 | FakturaAI Team | Initial release |
| 1.1 | January 2025 | FakturaAI Team | Added: Business Logic & Validation Rules (4.9), Human-in-the-Loop & Feedback System (9.9), Legal & Compliance Flows (10.6) |
| 1.2 | January 2025 | FakturaAI Team | Added: Accounting Intent Layer (4.10), Automation Rules Engine (4.11), SEF Integration (12.5), Expanded Feedback Loop Implementation (9.9.7) |
| 1.3 | January 2025 | FakturaAI Team | Updated OCR stack: dots.ocr (VLM) as primary engine with unified layout+OCR, EasyOCR as fallback, removed separate LayoutParser (Tesseract removed) |

---

**End of Document**
