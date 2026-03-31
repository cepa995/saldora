## 1. What is Saldora?

Saldora is a web-based invoice processing platform built specifically for the Serbian market. It uses artificial intelligence to automate the manual, time-consuming work of reading invoices, extracting data, verifying correctness, and preparing accounting entries.

**The core promise:** An accountant uploads a stack of invoices. Within seconds, the system reads every invoice, extracts all relevant data (PIB, company names, amounts, line items, VAT), verifies the numbers, suggests the correct accounting entries, and presents everything for a quick review. What used to take hours now takes minutes.

The accountant remains fully in control — the system proposes, the human approves.

---

## 2. High-Level System Overview

The following diagram shows the major components of the Saldora platform and how they connect:

```
┌──────────────────────────────────────────────────────────────┐
│                     Saldora Platform                        │
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
   SEF Portal           dots.ocr            Claude API         NBS API
   (eFaktura)           (VLM OCR)           (Extraction)       (Exchange Rates)
```

**Components at a glance:**

| Component | Role |
|-----------|------|
| **Web App** (Next.js) | What the user sees — upload, review, rules, export |
| **REST API** (FastAPI) | Business logic, authentication, data management |
| **Workers** (Celery) | Background OCR/extraction without blocking the user |
| **PostgreSQL** | All data — invoices, users, rules, audit logs |
| **Document Store** (S3/R2) | Original invoice files (PDFs, images) |
| **External: SEF, dots.ocr, Claude, NBS** | eFaktura portal, OCR engine, AI extraction, exchange rates |

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

1. Opens Saldora in a web browser
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

Serbia's electronic invoicing system (SEF) delivers invoices digitally. Saldora polls the SEF portal periodically and imports new invoices automatically.

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

## 8.4 Exchange Rate Conversion (Non-RSD Invoices)

When an invoice is in a foreign currency (EUR, USD, CHF, GBP), the system automatically converts the total amount to RSD using the NBS (National Bank of Serbia) middle rate.

### How It Works

```
Invoice: EUR 2,000.00  (dated 2026-03-03)
                │
                ▼
    Look up NBS middle rate for EUR on 2026-03-03
                │
    ┌───────────┴───────────────────────────┐
    │  4-tier lookup:                        │
    │  1. Redis cache (fastest)              │
    │  2. Database (exchange_rates table)    │
    │  3. NBS API (kurs.resenje.org)         │
    │  4. Fallback: latest known rate        │
    └───────────┬───────────────────────────┘
                │
                ▼
    Rate: 1 EUR = 117.1234 RSD (NBS srednji kurs)
    Conversion: 2,000.00 × 117.1234 = 234,246.80 RSD
```

### Key Points

- **Rate date = invoice date** — Serbian accounting law requires using the NBS middle rate from the date the invoice was issued, not the current date.
- **Rates cached in Redis** with 24-hour TTL to avoid repeated API calls.
- **Celery Beat** fetches rates for all supported currencies daily at 08:30 on business days (Mon–Fri), pre-populating the database and cache.
- **Audit trail** — the exchange rate, rate date, and RSD equivalent are stored on the invoice record for traceability.
- **Supported currencies:** EUR, USD, CHF, GBP. RSD invoices skip this step entirely.

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

Saldora comes with nine ready-to-use rule templates for common Serbian accounting scenarios. Users can apply a template and customize it rather than building rules from scratch:

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
│                               │                                   │
│                               │  ┌─ RSD ekvivalent ────────────┐ │
│                               │  │ 234.246,80 RSD              │ │
│                               │  │ 1 EUR = 117.1234 RSD        │ │
│                               │  │ NBS srednji kurs (03.03.26) │ │
│                               │  └─────────────────────────────┘ │
│                               │                                   │
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

**Goal:** Get the processed data out of Saldora and into the accountant's existing tools.

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

Saldora provides four system templates and supports custom user-defined templates:

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

For organizations using MiniMax accounting software, Saldora supports direct data push:

