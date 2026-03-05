## 1. What is FakturaAI?

FakturaAI is a web-based invoice processing platform built specifically for the Serbian market. It uses artificial intelligence to automate the manual, time-consuming work of reading invoices, extracting data, verifying correctness, and preparing accounting entries.

**The core promise:** An accountant uploads a stack of invoices. Within seconds, the system reads every invoice, extracts all relevant data (PIB, company names, amounts, line items, VAT), verifies the numbers, suggests the correct accounting entries, and presents everything for a quick review. What used to take hours now takes minutes.

The accountant remains fully in control — the system proposes, the human approves.

---

## 2. High-Level System Overview

The following diagram shows the major components of the FakturaAI platform and how they connect:

```
┌──────────────────────────────────────────────────────────────┐
│                     FakturaAI Platform                        │
│                                                              │
│  Web App (Next.js) ◄──► REST API (FastAPI) ◄──► Workers      │
│  Dashboard, Upload,     Auth, Invoices,        (Celery+Redis)│
│  Invoices, SEF Inbox,   Rules, Analytics,      OCR, Extract, │
│  Rules, Settings        Export, Audit          Validate, SEF │
│                                                              │
│        PostgreSQL (All Data)      Document Store (S3/R2)     │
└──────────────────────────────────────────────────────────────┘
         │                    │                   │
         ▼                    ▼                   ▼
   SEF Portal           dots.ocr            Claude API
   (eFaktura)           (VLM OCR)           (Extraction)
```

**Components at a glance:**

| Component | Role |
|-----------|------|
| **Web App** (Next.js) | What the user sees — upload, review, rules, export |
| **REST API** (FastAPI) | Business logic, authentication, data management |
| **Workers** (Celery) | Background OCR/extraction without blocking the user |
| **PostgreSQL** | All data — invoices, users, rules, audit logs |
| **Document Store** (S3/R2) | Original invoice files (PDFs, images) |
| **External: SEF, dots.ocr, Claude** | eFaktura portal, OCR engine, AI extraction |

---

## 3. User Journey Map

This diagram shows the complete user journey from first registration to exported accounting data:

```
┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
│  Sign Up │────►│ Upload  │────►│ System  │────►│ Review  │────►│ Export  │
│  & Login │     │ Invoice │     │ Process │     │ & Approve│     │ Data    │
└─────────┘     └─────────┘     └─────────┘     └─────────┘     └─────────┘
     │               │               │               │               │
     │               │               │               │               │
     ▼               ▼               ▼               ▼               ▼
 Create org      Manual upload   OCR reads text   View extracted   XLSX, CSV,
 Invite team     SEF inbox       AI extracts      data with        JSON, XML export
 Set up rules    Batch upload    fields           confidence       MiniMax push
                 (up to 50)     Validates PIB     Edit mistakes    Custom templates
                                Checks math       Accept/reject    Audit package
                                Suggests konta    Corrections
                                Runs rules        logged
```

---

## 4. Step 1 — Registration & Organization Setup

### What the User Does

1. Opens FakturaAI in a web browser
2. Creates an account with email, password, name, and organization name
3. Receives access immediately (no email verification delay)
4. Sees the dashboard — empty at first, ready for the first invoice

### What Happens Behind the Scenes

```
User fills form ──► API creates Organization ──► API creates User ──► JWT tokens issued
                         │                            │                      │
                         ▼                            ▼                      ▼
                    Org becomes the                User linked to         Tokens stored
                    data boundary                  org as admin           in browser
                    (tenant isolation)                                    (secure cookies)
```

**Key concepts:**

- **Organization** = one company or accounting office. All data belongs to an organization. Users from one organization can never see data from another.
- **User roles:** Admin (full access including audit logs and settings) and Member (day-to-day operations).
- **Security:** Passwords are hashed with Argon2 (industry standard). Every login and action is recorded in the audit log.

---

## 5. Step 2 — Invoice Intake

Invoices can enter the system through three channels:

### Channel A — Manual Upload

The user drags and drops files (or clicks to browse) on the Upload page.

- **Supported formats:** PDF, PNG, JPG, TIFF, WEBP
- **Limits:** Up to 50 files at once, max 20 MB per file, 200 MB total per batch
- **Validation:** File type, size, and image resolution (minimum 500×400px) checked immediately

