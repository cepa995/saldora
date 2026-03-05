# FakturaAI — Implementation Guide

**Reference:** [SRS.md](SRS.md)
**Date:** 2026-02-25

---

## Overview

This guide breaks the FakturaAI SRS into **9 milestones** with concrete issues for each. Milestones are ordered by dependency — each builds on the previous. Issues within a milestone can often be parallelized.

> **Note:** Line items and tax groups are stored as JSON within the invoice record (not separate relational tables) for schema flexibility during the OCR extraction phase. Seller/buyer data is also stored as inline JSON rather than FK references to a companies table. This is an intentional design decision — invoices from different formats have varying structures, and JSON columns accommodate this without schema migrations.

### Milestone Map

```
M1: Foundation & Authentication [COMPLETED]
 │
 ├──► M2: Document Storage & Upload
 │     │
 │     └──► M3: OCR Processing Pipeline
 │           │
 │           ├──► M4: Invoice Management & Verification
 │           │     │
 │           │     ├──► M5: Accounting Intelligence & Rules Engine
 │           │     │
 │           │     └──► M6: Data Export
 │           │
 │           └──► M7: External Integrations (SEF, NBS, Paddle)
 │
 ├──► M8: Frontend Application (can start after M1, iterates with backend milestones)
 │
 ├──► M9: CI/CD, Security & Production
 │
 └──► M10: Multi-Country Tax ID Validation (after M3+M4, before production launch)
```

### Requirement Coverage

Each issue references the SRS requirements it satisfies (e.g., `FR-4.2.1`). When all issues across all milestones are complete, every requirement in the SRS is covered.

---

## Milestone 1: Foundation & Authentication [COMPLETED]

**Goal:** API starts, connects to PostgreSQL and Redis, creates tables, shuts down cleanly. Users can register, login, and receive JWT tokens.

This milestone is complete. It established the database module, core models (User, Organization, Invoice), lifespan management, JWT authentication, password hashing (Argon2), auth endpoints (register/login), and the test infrastructure (conftest.py, unit tests, API tests).

**What was delivered:**
- Database module with async SQLAlchemy engine and session factory
- Base model with UUID and Timestamp mixins
- Core models: User, Organization, Invoice
- Application lifespan (startup/shutdown)
- Alembic migrations
- Auth endpoints: POST `/api/v1/auth/register`, POST `/api/v1/auth/login`
- Password hashing (Argon2) and JWT token creation/validation
- Auth dependency injection (`get_current_user`)
- Test infrastructure: separate test DB, session fixtures, HTTP client
- Unit tests (password hashing, JWT tokens) and API tests (register, login, protected endpoints)
- Frontend auth pages (login, register, password-reset), auth context, middleware

---

## Milestone 2: Document Storage & Upload

**Goal:** Users can upload invoice documents (single and batch). Files are stored in S3-compatible storage, database records are created, and Celery tasks are queued for processing.

### Issues

#### 2.1 — Implement S3-compatible storage service

**Description:** Create a storage abstraction over S3/MinIO so the rest of the app doesn't care which provider is used. Support upload, download (presigned URLs), and deletion.

**Requirements covered:** FR-4.2.1, FR-4.2.2, Section 10.4

**Tasks:**
- Create `apps/api/app/services/storage.py` with lazy-initialized boto3 client
- Implement `upload_document(organization_id, invoice_id, content, content_type, filename)` — organizes files as `organizations/{org_id}/invoices/{id}/original.{ext}`
- Implement `get_presigned_url(key, expires_in)` for secure temporary download links
- Implement `delete_document(key)` for cleanup on invoice deletion
- Add storage config to `apps/api/app/config.py`: `storage_endpoint`, `storage_bucket`, `storage_access_key`, `storage_secret_key`, `storage_region`
- Verify MinIO is reachable via Docker Compose health check

**Acceptance:** `upload_document()` stores a file in MinIO. `get_presigned_url()` returns a URL that downloads the file. `delete_document()` removes it.

---

#### 2.2 — Implement single invoice upload endpoint

**Description:** Wire the upload endpoint to validate files, create a database record, store the file in S3, and queue a Celery task for OCR processing.

**Requirements covered:** FR-4.2.1, FR-4.2.3, FR-4.2.4, Section 9.3

**Tasks:**
- Implement POST `/api/v1/invoices/upload` in `apps/api/app/routers/invoices.py`:
  - Accept `multipart/form-data` with file, optional `priority` and `callback_url`
  - Validate file type against `ocr_supported_formats` (PDF, JPEG, PNG, TIFF, BMP, WEBP)
  - Validate file size against `ocr_max_file_size_mb` (20 MB)
  - Create `Document` record with original filename, MIME type, size
  - Create `Invoice` record in `processing` status, linked to document
  - Upload file to S3 via storage service
  - Queue Celery task `process_invoice` with invoice ID and document path
  - Return 202 Accepted with `ProcessingStatus` response
- Create `apps/api/app/models/document.py` matching Section 8.2.5 schema
- Create Pydantic schemas for `ProcessingStatus` response

**Acceptance:** Upload a PDF via curl → 202 response with invoice ID. File visible in MinIO. Invoice record exists in database with status `processing`.

---

#### 2.3 — Implement batch upload endpoint

**Description:** Allow uploading up to 50 files in a single request, each queued independently for processing.

**Requirements covered:** FR-4.2.2, Section 9.3