```
┌───────────────┐     ┌────────────────┐     ┌──────────────────┐
│  Saldora    │────►│ MiniMax REST   │────►│ MiniMax Software │
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
 User uploads    1. Store in S3                    8. User reviews data
 PDF / image     2. Prepare document               9. Correct errors if needed
      │          3. OCR — dots.ocr VLM            10. Approve invoice
 SEF inbox  ───► 4. AI extraction — Claude LLM   11. Export (XLSX/CSV/JSON/XML)
 import          5. Validate (PIB, math, dupes)   12. MiniMax push (optional)
      │          6. Exchange rate (NBS, non-RSD)   13. Audit export (admin)
 API call        7. Accounting intelligence
                    (type, VAT, konta, rules)
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

Saldora maintains an immutable (append-only) audit log of every significant action:

| Event Category | Examples |
|----------------|----------|
| **Authentication** | Login, logout, failed login attempts |
| **Invoice Operations** | Upload, view, edit, delete, verify, export |
| **Corrections** | Every field edit with before/after values |
| **Rules** | Rule creation, modification, execution |
| **Administration** | User management, settings changes |

Each log entry records: who (user), what (action), when (timestamp), where (IP address), and the before/after state of affected data.

### Compliance Framework

| Requirement | How Saldora Complies |
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

## 15. Client Management (Agency Feature)

**Goal:** Enable accounting agencies to manage multiple client companies within a single organization and automatically associate invoices with the correct client.

Client Management is available exclusively on the Agency plan (€199/mo). Organizations on lower plans receive a 403 error when attempting to access client endpoints.

### 15.1 Client Setup

Agency administrators create client companies via the Clients page. Each client record includes:

| Field | Description |
|-------|-------------|
| **Name** | Client company name |
| **PIB** | Tax identification number (unique within the organization) |
| **MB** | Matični broj (company registration number) |
| **Address** | Street address, city, postal code |
| **Contact info** | Email, phone, contact person |

A client's PIB must be unique within the organization — two clients cannot share the same PIB.

### 15.2 Auto-Assignment

When an invoice is processed through OCR and field extraction, the system automatically attempts to match the invoice to a client:

```
Invoice processed ──► Extract buyer PIB and seller PIB
                              │
                              ▼
                    Check buyer PIB against active clients
                              │
                    ┌─────────┴─────────┐
                    │                   │
                  Match              No match
                    │                   │
                    ▼                   ▼
              Assign client     Check seller PIB against active clients
                                        │
                                ┌───────┴───────┐
                                │               │
                              Match          No match
                                │               │
                                ▼               ▼
                          Assign client    No client assigned
```

**Priority:** Buyer PIB is checked first. If no match is found, seller PIB is checked. This order reflects the typical agency workflow where the agency's clients are usually the buyers on incoming invoices.

### 15.3 Client Context Selector

Agency users see a client selector dropdown in the sidebar. Selecting a client scopes the view:

- **Dashboard statistics** — totals, counts, and charts reflect only the selected client's invoices
- **Invoice list** — filtered to show only invoices assigned to the selected client
- **Clearing the selector** — returns to the organization-wide view showing all invoices

This allows agency staff to quickly switch between client contexts without navigating away from their current page.

### 15.4 Manual Assignment

Users can manually assign or unassign a client to any invoice via the `PATCH /{invoice_id}/client` endpoint:

| Action | Request |
|--------|---------|
| **Assign client** | `PATCH /{invoice_id}/client` with `{ "client_id": "..." }` |
| **Unassign client** | `PATCH /{invoice_id}/client` with `{ "client_id": null }` |

Manual assignment overrides any auto-assignment. This is useful when:
- The auto-assignment matched the wrong client
- An invoice has no extractable PIB but belongs to a known client
- The user wants to reassign an invoice to a different client

### 15.5 Feature Gating

| Plan | Client Management Access |
|------|-------------------------|
| **Starter** (€49/mo) | Not available — 403 Forbidden |
| **Professional** (€99/mo) | Not available — 403 Forbidden |
| **Agency** (€199/mo) | Full access — create clients, auto-assignment, context selector |

Attempting to access any client endpoint (`/clients`, `/{invoice_id}/client`) on a non-agency plan returns a 403 error with a clear message indicating that the feature requires an Agency plan upgrade.

---

## 16. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **AI proposes, human approves** | Accountants stay in control. The system is a productivity tool, not a replacement. |
| **100% deterministic rules engine** | Rules must be predictable, auditable, and cost-free. No AI surprises. |
| **Serbian-first design** | Built for Serbian accounting standards, VAT system, PIB format, and legal framework — not a generic tool localized afterward. |
| **Dual-script support** | Serbian businesses use both Cyrillic and Latin. The system handles both natively. |
| **Math verification, not recomputation** | We check if extracted numbers are consistent, not recompute them. This respects real-world rounding that varies between invoices. |
| **Background processing** | Heavy OCR and AI work runs asynchronously. Users never wait for a loading screen. |
| **Pre-built rule templates** | Lower the barrier to entry. New users can set up automation in minutes using templates for common scenarios. |
| **NBS rate by invoice date** | Foreign currency conversion uses the NBS middle rate from the invoice date, not the current date, as required by Serbian accounting law. Rates are cached and pre-fetched daily. |
| **Immutable audit trail** | Every action is logged permanently. Records can never be deleted or modified. Required for compliance and builds trust. |

---

## 17. Invoice Reports & Procurement Intelligence (Izveštaji)

**Goal:** Give accountants and restaurant/hospitality managers instant analytical views of their invoice data — without any AI calls and at zero LLM cost.

### What Replaces What

The Reports feature replaces the earlier PDV knjige (KPR/KIR) plan. Instead of generating VAT-register exports mapped to PP-PDV form fields, the system provides general-purpose analytical report templates that are more broadly useful across day-to-day accounting work.

The former separate `/katalog` (product catalog) and `/dpu` (daily goods tracking) pages have been consolidated into the unified `/izvestaji` page.

### How the Denormalized Table Works

To make reports fast and query-simple, a separate `invoice_line_items` table mirrors every line item from every processed invoice in a flat, denormalized form. This table is populated at three points in the workflow:

```
OCR completes ──► Line items extracted into invoices.line_items JSON
                          │
                          ▼
                  Worker writes each line item as a row
                  in invoice_line_items table
                  (non-blocking — runs after the main save)