### Channel B — SEF Inbox (eFaktura)

Serbia's electronic invoicing system (SEF) delivers invoices digitally. FakturaAI polls the SEF portal periodically and imports new invoices automatically.

- Invoices appear in the SEF Inbox page with status "new"
- User reviews and decides: accept (import for processing) or reject/archive
- Accepted invoices enter the same processing pipeline as uploaded ones

### Channel C — API Integration

For advanced users, invoices can be submitted programmatically via the REST API, enabling integration with ERP systems or other business tools.

### Intake Flow

```
  ┌────────────┐  ┌────────────┐  ┌────────────┐
  │ Manual     │  │ SEF Inbox  │  │ API Call   │
  │ Upload     │  │ (Polling)  │  │ (External) │
  └──────┬─────┘  └──────┬─────┘  └──────┬─────┘
         └───────────────┼───────────────┘
                         ▼
              Validate ──► Store in S3 ──► Create Record ──► Queue Processing
              (type,size)                  (status: processing)
```

Once queued, the user sees the invoice in their list with a "Processing" status. They can continue uploading more invoices — processing happens in the background.

---

## 6. Step 3 — OCR & Text Recognition

**Goal:** Convert the invoice image or PDF into machine-readable text.

### What the User Sees

A spinning indicator on the invoice card showing processing progress (roughly 10–40%).

### What Happens Behind the Scenes

The original document (PDF or image) is sent directly to the OCR engine — no image preprocessing is applied. The engine is a Vision Language Model (VLM) that works best with raw, unmodified images.

```
┌────────────────────────────────────────────────────────────┐
│  OCR Engine (dots.ocr) — Vision Language Model             │
│                                                            │
│  Original Invoice (PDF/image)                              │
│       │  sent directly — no preprocessing                  │
│       ▼                                                    │
│  • Runs on dedicated inference server                      │
│  • Reads both Cyrillic and Latin scripts natively          │
│  • Understands document layout, tables, and structure      │
│  • Processes the full page in a single pass                │
│  • Returns: complete text + confidence score (0-100%)      │
│                                                            │
│  Unlike traditional OCR, a VLM "sees" the entire document  │
│  at once and understands context — like a human reads.     │
└────────────────────────────────────────────────────────────┘
```

**Key points:**

- **No preprocessing needed** — the VLM handles tilted, noisy, and low-contrast documents natively. Sending raw images preserves color and layout information that helps the model.
- **Full Cyrillic and Latin support** — critical for Serbian invoices which may use either or both scripts.
- If OCR confidence is too low (badly damaged or handwritten document), the invoice is flagged for manual data entry.

---

## 7. Step 4 — Intelligent Field Extraction

**Goal:** Transform raw OCR text into structured, usable data.

### What the User Sees

Progress indicator advances to roughly 70%. This step typically takes 2–5 seconds.

### What Happens Behind the Scenes

The raw text from OCR is sent to an AI language model (Claude) that has been instructed to identify and extract specific fields from Serbian invoices.

```
┌─────────────────────────────────┐     ┌─────────────────────────────────┐
│         Raw OCR Text             │     │        Structured Output         │
│                                 │     │                                 │
│  "RAČUN br. 2026-0142          │     │  invoice_number: "2026-0142"    │
│   Datum: 15.02.2026.           │     │  invoice_date: "2026-02-15"     │
│   PIB: 123456789               │ ──► │  seller:                        │
│   Acme d.o.o.                  │     │    pib: "123456789"             │
│   Beograd, Kneza Miloša 10    │     │    name: "Acme d.o.o."          │
│   ...                          │     │    city: "Beograd"              │
│   Ukupno: 59.000,00 RSD       │     │  total_amount: 59000.00         │
│   PDV 20%: 9.833,33 RSD"      │     │  tax_amount: 9833.33            │
│                                 │     │  currency: "RSD"                │
└─────────────────────────────────┘     └─────────────────────────────────┘
```

### Fields Extracted

| Category | Fields |
|----------|--------|
| **Seller** | PIB, company name, address, city, postal code |
| **Buyer** | PIB, company name, address, city, postal code |
| **Invoice** | Invoice number, date, due date, purchase order number |
| **Amounts** | Subtotal, tax amount, total amount, currency |
| **Line Items** | Description, quantity, unit price, total per item |
| **Tax Groups** | Tax rate, tax base, tax amount (per rate) |