**Tasks:**
- Implement POST `/api/v1/invoices/upload/batch` in `apps/api/app/routers/invoices.py`:
  - Accept multiple files (max 50 files, max 200 MB total)
  - Validate each file individually (type, size)
  - Create document + invoice records for each valid file
  - Upload each to S3, queue each as separate Celery task
  - Return list of `ProcessingStatus` objects (one per file)
  - Include per-file error details for rejected files (don't fail the entire batch)

**Acceptance:** Upload 5 PDFs in one request → 202 response with 5 status objects. Each file stored separately in MinIO.

---

#### 2.4 — Write tests for storage and upload

**Description:** Unit tests for storage utilities, integration tests for upload endpoints with mocked S3.

**Tasks:**
- Unit test `_get_extension()` for all MIME types including unknown fallback
- Integration test: single upload creates invoice + document records (mock S3 client)
- Integration test: batch upload with mix of valid and invalid files
- Integration test: upload rejects files exceeding size limit (422)
- Integration test: upload rejects unsupported file types (422)
- Integration test: upload requires authentication (401 without token)

**Acceptance:** All tests pass. S3 is mocked — tests don't require MinIO running.

---

## Milestone 3: OCR Processing Pipeline

**Goal:** The Celery worker picks up queued tasks, preprocesses images, runs OCR (dots.ocr via vLLM server), extracts structured fields, calculates confidence scores, and saves results to the database. The API returns processing status with real-time Redis-based progress.

### Issues

#### 3.1 — Implement image preprocessing module

**Description:** Build the preprocessing pipeline that normalizes invoice images before OCR: deskewing, denoising, binarization, contrast enhancement, and resolution scaling.

**Requirements covered:** FR-4.3.1, Section 4.3.2

**Tasks:**
- Implement `InvoicePreprocessor` in `packages/ml/fakturaai_ml/preprocessing/image.py`:
  - Deskewing via OpenCV Hough transform
  - Denoising via OpenCV fastNlMeansDenoising
  - Binarization via Otsu's method
  - Contrast enhancement via CLAHE
  - Resolution normalization to 300 DPI
  - Border/scanner artifact removal
- Implement PDF-to-image conversion in `packages/ml/fakturaai_ml/preprocessing/pdf.py` using PyMuPDF
- Handle multi-page PDFs (split into per-page images)
- Write unit tests for each preprocessing step with sample images

**Acceptance:** A skewed, noisy scan is corrected and produces cleaner OCR output. Multi-page PDF splits into individual images.

---

#### 3.2 — Integrate dots.ocr as primary OCR engine

**Description:** Implement the dots.ocr VLM engine wrapper that connects to a vLLM server running dots.ocr and calls it via the OpenAI-compatible chat completions API (the official approach from the dots.ocr project).

**Requirements covered:** FR-4.3.1, FR-4.3.3 (layout analysis), Section 3.4, Section 4.3.7

**Architecture:** dots.ocr runs as a separate vLLM server (`vllm/vllm-openai` Docker image) with GPU access. The worker calls it over HTTP via the `openai` Python client. This follows the official `demo_vllm.py` pattern from the dots.ocr repo.

**Tasks:**
- Implement `DotsOCREngine` in `packages/ml/fakturaai_ml/ocr/dots_ocr.py`:
  - Connect to vLLM server via OpenAI-compatible API (`DOTS_OCR_SERVER_URL` env var)
  - Send images as base64 data URIs with the official prompt format (includes `<|img|><|imgpad|><|endofimg|>` tokens)
  - Accept raw color image (no preprocessing — VLMs work best with originals), return text/structured output
  - Support Cyrillic and Latin script recognition (100+ languages)
- Add `dots-ocr-server` service to `docker-compose.yml`:
  - Uses `vllm/vllm-openai:latest` image with GPU reservation
  - Launches with `--chat-template-content-format string --trust-remote-code`
  - Model weights cached in `huggingface_cache` Docker volume
  - Health check on `/health` endpoint (5-min start period for model loading)
- Define `OCRResult` dataclass with regions, reading order, full text, overall confidence
- Handle server unavailability gracefully (log error, return empty result for manual review)

**Acceptance:** Feed a sample Serbian invoice image → receive structured output with extracted text, layout regions, and confidence scores.

---

#### 3.3 — Fallback handling when OCR fails

**Description:** When dots.ocr returns low confidence or the vLLM server is unavailable, the invoice is saved with status `review` for manual data entry by the user. EasyOCR was evaluated but dropped due to poor Serbian Cyrillic support and low extraction quality.

**Requirements covered:** FR-4.3.1, Section 3.4 (fallback path), Section 4.3.7

**Tasks:**
- Set `OCR_FALLBACK_ENGINE=none` in docker-compose (EasyOCR disabled)
- When dots.ocr fails or returns low confidence, save invoice with status `review` and empty fields
- Record `ocr_engine` field in the result to track which engine was used
- User manually fills in fields via the review UI

**Acceptance:** When dots.ocr fails, the invoice is saved for manual review. No cascading fallback to a second OCR engine.

---

#### 3.4 — Implement field extraction from OCR output

**Description:** Extract structured invoice fields (PIB, dates, amounts, invoice number, seller/buyer info, line items, tax groups) from raw OCR text. Uses a dual-extractor architecture: LLM-based extraction as primary method (Anthropic Claude), with regex pattern matching as fallback.

**Requirements covered:** FR-4.3.2, Section 4.3.4, Section 4.3.5

**Architecture:** The LLM receives the complete raw OCR text and a structured JSON schema prompt, returning all fields in a single API call. This approach handles the diversity of Serbian invoice formats far more robustly than hand-crafted regex patterns. The regex `FieldExtractor` serves as fallback when the LLM is unavailable.

**Tasks:**
- Implement `LLMFieldExtractor` in `packages/ml/fakturaai_ml/extraction/llm_extractor.py` (PRIMARY):
  - Send raw OCR text to Anthropic Claude API with structured JSON schema prompt
  - Extract all fields in a single LLM call: seller/buyer (PIB, MB, name, address, city, postal_code), invoice number, dates, amounts, currency, line items, tax groups
  - Extract `tax_groups` as per-PDV-section breakdown: each printed PDV row becomes one entry with rate, base_amount, tax_amount — groups are NOT merged even when they share the same rate
  - Parse and validate LLM JSON response
  - Configurable model via `ANTHROPIC_MODEL` env var (default: `claude-haiku-4-5-20251001`)
  - Requires `ANTHROPIC_API_KEY` env var
- Implement `FieldExtractor` in `packages/ml/fakturaai_ml/extraction/fields.py` (FALLBACK):
  - PIB extraction (9-digit patterns, both `PIB:` and `ПИБ:` prefixes)
  - MB extraction (8-digit matični broj)
  - Invoice number, date, amount, currency, VAT rate extraction via regex
  - Company name and address extraction
- Implement PIB validation in `packages/ml/fakturaai_ml/validation/pib.py`:
  - 9-digit format check, no leading zero, mod-11 weighted checksum
  - Runs as part of the ML pipeline (not as a separate API service)
- Implement math validation in `packages/ml/fakturaai_ml/validation/math_check.py`:
  - Line items sum ≈ subtotal, subtotal + tax ≈ total, line item math (qty * price ≈ total)
  - Tax groups consistency: sum of group base_amounts ≈ subtotal, sum of group tax_amounts ≈ tax_amount
  - Tiered tolerance by amount range (Section 4.9.5)
  - Design decision: tax amount is NOT recomputed from subtotal * rate
- Implement per-field confidence scoring in `packages/ml/fakturaai_ml/postprocessing/confidence.py`
- Write tests with sample OCR outputs covering Cyrillic, Latin, and mixed-script invoices

**Acceptance:** Given OCR text from a Serbian invoice, all required fields are extracted with per-field confidence scores. LLM extraction is primary; regex is fallback. Tax groups preserve per-section PDV breakdowns.

---

#### 3.5 — Connect Celery worker to database and pipeline

**Description:** Wire the Celery `process_invoice` task to download the document from S3, run it through the ML pipeline, and save extraction results to the database.

**Requirements covered:** FR-4.3.1, Section 3.3 (data flow)

**Tasks:**
- Implement `_save_extraction_result()` in `workers/ocr_worker/tasks.py`:
  - Use synchronous SQLAlchemy engine (psycopg2, not asyncpg — Celery tasks are sync)
  - Map extraction result fields to Invoice model columns
  - Store `raw_ocr_text`, `raw_llm_output`, `field_confidences`, `warnings`, `ocr_engine`, `processing_time_ms`, `tax_groups`
  - Update invoice status to `review` on success, `error` on failure
  - Pipeline configuration: `use_llm` (bool), `llm_api_key`, `llm_model` parameters
- Implement `_update_invoice_status()` for status transitions
- Implement `_download_document()` to fetch file from S3 for processing
- Handle errors: update invoice status to `error`, store error details in `warnings` JSON
- Send webhook callback if `callback_url` was provided
- Implement `process_batch` task that orchestrates multiple `process_invoice` calls

**Acceptance:** Upload a file → Celery picks up the task → OCR runs → invoice record updated with extracted data and status `review`. Error cases produce status `error` with details.

---

#### 3.6 — Implement processing status polling

**Description:** Allow the frontend to poll for processing progress and status updates.

**Requirements covered:** FR-4.2.2 (progress), Section 9.3

**Tasks:**
- Implement GET `/api/v1/invoices/{id}/status` in `apps/api/app/routers/invoices.py`:
  - Return current status, progress percentage, estimated time remaining
  - For batch uploads, return per-invoice status
- Use Redis to store progress updates from the worker (write) and serve them via API (read)
- Worker publishes progress: `preprocessing` → `ocr_running` → `extracting_fields` → `validating` → `complete`

**Acceptance:** After upload, polling `/status` shows progress updates. Final poll returns `review` status with extracted data summary.

---

#### 3.7 — Write tests for OCR pipeline

**Description:** Unit and integration tests for the processing pipeline end-to-end.

**Tasks:**
- Unit test each preprocessing step (deskew, denoise, binarize)
- Unit test field extraction with sample OCR text (Cyrillic and Latin)
- Unit test confidence scoring calculation
- Unit test PIB extraction for various formats
- Unit test date parsing for all Serbian date formats
- Unit test amount parsing for Serbian number format (`45.000,00`)
- Integration test: mock OCR engine → field extraction → confidence scoring → result
- Test fallback logic: low-confidence dots.ocr saves invoice for manual review
- Test worker task saves results to database correctly

**Acceptance:** All tests pass. Pipeline coverage includes both happy paths and edge cases.

---

## Milestone 4: Invoice Management & Verification

**Goal:** Full invoice CRUD with filtering, pagination, and search. PIB verification against APR. Mathematical verification. Duplicate detection. Correction logging for quality monitoring.

### Issues

#### 4.1 — Implement invoice list endpoint with filtering and pagination

**Description:** Build the invoice listing API with support for status filtering, date ranges, PIB filtering, full-text search, sorting, and cursor-based pagination.

**Requirements covered:** FR-4.7.3, Section 9.3 (GET /invoices)

**Tasks:**
- Implement GET `/api/v1/invoices` in `apps/api/app/routers/invoices.py`:
  - Query parameters: `page`, `per_page` (max 100), `status`, `date_from`, `date_to`, `seller_pib`, `buyer_pib`, `search`, `sort`, `order`
  - Multi-tenant: always filter by `organization_id` from authenticated user
  - Full-text search via PostgreSQL `to_tsvector` on invoice number, seller/buyer name
  - Return paginated response: `{ data: [...], pagination: { page, per_page, total, total_pages } }`
- Implement GET `/api/v1/invoices/{id}` with full invoice details including document download URL
- Create Pydantic response schemas matching Section 9.3 response format

**Acceptance:** Authenticated user retrieves paginated invoice list. Filters narrow results correctly. User cannot see other organizations' invoices.

---

#### 4.2 — Implement invoice update and delete

**Description:** Allow users to edit extracted fields (manual corrections) and delete invoices with document cleanup.

**Requirements covered:** FR-4.5.2, Section 9.3 (PATCH, DELETE)

**Tasks:**
- Implement PATCH `/api/v1/invoices/{id}`:
  - Accept partial updates to any extracted field
  - Validate updated fields (date formats, PIB format, numeric amounts)
  - Recalculate confidence score after manual edits (set to 1.0 for manually verified fields)
  - Log corrections (see issue 4.5)
- Implement DELETE `/api/v1/invoices/{id}`:
  - Delete invoice record, associated document record
  - Delete file from S3 storage
  - Require `admin` or `manager` role
- Implement POST `/api/v1/invoices/{id}/verify`:
  - Set status to `verified`, record who verified and when

**Acceptance:** User edits an extracted field → field updated, correction logged. Admin deletes invoice → record and S3 file removed.

---

#### 4.3 — Implement APR PIB verification service

**Description:** Build the APR integration service to verify Serbian PIB numbers against the Business Registers Agency database. Cache responses for 24 hours.

**Note:** PIB format validation (9 digits, no leading zero, mod-11 checksum) is already implemented in the ML pipeline (`packages/ml/fakturaai_ml/validation/pib.py`) and runs during extraction. This issue covers the remaining APR API integration work.

**Requirements covered:** FR-4.4.1, Section 10.1, Section 4.4.1

**Tasks:**
- Create `apps/api/app/services/apr.py`:
  - `verify_pib(pib: str) -> APRVerificationResult` — call APR API, return company info + status
  - ~~PIB format validation: exactly 9 digits, doesn't start with 0, mod-11 checksum~~ (already in ML pipeline)
  - Cache successful responses in Redis for 24 hours
  - Handle APR unavailability gracefully (return `APR_UNAVAILABLE` status, allow manual override)
- Create `apps/api/app/models/company.py` matching Section 8.2.4 schema
- Implement GET `/api/v1/verify/pib/{pib}` endpoint (Section 9.5)
- Upsert company records on verification (store APR data for future lookups)
- Apply PIB validation outcome rules from Section 4.4.1:
  - `AKTIVAN` → auto-approve
  - `BRISAN` / `U LIKVIDACIJI` / `STEČAJ` → flag for review
  - Not found → flag for review
  - Invalid format → block export
- Implement same seller/buyer detection (Section 4.4.1)

**Acceptance:** Valid active PIB returns company info from APR. Invalid PIB returns format error. APR down → warning, not failure. Results cached in Redis.

---

#### 4.4 — Implement mathematical and business rule verification

**Description:** Verify invoice calculations (line items sum, tax calculation, total) and apply date/currency validation rules.

**Note:** Core math validation is already implemented in the ML pipeline (`packages/ml/fakturaai_ml/validation/math_check.py`) and runs during extraction. Completed checks: line items sum ≈ subtotal, subtotal + tax ≈ total, line item math (qty * price ≈ total), tax groups consistency. This issue covers the remaining verification work not yet in the pipeline.

**Requirements covered:** FR-4.4.2, FR-4.4.3, Section 4.4.2, 4.4.3, 4.4.4, 4.4.5, 4.4.6

**Tasks:**
- ~~`verify_calculations(invoice)` — check line items sum to subtotal, tax calculation, total = subtotal + tax~~ (already in ML pipeline)
- ~~Apply tolerance rules per amount range (Section 4.4.3)~~ (already in ML pipeline)
- ~~Multi-rate invoice handling~~ (already via `tax_groups` in ML pipeline)
- Remaining work in `apps/api/app/services/verification.py`:
  - VAT rate validation: only 0%, 10%, 20% are valid Serbian rates
  - Date validation: future invoice date, due date before invoice date, very old invoices
  - Currency validation: detect mixed currencies, validate currency code
  - Duplicate detection: same invoice number + seller PIB + date
  - Apply export blocking rules (Section 4.4.7): block if PIB invalid, required fields missing, math fails, or unreviewed warnings

**Acceptance:** Invoice with wrong total → warning flagged. Duplicate invoice → user warned. Invalid VAT rate → flagged for review. Export blocked for unresolved critical issues.

---

#### 4.5 — Implement correction logging for quality monitoring

**Description:** Log every human correction to extracted data for quality monitoring and analytics.

**Requirements covered:** FR-4.3.8, Section 4.3.8, Section 8.4

**Tasks:**
- Create `apps/api/app/models/correction_log.py` matching Section 8.4.1 schema
- When PATCH `/invoices/{id}` modifies a field, create a `correction_log` entry:
  - Record `field_name`, `original_value`, `corrected_value`, `model_confidence`, `correction_type`
- Implement GET `/api/v1/analytics/corrections` for quality dashboard data:
  - Field error rate (% of invoices requiring correction per field)
  - High confidence errors (corrections where model confidence > 90%)
  - Repeat error patterns

**Acceptance:** Edit an invoice field → correction log entry created. Analytics endpoint returns error rates per field.

---

#### 4.6 — Write tests for invoice management and verification

**Description:** Tests for CRUD operations, APR verification, mathematical checks, and correction logging.

**Tasks:**
- Test invoice list with pagination, filtering, and multi-tenancy isolation
- Test invoice update creates correction log
- Test invoice delete removes S3 file (mock S3)
- Test PIB format validation (valid, invalid, mod-11 check)
- Test APR verification with mocked API responses (active, inactive, not found, unavailable)
- Test mathematical verification (correct totals, wrong totals, tolerance edges)
- Test duplicate detection
- Test export blocking rules
- Test correction logging creates entries with correct field values

**Acceptance:** All tests pass. APR is mocked — tests don't require external API.

---

#### 4.7 — Implement audit logging middleware

**Description:** Create the `audit_logs` table and middleware that records all data mutations, authentication events, and administrative actions for compliance and forensics.

**Requirements covered:** Section 5.4.5, Section 8.1 (audit_logs ERD)

**Tasks:**
- Create `apps/api/app/models/audit_log.py` matching the SRS ERD: `id`, `organization_id`, `user_id`, `action`, `entity_type`, `entity_id`, `old_values`, `new_values`, `ip_address`, `user_agent`, `created_at`
- Create audit logging middleware/service:
  - Log authentication events (login success, login failure, logout, token refresh)
  - Log data mutations (create, update, delete on invoices, rules, settings)
  - Log administrative actions (team changes, role assignments, API key operations)
  - Capture `ip_address` and `user_agent` from request headers
  - Store `old_values` and `new_values` as JSONB for change tracking
- Write audit entries asynchronously (don't block API responses)
- Audit log retention: 12 months minimum (7 years for invoice-related actions)
- Add GET `/api/v1/audit-logs` endpoint (admin only, filterable by entity, user, date range)

**Acceptance:** Edit an invoice → audit log entry created with old and new values. Login → auth event logged. Admin can query audit trail.

---

## Milestone 5: Accounting Intelligence & Rules Engine

**Goal:** Transform FakturaAI from an "OCR tool" into an "accounting intelligence platform." Classify documents, determine VAT treatment, suggest konta, map to PDV books, and apply organization-specific automation rules.

### Issues

#### 5.1 — Implement AccountingIntent generation pipeline

**Description:** Build the five-step pipeline that generates an AccountingIntent from extracted invoice data: document classification → transaction type detection → VAT treatment decision → konta suggestion → review flag decision.

**Requirements covered:** FR-4.5.1 through 4.5.5, Section 7.3

**Tasks:**
- Create `apps/api/app/models/accounting_intent.py` matching Section 8.3.1 schema
- Create `apps/api/app/services/accounting_intent.py` with the generation pipeline:
  - **Step 1: Document Classification** — analyze seller/buyer PIB relationship to organization, detect credit notes, advance invoices, proformas (Section 4.5.2 document types)
  - **Step 2: Transaction Type Detection** — check for foreign PIB, EU VAT numbers, reverse charge indicators (Section 4.5.2 transaction types)
  - **Step 3: VAT Treatment Decision** — apply deductibility rules, check non-deductible expense categories, calculate partial deductions (Section 4.5.2 VAT treatments, Section 4.5.6)
  - **Step 4: Konta Suggestion** — match line item descriptions to expense categories, check supplier history, generate balanced debit/credit entries (Section 4.5.3)
  - **Step 5: Review Flag Decision** — flag if confidence < 80%, unusual transaction type, new konta, amount exceeds threshold
- Non-deductible expense detection using keyword patterns (Section 4.5.6): reprezentacija, gorivo, zabava
- Generate AccountingIntent automatically after invoice verification
- Store `applied_rules` and `review_reasons` in the intent record

**Acceptance:** Process an input invoice → AccountingIntent created with correct document type, VAT treatment, suggested konta, and PDV book entries.

---

#### 5.2 — Implement PDV book mapping (KPR/KIR)

**Description:** Map invoice data to correct PDV book entries for KPR (received invoices) and KIR (issued invoices), with PP-PDV field mappings.

**Requirements covered:** FR-4.5.4, Section 7.4

**Tasks:**
- Implement `generate_pdv_book_entries(invoice, accounting_intent)` in accounting intent service:
  - Determine book type: KPR for input invoices, KIR for output invoices
  - Map VAT breakdown to PP-PDV fields (Polje 3, 4, 6, 8, 8a, 9 etc.)
  - Calculate per-rate base and tax amounts
  - Generate sequential entry numbers per organization and period
- Store `pdv_book_entries` JSON in the AccountingIntent record
- Support multi-rate invoices (items at 20%, 10%, and 0% in the same invoice)

**Acceptance:** Input invoice with 20% VAT → KPR entry with correct Polje 8 values. Output invoice → KIR entry. Multi-rate invoice splits correctly.

---

#### 5.3 — Implement automation rules engine

**Description:** Build the rules engine that evaluates organization-specific rules against invoices and modifies AccountingIntents accordingly.

**Requirements covered:** FR-4.6.1 through 4.6.7, Section 7.5, Section 8.3.2, 8.3.3

**Tasks:**
- Create `apps/api/app/models/automation_rule.py` matching Section 8.3.2 schema
- Create `apps/api/app/models/rule_execution.py` matching Section 8.3.3 schema
- Create `apps/api/app/services/rules_engine.py`:
  - `evaluate_rules(invoice, accounting_intent, organization_id)` — load active rules, evaluate conditions, apply actions
  - Implement condition evaluation: all operators from Section 4.6.3 (`equals`, `contains`, `regex`, `greater_than`, `between`, `in`, etc.)
  - Support nested AND/OR logical operators
  - Support `line_items[].description` array field matching
  - Implement actions: `SET_KONTO`, `SET_VAT_TREATMENT`, `FLAG_REVIEW`, `AUTO_APPROVE`, `SET_CUSTOM_FIELD` (Section 4.6.4)
  - Conflict resolution: priority order, `FLAG_FOR_REVIEW` overrides `AUTO_APPROVE`, last matching konto/VAT rule wins (Section 4.6.6)
  - Log each rule execution in `rule_executions` table
- Create CRUD API for automation rules:
  - POST `/api/v1/rules` — create rule
  - GET `/api/v1/rules` — list organization rules
  - PATCH `/api/v1/rules/{id}` — update rule
  - DELETE `/api/v1/rules/{id}` — delete rule
- Provide pre-built rule templates for common Serbian scenarios (Section 4.6.7)

**Acceptance:** Create a rule "Telekom invoices → konto 5210". Upload a Telekom invoice → rule matches, konto set automatically. Rule execution logged.

---

#### 5.4 — Write tests for accounting intelligence and rules

**Description:** Tests for AccountingIntent generation, PDV mapping, and rules engine.

**Tasks:**
- Test document classification (input vs output invoice, credit notes, advance invoices)
- Test transaction type detection (domestic, foreign, reverse charge)
- Test VAT treatment assignment (fully deductible, non-deductible fuel, partial reprezentacija)
- Test konta suggestion for common scenarios
- Test KPR/KIR PDV book entry generation
- Test multi-rate invoice PDV mapping
- Test rules engine condition evaluation for all operator types
- Test nested AND/OR conditions
- Test conflict resolution (FLAG_FOR_REVIEW overrides AUTO_APPROVE)
- Test rule execution logging
- Test rule CRUD API

**Acceptance:** All tests pass. Complete coverage of document types, VAT treatments, and rule evaluation paths.

---

## Milestone 6: Data Export

**Goal:** Export verified invoice data to XLSX, CSV, and JSON formats. Support custom templates and field mapping. Implement audit export for Serbian tax inspections.

### Issues

#### 6.1 — Implement XLSX export

**Description:** Generate Excel exports with formatted headers, multiple sheets, and data validation.

**Requirements covered:** FR-4.6.1, Section 9.4

**Tasks:**
- Create `apps/api/app/services/export.py`:
  - `generate_xlsx(invoices, template, options)` — produce XLSX file
  - Main sheet: one row per invoice with all core fields
  - Line items sheet: detailed line items linked to invoices
  - Accounting sheet: konta assignments and VAT summary
  - Apply Serbian number formatting (`45.000,00`)
  - Apply date formatting (`DD.MM.YYYY` per Serbian convention)
  - Add header row styling and column auto-width
- Implement POST `/api/v1/export` endpoint:
  - Accept `format`, `invoice_ids`, `template_id`, `options`
  - Generate file, upload to S3 exports bucket
  - Return presigned download URL with expiration (30 days auto-delete per Section 10.4)

**Acceptance:** Export 10 invoices → downloadable XLSX with correct formatting, Serbian number/date formats, and line items sheet.

---

#### 6.2 — Implement CSV and JSON exports

**Description:** Generate CSV exports (UTF-8 with BOM, configurable delimiter) and JSON exports (flat or nested structure).

**Requirements covered:** FR-4.6.2, FR-4.6.3, Section 9.4

**Tasks:**
- Add CSV generation to export service:
  - UTF-8 with BOM for Excel compatibility
  - Configurable delimiter (comma, semicolon, tab)
  - Same field set as XLSX
- Add JSON generation to export service:
  - Flat mode: one JSON object per invoice
  - Nested mode: includes line items, accounting intent, verification results
- Wire both formats to POST `/api/v1/export` endpoint

**Acceptance:** CSV opens correctly in Excel (Serbian characters preserved). JSON validates against expected schema.

---

#### 6.3 — Implement custom export templates and field mapping

**Description:** Allow organizations to define custom export templates with field selection, ordering, renaming, and formatting.

**Requirements covered:** FR-4.6.4

**Tasks:**
- Implement GET `/api/v1/export/templates` — list available templates (default + custom)
- Create default template with all standard fields
- Allow custom templates: selected fields, custom column names, field ordering, date/number format overrides
- Store custom templates per organization in the database
- Apply export blocking rules (Section 4.4.7): reject export if required fields missing, unresolved warnings, or confidence < 60% without manual verification

**Acceptance:** Create a custom template with 5 fields → export uses only those fields in specified order.

---

#### 6.4 — Implement audit export for tax inspections

**Description:** Generate comprehensive data exports for Serbian tax authority (Poreska Uprava) inspections.

**Requirements covered:** Section 13.6, Section 8.6.3, Section 11.7

**Tasks:**
- Create `apps/api/app/models/audit_export.py` matching Section 8.6.3 schema
- Implement POST `/api/v1/export/audit`:
  - Accept date range, content selection (invoice register XML, original PDFs, audit trail CSV, VAT summary Excel)
  - Generate eFaktura-compatible XML (Section 13.6 format)
  - Bundle original uploaded documents (PDFs)
  - Generate audit trail (all actions on invoices in period)
  - Generate PDV summary (VAT breakdown by rate and period)
  - Package everything into a ZIP archive
  - Log the export in `audit_exports` table (this export is itself an auditable event)
  - Require `admin` role
- Set export expiration (downloadable for 30 days)

**Acceptance:** Admin generates audit export for 2024 → ZIP file contains XML register, PDFs, audit trail CSV, and VAT summary Excel. Export logged.

---

#### 6.5 — Implement MiniMax XML export

**Description:** Generate MiniMax-compatible XML files for import into MiniMax accounting software (minimax.rs).

**Requirements covered:** FR-4.6.5, Section 12.5

**Tasks:**
- Create `apps/api/app/services/export/minimax_xml.py`:
  - `generate_minimax_xml(invoices)` — produce XML with Stranke + Temeljnice structure
  - Stranke: deduplicated sellers by PIB (Sifra, Naziv, DavcnaStevilka, Naslov, Posta)
  - Temeljnice: journal entries from accounting_intent (konto codes, debit/credit amounts, VAT entries)
  - Uses `xml.etree.ElementTree` (stdlib)
- Add `minimax_xml` format option to POST `/api/v1/export` endpoint
- Add validation: require verified invoices (with accounting_intent) for MiniMax XML export

**Acceptance:** Export 5 verified invoices → valid MiniMax XML with Stranke + Temeljnice. Unverified invoices show clear error.

---

#### 6.6 — Implement MiniMax REST API integration

**Description:** Direct push of invoices to MiniMax via REST API. Includes OAuth2 authentication, customer management, and per-organization configuration.

**Requirements covered:** FR-4.6.6, Section 12.5

**Tasks:**
- Create `apps/api/app/services/minimax/client.py`:
  - OAuth2 token management with auto-refresh
  - `push_received_invoice(data)` — create received invoice in MiniMax
  - `find_or_create_customer(pib, name, address, city)` — customer lookup/creation by PIB
  - `get_currency(code)` — currency ID lookup
- Create `apps/api/app/services/minimax/mapper.py`:
  - `map_invoice_to_received(invoice, customer_id, currency_id)` — map FakturaAI fields to MiniMax schema
- Create `apps/api/app/schemas/minimax.py` — Pydantic schemas for push request/response/config
- Create `apps/api/app/models/minimax_config.py` — per-org credentials (client_id, client_secret, username, password, minimax_org_id)
- Create Alembic migration for `minimax_configs` table
- Add API endpoints to export router:
  - POST `/api/v1/export/minimax/push` — push invoices to MiniMax
  - GET/PUT/PATCH `/api/v1/export/minimax/config` — manage credentials

**Acceptance:** Configure MiniMax credentials → push verified invoice → appears in MiniMax as received invoice. Customer created if not found.

---

#### 6.7 — Implement frontend export UI

**Description:** Build the frontend export dialog with format selection, options, and file download. Integrate into invoice list (batch export) and invoice detail (single export).

**Requirements covered:** FR-4.6.7

**Tasks:**
- Create `apps/web/src/lib/types/export.ts` — TypeScript types
- Add `apiDownload()` to `apps/web/src/lib/api-client.ts` — binary file download with auth
- Create `apps/web/src/lib/api/export.ts` — export API service + browser download trigger
- Create `apps/web/src/components/ExportDialog.tsx`:
  - Format selection cards (XLSX, CSV, JSON, MiniMax XML) in 2x2 grid
  - Format-specific options (include line items, delimiter, nested JSON)
  - Error handling: blocked invoices display with reasons (422)
  - MiniMax XML validation: warn if invoices not verified
  - Loading state with spinner during export
- Integrate into invoice list page: export button in batch action bar
- Integrate into invoice detail page: export option in more actions menu
- Activate dashboard "Export Report" button (remove "Coming Soon" badge)
- Add translation keys to all 3 locale files (sr-Latn, sr-Cyrl, en)

**Acceptance:** Select invoices → click Izvezi → choose format → file downloads. Single export from invoice detail works. MiniMax XML shows warning for unverified invoices.

---

#### 6.8 — Write tests for exports

**Description:** Tests for all export formats, templates, audit export, and MiniMax integration.

**Tasks:**
- Test XLSX generation: correct sheets, Serbian number/date formatting, column headers
- Test CSV generation: UTF-8 BOM, configurable delimiter, correct encoding of Serbian characters
- Test JSON generation: flat and nested modes validate against schema
- Test MiniMax XML: valid structure, Stranke + Temeljnice content
- Test custom template applies field selection and ordering
- Test export blocking: rejected when critical warnings unresolved
- Test audit export generates valid content, includes all requested types
- Test MiniMax push: mock API, verify mapping, customer creation
- Test export requires authentication and proper roles

**Acceptance:** All tests pass. Exported files contain correctly formatted data.

---

## Milestone 7: External Integrations

**Goal:** Integrate with SEF (eFaktura) for electronic invoice sync, NBS for exchange rates, Paddle for billing, and an email service for transactional emails.

### Issues

#### 7.1 — Implement SEF (eFaktura) inbound invoice sync

**Description:** Pull invoices from the Serbian E-Invoice System via polling (SEF does not support webhooks). Parse UBL/XML, download PDF attachments, and feed into the FakturaAI pipeline.

**Requirements covered:** Section 10.5.1 through 10.5.3, Section 7.6, Section 8.5.1, 8.5.2

**Tasks:**
- Create `apps/api/app/models/sef_connection.py` matching Section 8.5.1 schema
- Create `apps/api/app/models/sef_invoice.py` matching Section 8.5.2 schema
- Create `apps/api/app/services/sef.py`:
  - `poll_new_invoices(org_id)` — fetch invoices since last sync via SEF API
  - Parse UBL/XML into structured data
  - Download PDF attachments, store in S3
  - Create invoice + document records with SEF metadata
  - Run OCR on PDF for additional data/validation (SEF-OCR hybrid processing, Section 10.5.6)
  - Apply merge rules: PIB from SEF (authoritative), amounts from SEF, flag if OCR differs > 1%
  - Handle duplicate detection by SEF ID
- Create Celery periodic task for polling (configurable interval, default 15 min, 5 min during business hours, Section 10.5.5)
- SEF connection setup API:
  - POST `/api/v1/integrations/sef/connect` — store encrypted API key, org PIB
  - GET `/api/v1/integrations/sef/status` — sync status, last sync time, counts
  - POST `/api/v1/integrations/sef/sync` — trigger manual sync
- Handle all SEF error scenarios (Section 10.5.7)

**Acceptance:** Configure SEF connection → polling starts → new SEF invoices appear in invoice list with SEF metadata. Hybrid OCR+SEF data merged correctly.

---

#### 7.2 — Implement SEF outbound invoice push and status polling

**Description:** Support sending invoices to SEF and polling for status changes (approved, rejected, paid, etc.).

**Requirements covered:** Section 10.5.4, 10.5.5

**Tasks:**
- Implement UBL 2.1 XML generation from invoice data (Section 10.5.4 field mapping)
- Implement POST `/api/v1/invoices/{id}/send-to-sef`:
  - Validate all required UBL fields present
  - Generate XML, push to SEF API
  - Store SEF ID, update status
  - Handle errors with retry
- Implement status polling in `poll_sef_status_changes(org_id)`:
  - Detect status transitions (DELIVERED → APPROVED, REJECTED, etc.)
  - Handle each transition: update local status, notify user, create cancellation records as needed
  - Respect SEF API rate limits (max 100 requests/hour per org)
- Wire status changes to notification system

**Acceptance:** Send invoice to SEF → SEF ID stored. Buyer approves on SEF → status updated in FakturaAI within polling interval.

---

#### 7.3 — Implement NBS exchange rate integration

**Description:** Fetch daily exchange rates from the National Bank of Serbia for foreign currency → RSD conversion.

**Requirements covered:** Section 10.6, Section 7.7, Section 8.5.3

**Tasks:**
- Create `apps/api/app/models/exchange_rate.py` matching Section 8.5.3 schema
- Create `apps/api/app/services/nbs.py`:
  - `fetch_rate(currency, date)` — call NBS API, parse response
  - `get_exchange_rate(currency, date)` — check cache → DB → NBS API → fallback to last known
  - `convert_to_rsd(amount, currency, invoice_date)` — convert and record the rate used
  - Cache rates in Redis (24h TTL)
  - Support EUR, USD, CHF, GBP
- Create Celery beat task: fetch rates on business days at 08:30 (Section 10.6.4)
- Display RSD equivalent for foreign currency invoices
- Store the exchange rate used for each conversion (audit requirement)

**Acceptance:** Foreign currency invoice shows RSD equivalent. Rate sourced from NBS for the invoice date. Weekends use last business day rate.

---

#### 7.4 — Implement Paddle billing integration

**Description:** Integrate Paddle as Merchant of Record for subscription management and payment processing.

**Requirements covered:** Section 10.2

**Tasks:**
- Create `apps/api/app/services/paddle.py`:
  - Generate Paddle Checkout links for plan selection
  - Handle subscription lifecycle via webhooks
- Implement POST `/api/v1/webhooks/paddle` endpoint:
  - Verify Paddle webhook signatures
  - Handle events: `subscription.created`, `subscription.updated`, `subscription.canceled`, `transaction.completed`, `transaction.payment_failed`
  - Update organization `plan`, `payment_provider_customer_id`, `payment_provider_subscription_id`
- Create `apps/api/app/models/plan.py` for plan definitions (Starter, Professional, Enterprise)
- Implement usage tracking against subscription limits (Section 4.7.2)
- Implement usage alerts at 80%, 90%, 100% of plan limits

**Acceptance:** User subscribes via Paddle Checkout → organization plan updated. Usage tracked. Plan downgrade restricts features.

---

#### 7.5 — Implement transactional email service

**Description:** Send transactional emails for account lifecycle events.

**Requirements covered:** Section 10.3

**Tasks:**
- Create `apps/api/app/services/email.py` with SendGrid/Resend integration
- Implement email templates (Serbian + English):
  - Welcome / email verification
  - Password reset link
  - Invoice processing complete notification
  - Subscription change notification
  - Usage limit warning
- Queue emails via Celery (don't block API responses)

**Acceptance:** Register → welcome email sent. Request password reset → email with reset link sent.

---

#### 7.6 — Write tests for external integrations

**Description:** Tests for SEF, NBS, Paddle, and email integrations with mocked external APIs.

**Tasks:**
- Test SEF inbound sync with mocked SEF API responses
- Test SEF-OCR hybrid merge rules (amounts match, amounts differ, line item count differs)
- Test SEF outbound push with UBL XML validation
- Test SEF status polling and transition handling
- Test NBS rate fetching with cache, DB, and API layers
- Test currency conversion with correct rate selection
- Test Paddle webhook signature verification
- Test subscription lifecycle (create, update, cancel)
- Test email sending with mocked email provider

**Acceptance:** All tests pass. All external APIs are mocked.

---

#### 7.7 — Implement webhook notification system

**Description:** Allow organizations to register webhook URLs and receive callbacks for processing events (invoice processed, export ready, error occurred).

**Requirements covered:** FR-4.8.2, Section 8.1 (webhooks ERD)

**Tasks:**
- Create `apps/api/app/models/webhook.py`: `id`, `organization_id`, `url`, `events` (JSON array), `secret`, `is_active`, `created_at`
- Implement webhook CRUD API:
  - POST `/api/v1/webhooks` — register webhook URL with event subscriptions
  - GET `/api/v1/webhooks` — list organization webhooks
  - PATCH `/api/v1/webhooks/{id}` — update URL or event subscriptions
  - DELETE `/api/v1/webhooks/{id}` — remove webhook
- Implement webhook delivery service:
  - Sign payloads with HMAC-SHA256 using webhook secret
  - Deliver via Celery (async, don't block API)
  - Retry 3 times with exponential backoff on failure
  - Log delivery status and response codes
- Supported events: `invoice.processing_complete`, `invoice.error`, `export.ready`, `sef.status_changed`

**Acceptance:** Register webhook → upload invoice → webhook fires on processing complete with signed payload. Failed deliveries retry 3 times.

---

#### 7.8 — Implement usage tracking and recording

**Description:** Track organization resource usage (invoices processed, API calls, storage) per billing period for plan enforcement and billing.

**Requirements covered:** FR-4.7.2, Section 8.1 (usage_records ERD)

**Tasks:**
- Create `apps/api/app/models/usage_record.py`: `id`, `organization_id`, `period_start`, `period_end`, `invoices_count`, `api_calls_count`, `storage_bytes`
- Implement usage tracking middleware:
  - Increment `api_calls_count` per API request (via Redis counter, flush to DB periodically)
  - Increment `invoices_count` when invoice record created
  - Track `storage_bytes` when documents uploaded/deleted
- Implement usage aggregation Celery task (daily rollup)
- Enforce plan limits: return 429 when invoice limit exceeded
- Implement GET `/api/v1/usage` endpoint for current period usage

**Acceptance:** Process 5 invoices → usage record shows count 5. Exceed plan limit → 429 response. Usage endpoint returns accurate numbers.

---

## Milestone 8: Frontend Application

**Goal:** Build the complete frontend: dashboard, upload interface, invoice list, side-by-side review, settings, SEF inbox, billing, and responsive mobile layout with Cyrillic/Latin script support.

### Issues

#### 8.1 — Build dashboard and analytics page

**Description:** Create the main dashboard showing processing statistics, usage tracking, and quick actions.

**Requirements covered:** FR-4.7.1, FR-4.7.2, Section 11.2

**Tasks:**
- Create dashboard page at `/dashboard`:
  - Total invoices processed (daily, weekly, monthly, custom range)
  - Success rate and average processing time
  - Current usage vs subscription limit with progress bar
  - Recent invoices list (last 10)
  - Quick actions: upload, export, SEF sync
- Fetch data from backend analytics endpoints
- Use Recharts for data visualization (processing volume over time, accuracy trends)
- Add Zustand store for dashboard state

**Acceptance:** Dashboard shows real statistics. Usage bar reflects actual plan limits. Charts render with correct data.

---

#### 8.2 — Build invoice upload interface

**Description:** Create the drag-and-drop upload interface with file validation, progress indication, and batch support.

**Requirements covered:** FR-4.2.1, FR-4.2.2, FR-4.2.3, FR-4.2.4, Section 11.2

**Tasks:**
- Enhance upload page at `/upload`:
  - Drag-and-drop zone using react-dropzone (already installed)
  - File type and size validation with clear error messages (Serbian)
  - Support selecting up to 50 files for batch upload
  - Upload progress bar per file
  - Real-time processing status polling after upload
  - Mobile camera capture support (FR-4.2.4)
- Wire to POST `/api/v1/invoices/upload` and `/upload/batch` endpoints
- Show processing status updates as they arrive
- Navigate to invoice detail when processing completes

**Acceptance:** Drag PDF onto upload zone → file uploads with progress → processing status shown → navigates to review when done.

---

#### 8.3 — Build invoice list and filtering interface

**Description:** Create the filterable, sortable invoice table with pagination.

**Requirements covered:** FR-4.7.3, Section 11.2

**Tasks:**
- Create invoice list page at `/invoices`:
  - Use TanStack Table for data table
  - Columns: status, invoice number, date, seller, buyer, total, confidence, actions
  - Status filter chips (processing, review, verified, exported, error)
  - Date range picker
  - Full-text search input
  - Sortable columns
  - Pagination controls
- Wire to GET `/api/v1/invoices` with query parameters
- Row click navigates to invoice detail
- Batch actions: select multiple → export, delete, verify

**Acceptance:** Invoice list loads with pagination. Filters narrow results. Search finds invoices by number or company name.

---

#### 8.4 — Build side-by-side invoice review view

**Description:** Create the core review interface showing the original document alongside extracted data with confidence indicators and inline editing.

**Requirements covered:** FR-4.5.1, FR-4.5.2, Section 11.2

**Tasks:**
- Create invoice detail page at `/invoices/[id]`:
  - Left panel: document viewer (PDF via react-pdf, images via native viewer)
    - Zoom, pan, rotate controls
    - Click field → highlight corresponding area in document (if bounding boxes available)
  - Right panel: extracted data form
    - All fields editable inline
    - Confidence indicators per field (color-coded: green > 80%, yellow 60-80%, red < 60%)
    - Warnings and verification results displayed
    - AccountingIntent section: document type, VAT treatment, suggested konta
    - Correction tracking (edits auto-logged)
  - Action buttons: Verify, Export, Delete, Send to SEF
- Wire to GET `/api/v1/invoices/{id}`, PATCH `/api/v1/invoices/{id}`, POST `/api/v1/invoices/{id}/verify`

**Acceptance:** Review page shows document and extracted data side by side. Edit a field → saved and correction logged. Verify → status changes to verified.

---

#### 8.5 — Build settings, profile, and team management

**Description:** Create settings pages for user profile, organization settings, team management, and API keys.

**Requirements covered:** FR-4.1.4, Section 11.2

**Tasks:**
- Create settings page at `/settings`:
  - Profile tab: name, email, password change
  - Organization tab: company name, billing email, default script preference
  - Team tab: invite members, assign roles (admin, manager, operator, viewer), remove members
  - API Keys tab: generate/revoke API keys, view usage
  - Data & Privacy tab: consent management, data export request, account deletion
- Wire to backend user and organization endpoints
- Role-based visibility: only admins see team management and billing

**Acceptance:** User updates profile → changes saved. Admin invites team member → invitation sent. API key generated and usable.

---

#### 8.6 — Build SEF inbox interface

**Description:** Create the dedicated SEF inbox for managing incoming eFaktura invoices.

**Requirements covered:** Section 11.6

**Tasks:**
- Create SEF inbox page at `/sef-inbox`:
  - Table: status, supplier, invoice number, amount, sync date
  - Status filters: Sve, Nova, Na čekanju, Obrađeno, Odbijeno
  - Bulk actions: Obradi izabrane, Odbij, Arhiviraj
  - Manual sync trigger button
  - Last sync timestamp and pending count display
- Row click opens SEF invoice detail with accept/reject/process actions
- Wire to SEF integration endpoints

**Acceptance:** SEF invoices appear in inbox after sync. Process action creates FakturaAI invoice. Accept/reject sends response to SEF.

---

#### 8.7 — Build billing and subscription interface

**Description:** Create billing pages for plan selection, usage tracking, and invoice history.

**Requirements covered:** Section 11.2 (Billing)

**Tasks:**
- Create billing page at `/billing`:
  - Current plan display with feature list
  - Plan comparison and upgrade/downgrade (Starter, Professional, Enterprise)
  - Paddle Checkout integration for plan changes
  - Usage dashboard: invoices processed, API calls, storage used
  - Billing history (Paddle transaction history)
- Usage alerts shown as banners at 80%, 90%, 100% of limits

**Acceptance:** User sees current plan and usage. Upgrade redirects to Paddle Checkout. Transaction history loads.

---

#### 8.8 — Implement Cyrillic/Latin script toggle and i18n

**Description:** Add full bilingual support (Serbian Latin default, Cyrillic option) with a header toggle and all UI strings localized.

**Requirements covered:** Section 11.5

**Tasks:**
- Add i18n library (next-intl or react-i18next)
- Create translation files: `sr-Latn.json` (Latin), `sr-Cyrl.json` (Cyrillic), `en.json` (English)
- Replace all hardcoded strings across all components
- Add script toggle button in application header
- Persist script preference in user profile settings
- Locale-aware date/time formatting (`DD.MM.YYYY.` for Serbian)
- Locale-aware number formatting (`45.000,00` for Serbian)

**Acceptance:** Toggle to Cyrillic → all UI text switches to Cyrillic script. Preference persists across sessions.

---

#### 8.9 — Implement responsive mobile layout

**Description:** Make the entire UI responsive for mobile devices with a minimum 640px breakpoint.

**Requirements covered:** Section 11.3, Section 11.4

**Tasks:**
- Audit all pages and components for mobile breakpoints
- Invoice list: horizontal scroll or card layout on mobile
- Side-by-side review: stacked layout on mobile (document above, data below)
- Settings: full-screen panels on mobile
- Upload: full-width drop zone on mobile
- Dashboard: single-column card layout on mobile
- Ensure WCAG 2.1 AA compliance: keyboard navigation, screen reader compatibility, color contrast, focus indicators
- Test on Chrome Android and Safari iOS

**Acceptance:** App is fully usable on 640px-wide screen. No horizontal overflow. All interactive elements are touch-friendly.

---

#### 8.10 — Write frontend tests

**Description:** Component and integration tests for all frontend pages.

**Tasks:**
- Test auth flow: login → dashboard, logout → login redirect
- Test upload component: file validation, progress display
- Test invoice list: pagination, filtering, sorting
- Test invoice detail: field editing, verification action
- Test settings: profile update, team management visibility by role
- Test i18n: language switch changes all visible text
- Test responsive: key layouts render correctly at mobile breakpoint

**Acceptance:** All frontend tests pass. CI updated to run frontend tests.

---

#### 8.11 — Build public landing page

**Description:** Create the public marketing page with product features, pricing plans, and call-to-action.

**Requirements covered:** Section 11.2 (Landing Page)

**Tasks:**
- Create landing page at `/`:
  - Hero section with product description and CTA
  - Feature highlights (OCR, Cyrillic/Latin, APR verification, export, SEF integration)
  - Pricing table (Starter, Professional, Enterprise)
  - Footer with links to legal pages (privacy policy, terms of service)
- SEO optimization: meta tags, OpenGraph, structured data
- Serbian-first content with language toggle option

**Acceptance:** Landing page loads at `/`. Features, pricing, and CTA are visible. Links to login/register work.

---

## Milestone 9: CI/CD, Security & Production

**Goal:** Automated CI pipeline, end-to-end testing, security hardening, monitoring, and production deployment.

### Issues

#### 9.1 — Set up GitHub Actions CI pipeline

**Description:** Automated build, lint, and test pipeline for every push and PR.

**Requirements covered:** Section 6.3

**Tasks:**
- Create `.github/workflows/ci.yml`:
  - Lint: ESLint (frontend), Ruff (backend)
  - Type check: TypeScript (frontend), mypy (backend)
  - Unit tests: Jest (frontend), Pytest (backend) with PostgreSQL service container
  - Build: Next.js build, Docker image build
  - Coverage: report and enforce minimum thresholds (80% unit, 70% integration)
- Run Alembic migrations in CI before tests
- Cache dependencies (npm, pip) for faster runs
- Fail PR if any check fails

**Acceptance:** Push to any branch → CI runs all checks. PR blocked if tests fail or coverage drops.

---

#### 9.2 — Add end-to-end tests with Playwright

**Description:** E2E tests covering critical user flows.

**Requirements covered:** Section 12.3, Section 12.4

**Tasks:**
- Install and configure Playwright
- Write E2E tests for critical paths:
  - Registration → login → upload invoice → view processing status → review extracted data → verify → export
  - Login → SEF inbox → process invoice → review → export
  - Login → settings → change script → verify UI updates
  - Login → billing → view usage
- Run E2E tests against staging environment in CI
- Test on Chrome, Firefox, and WebKit

**Acceptance:** All E2E tests pass against staging. Critical user flows verified across browsers.

---

#### 9.3 — Security hardening

**Description:** Apply security measures across the stack.

**Requirements covered:** Section 5.4

**Tasks:**
- Implement CSRF protection on state-changing endpoints
- Add rate limiting (per Section 9.1 rate limits by plan)
- Implement account lockout after failed login attempts
- Add CSP headers, X-Frame-Options, X-Content-Type-Options
- Ensure all file uploads are validated (type, size, virus scan if available)
- PII masking in logs (email, PIB values)
- Implement token blacklisting for logout
- Complete password reset flow with email verification
- Implement token refresh endpoint (POST `/api/v1/auth/refresh`)
- Review and test all OWASP Top 10 vectors

**Acceptance:** Security scan (OWASP ZAP or equivalent) shows no critical or high vulnerabilities. Rate limiting enforced. CSRF protection active.

---

#### 9.4 — Set up monitoring and observability

**Description:** Deploy monitoring stack for production visibility.

**Requirements covered:** Section 6.4

**Tasks:**
- Integrate OpenTelemetry for distributed tracing
- Set up Prometheus metrics endpoint in FastAPI
- Configure Grafana dashboards:
  - Request latency (p50, p95, p99)
  - Error rate
  - OCR processing time distribution
  - Celery queue depth
  - Database connection pool usage
- Configure alerting via Alertmanager:
  - Error rate > 5% → alert
  - OCR queue depth > 50 → alert
  - API latency p99 > 1s → alert
- Ensure Sentry integration captures all unhandled exceptions (already partially configured)
- Configure Loki for log aggregation

**Acceptance:** Grafana dashboards show live metrics. Alerts fire correctly when thresholds exceeded. Sentry captures errors with stack traces.

---

#### 9.5 — Production deployment with Kubernetes

**Description:** Deploy to production Kubernetes cluster with proper resource allocation, health checks, and auto-scaling.

**Requirements covered:** Section 6.1, 6.2, Section 5.1, 5.2, 5.3

**Tasks:**
- Finalize Kubernetes manifests in `infra/k8s/`:
  - Web app deployment (2-4 replicas, 256Mi-512Mi memory)
  - API server deployment (2-4 replicas)
  - ML worker deployment (2-4 replicas, GPU resource requests)
  - Celery beat deployment (single replica)
  - PostgreSQL (managed service or StatefulSet with replicas)
  - Redis cluster (3 nodes)
  - Ingress with TLS (Let's Encrypt)
- Configure health check endpoints (liveness + readiness probes)
- Configure HPA (Horizontal Pod Autoscaler) based on CPU and queue depth
- Docker images: non-root user, distroless base where possible
- Alembic migrations run as init container before API starts
- Configure Cloudflare for CDN, DDoS protection, and SSL termination
- Set up daily automated database backups (30-day retention)

**Acceptance:** `kubectl apply` deploys the full stack. Health checks pass. Auto-scaling responds to load. Backups run daily.

---

#### 9.6 — Implement ZZPL compliance features

**Description:** Implement data protection features required by Serbian law (ZZPL).

**Requirements covered:** Section 13.1 through 13.7

**Tasks:**
- Create `apps/api/app/models/consent_record.py` matching Section 8.6.2
- Create `apps/api/app/models/deletion_request.py` matching Section 8.6.4
- Create `apps/api/app/models/data_processing_agreement.py` matching Section 8.6.1
- Implement consent management:
  - Track consent per type (basic processing, analytics, marketing)
  - Revocation endpoint with confirmation
- Implement right to erasure (ZZPL Article 30):
  - Delete profile data, preferences, sessions
  - Retain invoice data where legally required (10-year retention)
  - Confirm what was deleted vs retained
- Implement DPA management for enterprise clients
- Implement data breach notification template and workflow
- Add privacy policy endpoint serving current version

**Acceptance:** User requests data deletion → profile data removed, invoice data retained with explanation. Consent tracked per type. DPA stored for enterprise accounts.

---

#### 9.7 — Write integration and performance tests

**Description:** Final round of integration tests and performance benchmarks.

**Tasks:**
- Full integration test: upload → OCR → verify → accounting intent → export (end-to-end with test DB)
- Performance benchmarks (Section 12.2):
  - Page load (LCP) < 2s
  - Single invoice OCR < 5s (with GPU)
  - API response < 200ms for non-processing endpoints
  - Search query < 500ms
- Load test: 100 concurrent OCR jobs (Section 5.1)
- Multi-tenant isolation test: verify organization data boundaries
- Security test: OWASP Top 10 automated scan

**Acceptance:** All benchmarks met. Load test passes at target concurrency. No data leaks between organizations.

---

#### 9.8 — Implement API key authentication

**Description:** Build the API key system as an alternative authentication method for programmatic access (third-party integrations, scripts).

**Requirements covered:** FR-4.8.1, Section 8.1 (api_keys ERD), Section 9.1

**Tasks:**
- Create `apps/api/app/models/api_key.py`: `id`, `organization_id`, `user_id`, `key_hash`, `key_prefix` (first 8 chars for identification), `name`, `permissions` (JSON), `last_used`, `expires_at`, `created_at`
- API key generation: generate random key, store only the hash (Argon2), return plain key once to user
- Implement authentication middleware that accepts either JWT Bearer token or `X-API-Key` header
- Implement rate limiting per API key based on organization plan (Section 9.1)
- Create endpoints:
  - POST `/api/v1/api-keys` — generate new key (returns plain key once)
  - GET `/api/v1/api-keys` — list keys (prefix only, never expose full key)
  - DELETE `/api/v1/api-keys/{id}` — revoke key
- Track `last_used` timestamp on each API call

**Acceptance:** Generate API key → use it in `X-API-Key` header → authenticated request succeeds. Revoked key returns 401. Rate limits enforced per plan.

---

#### 9.9 — Implement email verification and OAuth login

**Description:** Complete the email verification flow for new registrations and add OAuth 2.0 as an alternative login method.

**Requirements covered:** FR-4.1.1, FR-4.1.2

**Tasks:**
- Email verification flow:
  - On registration, generate verification token (UUID, 24h expiry)
  - Send verification email via email service (issue 7.5)
  - Implement GET `/api/v1/auth/verify?token=...` endpoint to confirm email
  - Set `email_verified = true` on confirmation
  - Optionally restrict unverified users (warning banner, no export)
- OAuth 2.0 login (Google):
  - Implement GET `/api/v1/auth/oauth/google` — redirect to Google OAuth consent
  - Implement GET `/api/v1/auth/oauth/google/callback` — exchange code, create/link user account
  - Auto-verify email for OAuth users (Google guarantees email ownership)
  - Create organization for new OAuth users (same as email registration)

**Acceptance:** Register → verification email received → click link → email verified. Google OAuth login creates user account and JWT tokens.

---

#### 9.10 — Implement data retention automation

**Description:** Create scheduled jobs that enforce data retention policies defined in Section 13.4.

**Requirements covered:** Section 13.4

**Tasks:**
- Create Celery beat tasks for data cleanup:
  - Delete temporary files older than 24 hours
  - Delete expired sessions older than 30 days
  - Archive/delete correction logs older than 3 years
  - Flag inactive user accounts after 2 years (don't auto-delete, flag for admin review)
  - Audit log rotation: compress logs older than 12 months, delete older than 7 years
- Invoice data and original documents: 10-year retention (no auto-delete, but track retention end date)
- Export files: auto-delete after 30 days (already handled by S3 lifecycle rules)
- Log all automated retention actions in audit log

**Acceptance:** Scheduled cleanup runs → expired sessions deleted, temp files removed. Invoice data untouched (10-year retention). Cleanup logged.

---

## Milestone 10: Multi-Country Tax ID Validation

**Goal:** Extend tax ID validation beyond Serbian PIB to support invoices from the broader Balkan region and EU. Auto-detect country from tax ID format, validate with country-specific checksum algorithms, and provide appropriate user feedback.

**Dependencies:** M3 (PIB validation pipeline), M4 (APR verification pattern)

### Issues

#### 10.1 — Implement country-specific tax ID validators

**Description:** Create validators for Croatian OIB, Bosnian JIB, Montenegrin PIB, and EU VAT IDs alongside the existing Serbian PIB validator.

**Requirements covered:** SRS 4.9.2b

**Tasks:**
- Create `packages/ml/fakturaai_ml/validation/tax_id.py` with `TaxIDValidator` dispatcher
- Implement `OIBValidator` — Croatian 11-digit OIB (ISO 7064 Mod 11,10 checksum)
- Implement `JIBValidator` — Bosnian 13-digit JIB (Mod 10 checksum)
- Implement `MontenegroValidator` — Montenegrin 8-digit PIB (Mod 11 checksum)
- Implement `EUVATValidator` — EU VAT ID format validation (country prefix + country-specific pattern)
- `TaxIDValidator.detect_and_validate(tax_id, country_hint=None)` auto-detects country from:
  1. Tax ID length (9=Serbia, 11=Croatia, 13=BiH, 8=Montenegro)
  2. Optional country hint from invoice language/currency
- Each validator returns `ValidationResult` with `is_valid`, `country`, `warnings[]`
- Update pipeline `_sanitize_pibs` to call `TaxIDValidator` instead of hardcoded PIB logic
- Preserve backward compatibility: Serbian PIB validation unchanged

**Acceptance:** Given tax IDs from Serbia (9-digit), Croatia (11-digit), BiH (13-digit), and Montenegro (8-digit), the system correctly identifies the country and validates format + checksum. Invalid IDs produce appropriate warnings.

---

#### 10.2 — Extend LLM extraction prompt for multi-country invoices

**Description:** Update the Claude extraction prompt to recognize tax ID formats from Croatia, Bosnia, Montenegro, and EU countries.

**Requirements covered:** SRS 4.9.2b

**Tasks:**
- Add country-specific PIB/OIB/JIB extraction rules to `_SYSTEM_PROMPT` in `llm_extractor.py`:
  - Croatian invoices: OIB (11 digits), typically labeled "OIB:"
  - Bosnian invoices: JIB (13 digits), labeled "JIB:" or "ID broj:"
  - Montenegrin invoices: PIB (8 digits), labeled "PIB:"
  - EU invoices: VAT ID with country prefix (e.g., "DE123456789", "AT U12345678")
- Add `country` field to JSON extraction schema (auto-detected from invoice language/format)
- Update `CompanyData` type with optional `country` field
- Test with sample invoices from each country

**Acceptance:** LLM correctly extracts OIB from Croatian invoices, JIB from Bosnian invoices, and EU VAT IDs from EU invoices without breaking Serbian PIB extraction.

---

#### 10.3 — Add country-aware confidence scoring and validation warnings

**Description:** Extend confidence scoring and validation warnings to account for multi-country tax IDs.

**Requirements covered:** SRS 4.9.2b

**Tasks:**
- Update `ConfidenceCalculator._calculate_pib_confidence()` to boost confidence for valid OIB/JIB/Montenegro PIB checksums
- Update `_validate_invoice()` to use country-aware validation:
  - Serbian invoices: validate against Serbian VAT rates (0%, 10%, 20%)
  - Croatian invoices: validate against Croatian VAT rates (0%, 5%, 13%, 25%)
  - Bosnian invoices: validate against BiH VAT rate (17%)
  - Montenegrin invoices: validate against Montenegrin VAT rates (0%, 7%, 21%)
- Add country-specific validation warning messages (localized)
- Update frontend validation warning display if needed

**Acceptance:** Croatian invoice with OIB and 25% VAT rate validates correctly. Serbian invoice with 25% rate is flagged for review. Confidence scores reflect checksum validation per country.

---

#### 10.4 — Write tests for multi-country tax ID validation

**Description:** Comprehensive test coverage for all country-specific validators.

**Tasks:**
- Unit tests for OIBValidator: valid/invalid OIB, checksum validation, edge cases
- Unit tests for JIBValidator: valid/invalid JIB, checksum validation
- Unit tests for MontenegroValidator: valid/invalid 8-digit PIB
- Unit tests for EUVATValidator: common EU formats (DE, AT, FR, IT, NL)
- Unit tests for TaxIDValidator dispatcher: auto-detection from length, country hint override
- Integration tests: multi-country invoices through full pipeline
- Regression tests: Serbian PIB extraction unchanged by new validators

**Acceptance:** All tests pass. Coverage includes happy paths, invalid formats, checksum failures, and ambiguous cases.

---

## Summary

| Milestone | Issues | Key Deliverable |
|-----------|--------|----------------|
| **M1: Foundation & Auth** [DONE] | 1.1–1.6 | Users can register, login, JWT auth works, test infrastructure established |
| **M2: Document Storage & Upload** | 2.1–2.4 | Files upload to S3, database records created, Celery tasks queued |
| **M3: OCR Processing Pipeline** | 3.1–3.7 | dots.ocr (OCR) + Claude LLM (field extraction) extract structured data including tax_groups; regex fallback; PIB + math validation in pipeline; results saved to DB |
| **M4: Invoice Management & Verification** | 4.1–4.7 | Full CRUD, APR PIB verification, math checks, correction logging, audit trail |
| **M5: Accounting Intelligence & Rules** | 5.1–5.4 | AccountingIntent, VAT treatment, konta, PDV books, automation rules engine |
| **M6: Data Export** | 6.1–6.5 | XLSX/CSV/JSON export, custom templates, audit export for tax inspections |
| **M7: External Integrations** | 7.1–7.8 | SEF eFaktura sync, NBS exchange rates, Paddle billing, email, webhooks, usage tracking |
| **M8: Frontend Application** | 8.1–8.11 | Dashboard, upload, invoice list, review, settings, SEF inbox, billing, i18n, responsive, landing page |
| **M9: CI/CD & Production** | 9.1–9.10 | CI pipeline, E2E tests, security, monitoring, K8s deployment, ZZPL compliance, API keys, OAuth, data retention |
| **M10: Multi-Country Tax ID** | 10.1–10.4 | OIB/JIB/EU VAT validators, LLM prompt for multi-country, country-aware confidence scoring, tests |

**Total: 61 issues across 10 milestones.**

### Parallelization Opportunities

- **M2 and M8** can partially overlap — frontend upload UI (8.2) can start once upload endpoints exist
- **M5 and M6** are independent of each other after M4 completes
- **M7** sub-issues are largely independent: SEF, NBS, Paddle, email, and webhooks can be built in parallel
- **M8** frontend issues can proceed incrementally as backend milestones deliver APIs
- **M9.1** (CI pipeline) should start early (after M1) and evolve with each milestone
- **M8.8** (i18n) can start any time and be applied incrementally to new pages
- **M8.11** (landing page) is independent and can be built any time
- **M9.8** (API keys) and **M9.9** (OAuth) can be built in parallel
- **M10** can start after M3 (PIB validation exists). **10.1** (validators) and **10.2** (LLM prompt) can be built in parallel. **10.3** (confidence scoring) depends on 10.1. **10.4** (tests) can start with 10.1

### Estimated Issue Sizing

| Size | Description | Issues |
|------|-------------|--------|
| **S** | Config changes, small components, simple endpoints | 2.3, 3.6, 6.2, 7.3, 7.5, 7.8, 8.5, 8.7, 8.8, 8.9, 8.11, 9.10, 10.4 |
| **M** | Single service/component, moderate complexity | 2.1, 2.2, 2.4, 3.1, 3.3, 3.7, 4.1, 4.2, 4.5, 4.7, 5.2, 6.1, 6.3, 6.5, 7.4, 7.6, 7.7, 8.1, 8.2, 8.3, 8.6, 8.10, 9.1, 9.3, 9.6, 9.8, 9.9, 10.2, 10.3 |
| **L** | Multi-file, complex logic, significant testing | 3.2, 3.4, 3.5, 4.3, 4.4, 4.6, 5.1, 5.3, 5.4, 6.4, 7.1, 7.2, 8.4, 9.2, 9.4, 9.5, 9.7, 10.1 |