User edits invoice ──► Line items updated in invoices.line_items JSON
                                │
                                ▼
                        invoice_line_items rows
                        deleted and re-inserted
                        for that invoice

User verifies invoice ──► Same sync as on edit
                                │
                                ▼
                        invoice_line_items rows refreshed
```

### Product Catalog

For restaurant and hospitality clients, the `product_catalog` table stores canonical product names with aliases (alternative descriptions from different suppliers), categories, selling prices, and default margins.

When a line item is written to `invoice_line_items`, the system attempts to match its description to a catalog entry using PostgreSQL trigram similarity (`pg_trgm`). On a successful match the `product_id` FK is set, enabling the procurement intelligence reports.

```
Line item written ──► pg_trgm fuzzy match against product_catalog
                              │
                    ┌─────────┴─────────┐
                    │                   │
               Match (≥0.6)         No match
                    │                   │
                    ▼                   ▼
              product_id FK set    product_id = NULL
              match_count++        (item remains unlinked)
```

### Report Templates

All reports live under `/api/v1/reports/`. The `/izvestaji` page organizes them into three groups:

#### Group: Opšti (General Reports)

| Report | URL | What It Shows |
|--------|-----|---------------|
| **Pregled primljene robe** | `/received-goods` | Line items grouped by description; sums quantity and total; all suppliers per item |
| **Troškovi po dobavljaču** | `/spending-by-supplier` | Total amount spent per supplier over the selected period |
| **Mesečni pregled stavki** | `/monthly-breakdown` | Paginated flat list of all line items for a selected date range |
| **Poređenje cena** | `/price-comparison` | Items from multiple suppliers with min/max/avg unit price |
| **Pregled troškova** | `/expense-summary` | Expense totals grouped by month or week |

#### Group: Nabavka i prodaja (Procurement & Sales)

| Report | URL | What It Shows |
|--------|-----|---------------|
| **Kalkulacija** | `/kalkulacija` | Purchase price, margin %, and calculated selling price per line item |
| **RUC** | `/ruc` | Razlika u ceni — markup analysis grouped by canonical product |
| **Troškovi po kategoriji** | `/spending-by-category` | Total spending grouped by product catalog category |
| **Dnevna evidencija robe** | `/dpu` | All goods received on a specific date |

#### Group: Upravljanje (Management)

Product catalog management — add/edit canonical products, manage aliases, review merge suggestions for likely-duplicate entries.

### How the User Navigates Reports

```
User opens Izveštaji page
        │
        ▼
Selects a group (Opšti / Nabavka i prodaja / Upravljanje)
        │
        ▼
Clicks a tab within the group
        │
        ▼
Sets filters: date range, optional supplier, optional keyword, optional client (Agency plan)
        │
        ▼
Results table loads instantly (SQL aggregation — no AI)
        │
        ▼
User reviews data in-page or clicks "Izvezi CSV"
        │
        ▼
CSV file downloads with Serbian locale formatting
(semicolon delimiter, comma decimal separator, UTF-8 BOM)
```

### Zero Cost, Instant Results

Unlike invoice processing (which uses the OCR engine and Claude LLM), reports involve no AI calls whatsoever. Every report is a single SQL query over the `invoice_line_items` table (joined with `product_catalog` where needed). Response times are typically under 200 ms for organizations with tens of thousands of line items.

### Feature Gate

Reports are a PRO plan feature. Starter-plan users see an upgrade prompt when they navigate to the Izveštaji page.

---

*This document describes Saldora through the Procurement Intelligence feature (Milestone 16). For detailed technical documentation of specific subsystems, see [AUTOMATION_RULES.md](AUTOMATION_RULES.md) and [SRS.md](SRS.md).*