**Fallback mechanism:** If the AI model is unavailable, a regex-based extractor handles the most common fields (PIB, invoice number, dates, amounts). This ensures the system remains operational even during API outages.

---

## 8. Step 5 — Validation & Quality Assurance

**Goal:** Verify that extracted data is correct and flag potential problems.

Three types of validation run automatically:

### 8.1 PIB Validation

Every extracted PIB (tax identification number) is checked:

```
PIB: 123456789
  [ok] Format check — exactly 9 digits, no leading zero
  [ok] Checksum — ISO 7064 Mod 11,10 algorithm passes
  Result: VALID
```

- **Seller PIB** — must be valid (required for accounting classification)
- **Buyer PIB** — validated but optional (cash invoices may not have one)

### 8.2 Mathematical Verification

The system re-checks the arithmetic on every invoice:

```
Line Items:
  Item 1:  5 × 2.000,00 = 10.000,00  [ok]
  Item 2:  3 × 3.000,00 =  9.000,00  [ok]

Subtotal check:
  10.000,00 + 9.000,00 = 19.000,00  [ok]  (matches extracted subtotal)

Tax check:
  19.000,00 × 20% = 3.800,00  [ok]  (matches extracted tax amount)

Total check:
  19.000,00 + 3.800,00 = 22.800,00  [ok]  (matches extracted total)
```

**Important design decision:** The system does not recompute tax from subtotal × rate and replace the extracted value. It checks whether the extracted numbers are internally consistent. This respects rounding differences that are common in real-world invoices.

### 8.3 Duplicate Detection

Checks whether an invoice with the same number, seller PIB, and date already exists. Returns a warning if found — but does not block processing (the user decides).

### Confidence Scoring

Every extracted field receives a confidence score (0–100%) based on:

| Factor | Weight | Description |
|--------|--------|-------------|
| OCR confidence | 40% | How certain the OCR engine was about the text |
| Validation result | 30% | Whether the value passes format/checksum checks |
| Pattern strength | 20% | Whether the value matches expected patterns |
| Cross-field consistency | 10% | Whether the value is consistent with other fields |

Fields below 80% confidence are highlighted for manual review.

---

## 9. Step 6 — Accounting Intelligence

**Goal:** Automatically suggest accounting entries so the accountant doesn't have to classify every invoice manually.

This is a five-step classification pipeline:

```
Step 1              Step 2              Step 3             Step 4            Step 5
Document Type  ──►  Transaction Type ──► VAT Treatment ──► Konta         ──► Review Flags
                                                           Suggestion
• Invoice           • Domestic          • Fully deduct.    • 5010 Goods      • High-value
• Credit note       • EU import         • Partial deduct.  • 5120 Office     • Foreign tx
• Advance           • Non-EU            • Non-deductible   • 5131 Fuel       • Non-deduct.
• Proforma          • Reverse charge    • Output / Exempt  • 5330 Services   • Non-std VAT
```

### Example Classification

| Invoice Content | System Suggestion |
|-----------------|-------------------|
| Fuel invoice from NIS Petrol, PIB 100002270, 15,000 RSD | Document: Input Invoice. Transaction: Domestic. VAT: Partially deductible (fuel 50%). Konto: 5131. Flag: Non-deductible category. |
| IT consulting from EU company, EUR 2,000 | Document: Input Invoice. Transaction: Foreign EU. VAT: Reverse charge. Konto: 5330. Flag: Foreign + reverse charge. |
| Office supplies from local retailer, 8,500 RSD | Document: Input Invoice. Transaction: Domestic. VAT: Fully deductible. Konto: 5120. No flags. |

---

## 10. Step 7 — Automation Rules Engine

**Goal:** Let accountants define custom rules that automatically classify invoices without manual intervention.

The rules engine is **100% deterministic** — no AI is involved. Rules use exact matching, pattern matching, and numeric comparisons. This guarantees that the same invoice will always produce the same result.

### How Rules Work

```
┌──────────────────────────────────────────────────────────────┐
│                     Rule Definition                           │
│                                                              │
│  Name: "Office supplies from Comtrade"                       │
│  Priority: 10 (runs early)                                   │
│  Type: KONTO_ASSIGNMENT                                      │
│                                                              │
│  IF:                                                         │
│    seller.pib = "100065014"                                  │
│    AND total_amount < 50,000                                 │
│                                                              │
│  THEN:                                                       │
│    Set konto to 5120 (Office supplies)                       │
│    Auto-approve                                              │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Rule Types

| Rule Type | What It Does |
|-----------|-------------|
| **Konto Assignment** | Automatically assigns the correct account code |
| **VAT Treatment** | Sets the VAT classification (deductible, exempt, etc.) |
| **Auto-Approve** | Marks trusted invoices as verified without manual review |
| **Flag for Review** | Forces specific invoices to require manual review |
| **Document Type** | Reclassifies the document type |
| **Custom Field** | Sets any additional metadata |

### Pre-Built Templates

FakturaAI comes with nine ready-to-use rule templates for common Serbian accounting scenarios. Users can apply a template and customize it rather than building rules from scratch:

- Small-value purchase auto-approval
- Foreign supplier flagging
- Utility bill classification
- Office supply routing
- And more

### Execution Flow

```
Invoice enters verification ──► Load active rules (sorted by priority)
  │
  ├─► Rule 1 (pri. 10) ──► Match? ──► YES: Apply actions  /  NO: Skip
  ├─► Rule 2 (pri. 20) ──► Match? ──► YES: Apply actions  /  NO: Skip
  ├─► Rule 3 (pri. 30) ──► Match? ──► YES: Apply actions  /  NO: Skip
  └─► (...)
  │
  ▼
  Merge all matching actions ──► Resolve conflicts (last writer wins) ──► Save + Log
```

For detailed technical documentation of the rules engine, see [AUTOMATION_RULES.md](AUTOMATION_RULES.md).

---

## 11. Step 8 — Human Review & Approval

**Goal:** Give the accountant full visibility and control before any data leaves the system.

### What the User Sees

The invoice detail page shows:

```
┌───────────────────────────────┬───────────────────────────────────┐
│  Original Document            │  Invoice #2026-0142               │
│  (PDF viewer / image preview) │                                   │
│                               │  Seller: Acme d.o.o.         OK  │
│  The accountant can see the   │  PIB: 123456789              OK  │
│  original document side-by-   │  Buyer: MojFirma d.o.o.      OK  │
│  side with extracted data     │  PIB: 987654321              OK  │
│                               │  Date: 15.02.2026.           OK  │
│                               │  Subtotal: 49.166,67         OK  │
│                               │  PDV 20%:   9.833,33         OK  │
│                               │  Total:    59.000,00         OK  │
│                               │  Konto: 5330 (Services)      OK  │
│                               │  VAT: Fully deductible       OK  │
│                               │                                   │
│                               │  [!] 1 warning: buyer address 72% │
│                               │  [Accept]  [Edit]  [Reject]      │
└───────────────────────────────┴───────────────────────────────────┘
```

### Confidence Indicators

- **[OK] Green (80-100%):** High confidence — likely correct
- **[!] Yellow (50-79%):** Medium confidence — review recommended
- **[X] Red (below 50%):** Low confidence — manual verification needed

### User Actions

| Action | What Happens |
|--------|-------------|
| **Accept** | Invoice status changes to "verified". Accounting entries confirmed. |
| **Edit** | User clicks a field, types the correction. Original and corrected values are both recorded. |
| **Reject** | Invoice marked as error or deleted. |
| **Flag for review** | Invoice stays in review queue for a senior accountant. |

### Correction Tracking

Every manual edit is permanently recorded:

```
Correction Log Entry:
  Field: seller.address
  Original value: "Kneza Miloša 1O"   (OCR read "O" instead of "0")
  Corrected value: "Kneza Miloša 10"
  Confidence was: 72%
  Corrected by: marko@agencija.rs
  Timestamp: 2026-03-03 14:22:15
```

This correction log serves two purposes:
1. **Quality monitoring** — identify which fields and which suppliers cause the most errors
2. **Audit trail** — full traceability of every change for compliance

---

## 12. Step 9 — Export & Integration

**Goal:** Get the processed data out of FakturaAI and into the accountant's existing tools.

### Export Formats

| Format | Use Case |
|--------|----------|
| **XLSX** | Multi-sheet workbook — Invoices, Line Items, and Accounting sheets |
| **CSV** | UTF-8 with BOM for Serbian character support; configurable delimiter (semicolon, comma, tab) |
| **JSON** | Flat (array of records) or nested (full invoice objects with line items) |
| **MiniMax XML** | Direct import format for MiniMax accounting software; requires verified invoices with valid PIB |

### Serbian Formatting

All exports use Serbian locale conventions by default:

- **Decimal separator:** comma (59.000,00)
- **Date format:** DD.MM.YYYY (15.06.2025.)
- **Serbian headers:** "Broj fakture", "Datum fakture", "Ukupan iznos", etc.
- **UTF-8 BOM** in CSV files for correct display in Excel

### Export Safety Rules

The system blocks export of invoices that are not ready:

- **Missing required fields** (invoice number, date, seller info, amounts) — blocked
- **Low confidence** (below 70%) — blocked with warning
- **MiniMax XML** additionally requires verified status and valid 9-digit PIB

### Export Templates

FakturaAI provides four system templates and supports custom user-defined templates:

**System Templates (built-in):**

| Template | Fields | Formats |
|----------|--------|---------|
| **Standardni izvoz** | All 16 fields in standard order | XLSX, CSV, JSON |
| **Racunovodstveni izvoz** | Invoice number, seller, PIB, date, amounts, currency | XLSX, CSV, JSON |
| **MiniMax izvoz** | Fixed XML schema (not customizable) | MiniMax XML |
| **PDV evidencija** | Tax-relevant fields for VAT return | XLSX, CSV |

**Custom Templates:**

Users can create their own templates with:
- **Field selection** — choose which of the 16 available fields to include
- **Field ordering** — arrange columns in any order
- **Custom labels** — rename column headers (e.g., "Broj fakture" → "Br. fakt.")
- **Format overrides** — set date format and decimal separator per template

```
Custom Template Example:
  Name: "Mesečni izveštaj"
  Fields:
    1. invoice_number  → "Br. fakture"
    2. seller_name     → "Dobavljač"
    3. total_amount    → "Iznos"
    4. tax_amount      → "PDV"
  Formats: XLSX, CSV
```

Templates are scoped per organization — each organization manages its own custom templates while system defaults are always available to all.

### MiniMax Integration

For organizations using MiniMax accounting software, FakturaAI supports direct data push:

```
┌───────────────┐     ┌────────────────┐     ┌──────────────────┐
│  FakturaAI    │────►│ MiniMax REST   │────►│ MiniMax Software │
│  (Verified    │     │ API            │     │ (Accounting)     │
│   invoices)   │     │ Basic Auth     │     │                  │
└───────────────┘     └────────────────┘     └──────────────────┘
```

**Setup:** Organization configures MiniMax credentials (URL, username, password) in Settings. The system stores encrypted credentials and validates the connection.

**Push flow:** Select verified invoices → "Push to MiniMax" → System converts to MiniMax XML → Sends via REST API → Reports success/failure per invoice.

### Audit Export

For tax inspections (Poreska Uprava), administrators generate a comprehensive export package:

```
Audit Export Package (ZIP):
  ├── invoice_register.xlsx     (structured register of all invoices in period)
  ├── vat_summary.xlsx          (VAT breakdown by rate and period)
  ├── audit_trail.csv           (who did what and when — all actions logged)
  └── original_documents/       (original PDFs and images)
```

**Access control:** Only users with admin role can generate audit exports.

**Tracking:** Every audit export is recorded in the database with:
- Date range and reason (e.g., "Poreska kontrola br. 123/2025")
- Invoice count and file size
- Presigned download URL (expires after 30 days)
- Lifecycle status: processing → ready → expired

Administrators can view the full audit export history for their organization.

### Export Flow

```
User selects invoices ──► Choose format + template
                              │
                    ┌─────────┴──────────┐
                    │                    │
               Direct export       MiniMax push
                    │                    │
                    ▼                    ▼
            Safety checks          Verify status
            (required fields,      (must be verified,
             confidence ≥ 70%)      valid PIB)
                    │                    │
                    ▼                    ▼
            Apply template         Convert to XML
            (field selection,      and POST to
             ordering, labels)     MiniMax API
                    │                    │
                    ▼                    ▼
            Generate file          Return success
            (XLSX/CSV/JSON)        per invoice
                    │
                    ▼
            Download with
            Serbian filename
            (fakture_2025-06-15.xlsx)
```

---

## 13. Complete Data Flow

This diagram traces a single invoice through the entire system, from upload to export:

```
 UPLOAD          PROCESS                          REVIEW & EXPORT
 ──────          ───────                          ───────────────
 User uploads    1. Store in S3                   7. User reviews data
 PDF / image     2. Prepare document              8. Correct errors if needed
      │          3. OCR — dots.ocr VLM            9. Approve invoice
 SEF inbox  ───► 4. AI extraction — Claude LLM   10. Export (XLSX/CSV/JSON/XML)
 import          5. Validate (PIB, math, dupes)   11. MiniMax push (optional)
      │          6. Accounting intelligence        12. Audit export (admin)
 API call           (type, VAT, konta, rules)
                                                         AUDIT LOG
                                                      (every step recorded)
```

### Invoice Status Lifecycle

```
  ┌────────────┐     ┌────────────┐     ┌────────────┐     ┌────────────┐
  │ Processing  │────►│  Review     │────►│  Verified   │────►│  Exported   │
  └────────────┘     └─────┬──────┘     └────────────┘     └────────────┘
                           │
                           ├────► Error (processing failed)
                           │
                           └────► Rejected (user rejected)
```

| Status | Meaning |
|--------|---------|
| **Processing** | System is running OCR, extraction, and validation |
| **Review** | Processing complete. Awaiting user review. |
| **Verified** | User accepted the extracted data. Ready for export. |
| **Exported** | Data has been exported to accounting software. |
| **Error** | Something went wrong during processing. |

---

## 14. Security, Compliance & Audit

### Multi-Tenant Data Isolation

Every query in the system is automatically scoped to the user's organization. There is no way for one organization to access another's data — this is enforced at the database query level, not just the UI level.

### Audit Trail

FakturaAI maintains an immutable (append-only) audit log of every significant action:

| Event Category | Examples |
|----------------|----------|
| **Authentication** | Login, logout, failed login attempts |
| **Invoice Operations** | Upload, view, edit, delete, verify, export |
| **Corrections** | Every field edit with before/after values |
| **Rules** | Rule creation, modification, execution |
| **Administration** | User management, settings changes |

Each log entry records: who (user), what (action), when (timestamp), where (IP address), and the before/after state of affected data.

### Compliance Framework

| Requirement | How FakturaAI Complies |
|-------------|----------------------|
| **ZZPL** (Serbian Data Protection Law) | All data access logged; encryption at rest and in transit; immutable audit trail |
| **Zakon o računovodstvu** (Accounting Law) | 10-year document retention; original documents preserved; full audit export for tax authority |
| **Tax Authority Inspection** | Audit export package with invoice register, originals, and access trail |

### Document Retention

- Original invoice files stored permanently in encrypted cloud storage
- Invoice metadata and extracted data stored in the database indefinitely
- Audit trail preserved for the full 10-year retention period required by Serbian accounting law
- All data encrypted at rest (AES-256) and in transit (TLS 1.3)

---

## 15. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **AI proposes, human approves** | Accountants stay in control. The system is a productivity tool, not a replacement. |
| **100% deterministic rules engine** | Rules must be predictable, auditable, and cost-free. No AI surprises. |
| **Serbian-first design** | Built for Serbian accounting standards, VAT system, PIB format, and legal framework — not a generic tool localized afterward. |
| **Dual-script support** | Serbian businesses use both Cyrillic and Latin. The system handles both natively. |
| **Math verification, not recomputation** | We check if extracted numbers are consistent, not recompute them. This respects real-world rounding that varies between invoices. |
| **Background processing** | Heavy OCR and AI work runs asynchronously. Users never wait for a loading screen. |
| **Pre-built rule templates** | Lower the barrier to entry. New users can set up automation in minutes using templates for common scenarios. |
| **Immutable audit trail** | Every action is logged permanently. Records can never be deleted or modified. Required for compliance and builds trust. |

---

*This document describes FakturaAI through Milestone 6 (Data Export). For detailed technical documentation of specific subsystems, see [AUTOMATION_RULES.md](AUTOMATION_RULES.md) and [SRS.md](SRS.md).*
