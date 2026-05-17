# Automation Rules Engine

## 1. Overview

The automation rules engine enables accounting offices to define custom, deterministic rules that automatically classify invoices during the verification stage of the processing pipeline. Rules can override suggested konta, set VAT treatment, flag invoices for manual review, or auto-approve them — based on conditions evaluated against invoice fields such as supplier PIB, amounts, line item descriptions, and computed metadata.

### Design Philosophy

The rules engine is **entirely deterministic and programmatic**. No LLM, ML model, or external AI service is involved in rule evaluation. Conditions are evaluated using exact matching logic — conditional branching, regular expressions, and numeric comparisons. This guarantees:

- **Predictability** — identical inputs always produce identical outputs
- **Performance** — evaluation completes in single-digit milliseconds with no external API calls
- **Auditability** — every match is recorded with the exact conditions that matched and actions that were applied
- **Zero marginal cost** — no per-invocation token usage or API fees

The LLM is used only in earlier pipeline stages (OCR text extraction and structured field extraction). By the time the rules engine executes, all invoice data is fully structured and available as typed fields.

---

## 2. User Workflow

### 2.1 Rule Creation

Accountants create rules via the `/rules` page. A rule consists of:

- **Name** — unique per organization (enforced by database constraint)
- **Description** — optional documentation of the rule's purpose
- **Rule type** — categorization (see Section 4)
- **Priority** — integer from 1 to 1000; lower values execute first
- **Conditions** — a logical group (AND or OR) containing one or more field conditions
- **Actions** — one or more modifications to apply when conditions match

Rules can be created manually or instantiated from one of nine pre-built templates designed for common Serbian accounting scenarios (see Section 8).

### 2.2 Invoice Processing

When an invoice is uploaded (via the upload page, SEF inbox, or API), the system runs OCR and field extraction. The invoice enters "review" status with structured data available.

### 2.3 Verification Triggers Rule Evaluation

Upon verification (triggered automatically or by the accountant clicking "Verifikuj"), the backend executes the accounting intelligence pipeline. The rules engine runs as Step 4.5 — after the AI-driven classification but before final review flag determination. See Section 5 for the precise integration point and merge behavior.

### 2.4 Ongoing Monitoring

Each rule tracks its execution count and last execution timestamp. The rules page displays these statistics on every rule card. A full execution history is available per rule, showing which invoices triggered the rule, what conditions matched, and what actions were applied.

---

## 3. Condition System

### 3.1 Condition Structure

Conditions are organized as a tree structure. The root is a **logical group** with an operator (AND or OR) containing a list of **condition rules** (leaf nodes). In the current frontend implementation, conditions are flat (a single AND/OR group with leaf conditions), which covers the vast majority of use cases. The backend supports arbitrary nesting for future extensibility.

**AND semantics:** All conditions in the group must match for the group to evaluate as true.

**OR semantics:** At least one condition in the group must match.

**Vacuous truth:** An AND group with zero conditions evaluates to true (matches all invoices). This enables rules that always fire, such as "flag every invoice from this organization for review."

### 3.2 Available Fields

Fields are organized into six groups:

**Seller fields** — `seller.pib`, `seller.name`, `seller.address`, `seller.city`

**Buyer fields** — `buyer.pib`, `buyer.name`, `buyer.address`, `buyer.city`

**Amount fields** — `total_amount`, `subtotal`, `tax_rate`, `tax_amount`

**Line item fields** — `line_items[].description` (with any-match semantics; see Section 3.4)

**Document fields** — `currency`, `document_type`, `invoice_number`

**Computed fields** (calculated at evaluation time via database queries):
- `is_first_from_supplier` — boolean; true if zero prior invoices exist from this seller PIB within the organization
- `supplier_invoice_count` — integer; total count of prior invoices from this seller PIB
- `confidence` — decimal; the ML pipeline's overall confidence score for the extracted data

### 3.3 Field Resolution

The engine resolves field paths using three strategies:

1. **Simple fields** (e.g. `total_amount`) — direct key lookup against the evaluation context dictionary.

2. **Dot-notation fields** (e.g. `seller.pib`) — the path is split on `.` and traversed through nested dictionaries. If any segment is missing or the intermediate value is not a dictionary, the field resolves to null.

3. **Array accessor fields** (e.g. `line_items[].description`) — the path is split on `[].` to extract the array name and the child field name. The engine maps over all items in the array, extracting the specified field from each. Returns a list of non-null values, or null if the array is empty or missing.

All resolution paths return null for missing data rather than raising exceptions, enabling safe use of `is_null` / `is_not_null` operators on any field.

### 3.4 Array Field Any-Match Semantics

When a condition targets an array field (currently only `line_items[].description`), the operator is applied to each element individually. The condition matches if **any** element satisfies the operator. This provides powerful implicit OR semantics: `line_items[].description contains "gorivo"` matches an invoice if any single line item mentions fuel, regardless of how many line items exist.

### 3.5 Operators

The engine supports 13 operators, each with defined type coercion behavior:

| Operator | Description | Applicable Types | Value Required |
|----------|-------------|-----------------|----------------|
| `equals` | Exact match with type coercion | All | Yes |
| `not_equals` | Inverse of equals | All | Yes |
| `contains` | Case-insensitive substring match | Text, arrays | Yes |
| `starts_with` | Case-insensitive prefix match | Text | Yes |
| `ends_with` | Case-insensitive suffix match | Text | Yes |
| `regex` | Regular expression match (case-insensitive) | Text | Yes |
| `greater_than` | Numeric comparison after Decimal coercion | Numeric | Yes |
| `less_than` | Numeric comparison after Decimal coercion | Numeric | Yes |
| `between` | Inclusive range check; value is [min, max] | Numeric | Yes (array of two) |
| `in` | Field value exists in provided list | Text | Yes (array) |
| `not_in` | Field value does not exist in provided list | Text | Yes (array) |
| `is_null` | Field is null/missing | All | No |
| `is_not_null` | Field is present and non-null | All | No |

**Null handling:** All operators except `is_null` and `is_not_null` return false when the field value is null. This prevents null-pointer errors and ensures rules only match when data is present.

**Regex error handling:** If the user provides an invalid regex pattern, the engine catches the error, logs a warning, and returns false (no match) rather than raising an exception.

### 3.6 Type Coercion

For comparison operators (`equals`, `not_equals`, `greater_than`, `less_than`, `between`), the engine applies a multi-level coercion strategy:

1. **Decimal numeric comparison** (primary) — both values are converted to Decimal for precise numeric comparison. This handles mixed types like string `"100"` compared against integer `200`.
2. **Boolean comparison** (fallback) — if either value is boolean, both are coerced to boolean.
3. **String comparison** (final fallback) — case-insensitive string comparison as the last resort.

This ensures that `total_amount greater_than 50000` works correctly even when the invoice stores amounts as strings from OCR extraction.

---

## 4. Action System

### 4.1 Action Types

| Action Type | Purpose | Required Parameters |
|-------------|---------|-------------------|
| `SET_KONTO` | Override suggested konta entries | `target` (debit/credit side), `value` (konto number), optional `description` |
| `SET_VAT_TREATMENT` | Override VAT treatment classification | `value` (treatment code) |
| `FLAG_REVIEW` | Force manual review | Optional `reason` (displayed to accountant) |
| `AUTO_APPROVE` | Mark as not requiring review | None |
| `SET_CUSTOM_FIELD` | Set arbitrary metadata | `target` (field name), `value` (field value) |

### 4.2 Action Application Behavior

Actions mutate a shared modifications dictionary progressively as each matching rule is processed:

**SET_KONTO** maps the provided target to the appropriate side of the accounting entry. The target parameter accepts accounting categories (expense, revenue, asset, vat_input, vat_output, liability), which are mapped to debit or credit sides. If an entry with the same description already exists, it is replaced to prevent duplicates.

**SET_VAT_TREATMENT** sets the VAT treatment field and automatically derives the `is_deductible` flag: treatments containing NON_DEDUCTIBLE or OUTPUT_EXEMPT set deductibility to false; all others set it to true.

**FLAG_REVIEW** sets `requires_review` to true and appends the provided reason to an accumulating list. Multiple rules can each contribute their own review reason, and all reasons are preserved for the accountant to see.

**AUTO_APPROVE** sets an approval flag. This is subject to conflict resolution (see Section 6).

**SET_CUSTOM_FIELD** adds an arbitrary key-value pair to a custom fields dictionary, enabling extensible metadata without schema changes.

---

## 5. Pipeline Integration

### 5.1 Position in the Processing Pipeline

The accounting intelligence pipeline runs during invoice verification in the following order:

| Step | Operation | Nature |
|------|-----------|--------|
| 1 | Classify document type | AI-driven |
| 2 | Detect transaction type | AI-driven |
| 3 | Determine VAT treatment | AI-driven |
| 4 | Suggest konta | AI-driven |
| 4.5 | **Apply automation rules** | **Deterministic** |
| 5 | Generate PDV book entries | Deterministic |
| 6 | Determine review flags | Deterministic |

Steps 1–4 produce the AI-driven baseline. Step 4.5 (rules) applies organization-specific overrides. Steps 5–6 finalize the accounting intent with the potentially-modified values.

### 5.2 Evaluation Flow

1. The orchestrator calls `evaluate_rules()`, passing the database session, invoice record, organization ID, document type from Step 1, the suggested konta dictionary from Step 4, VAT treatment from Step 3, and the overall confidence score.

2. The engine fetches all active rules for the organization, ordered by priority ascending then creation date ascending (deterministic ordering).

3. For each rule, the engine builds an evaluation context from the invoice data including computed fields (supplier history requires a database query, performed once and cached in the context).

4. Conditions are evaluated recursively. If the root condition group matches, the rule's actions are applied to the modifications accumulator.

5. After all rules have been evaluated, conflict resolution runs (see Section 6).

6. The engine returns a tuple: the modifications dictionary and the applied rules audit list.

### 5.3 Modification Merging

After the engine returns, the orchestrator merges modifications into the pipeline state:

- If rules produced a `suggested_konta` override, the AI-suggested konta are replaced entirely.
- If rules set a `vat_treatment`, the AI-determined treatment is replaced.
- If rules explicitly set `is_deductible`, that value takes precedence.

These merged values flow into Steps 5 and 6, meaning PDV book entries and review flags are computed against the rule-modified data.

### 5.4 Review Flag Merging

After Step 6 (review flag determination), rule-based review modifications are merged additively:

- If any rule set `requires_review`, the invoice is marked for review regardless of Step 6's determination.
- Rule-provided review reasons are appended to the pipeline's review reasons list.
- If a rule set `auto_approve` and no rule set `requires_review`, the pipeline's review flag can be overridden to false (with rule-irrelevant reasons filtered out).

### 5.5 Applied Rules Recording

The `applied_rules` field on the AccountingIntent record stores a JSON array of all rules that matched. Each entry contains the rule's UUID, name, and the list of actions that were applied. This provides a complete audit trail visible on the invoice detail page.

---

## 6. Conflict Resolution

When multiple rules match the same invoice, conflicts are resolved deterministically:

### 6.1 FLAG_FOR_REVIEW vs. AUTO_APPROVE

**FLAG_FOR_REVIEW always takes precedence.** If any rule sets `requires_review` to true, the `auto_approve` flag is removed from the modifications dictionary entirely. The rationale: a human explicitly requesting review should never be silently overridden by an auto-approve rule.

### 6.2 Competing KONTO or VAT Rules

**First match wins.** Because rules are evaluated in priority order (lowest number first), the first rule to set a konto assignment or VAT treatment establishes the value. Subsequent rules that attempt to override the same field will replace the earlier value, but since higher-priority rules execute first, they effectively win.

Accounting offices should assign lower priority numbers to their most authoritative rules.

### 6.3 Accumulative Fields

Review reasons accumulate across all matching rules. If three rules each flag for review with different reasons, all three reasons appear in the final `review_reasons` list. This ensures no information is lost and the accountant can see every reason the invoice was flagged.

---

## 7. Rule Types

Rules are categorized by type for organizational and filtering purposes:

| Type | Intended Use |
|------|-------------|
| `KONTO_ASSIGNMENT` | Rules that assign or override konto numbers based on supplier, amount, or line item content |
| `VAT_TREATMENT` | Rules that override the AI-determined VAT deductibility or treatment classification |
| `AUTO_APPROVE` | Rules that automatically approve invoices meeting specific criteria, bypassing manual review |
| `FLAG_FOR_REVIEW` | Safety-valve rules that ensure certain invoices always receive human attention |
| `DOCUMENT_TYPE` | Rules that reclassify the document type (input vs output invoice, credit note, etc.) |
| `CUSTOM_FIELD` | Rules that attach arbitrary metadata to the accounting intent for downstream consumption |

The `rule_type` field is informational and used for filtering in the UI. It does not constrain which actions a rule may contain — a rule typed as `KONTO_ASSIGNMENT` may also include a `FLAG_REVIEW` action if desired.

---

## 8. Pre-Built Templates

Nine templates are provided for common Serbian accounting scenarios. Templates are defined in application code (not stored in the database) and are immutable. Applying a template creates a new rule pre-populated with the template's conditions and actions; the user can modify it before saving.

### Automation Templates (konto/VAT assignment)

| Template | Priority | Conditions | Actions |
|----------|----------|------------|---------|
| **Fuel — non-deductible** | 5 | Line items contain fuel keywords (`gorivo`, `benzin`, `dizel`) AND seller is a known fuel company (NIS, MOL, OMV, Petrol, Lukoil) | SET_VAT_TREATMENT → NON_DEDUCTIBLE, SET_KONTO → 5130 (fuel expenses) |
| **Telecom expenses** | 10 | Seller PIB matches Telekom Srbija PIBs AND document type is INPUT_INVOICE | SET_KONTO → 5210 (telecommunication costs) |
| **Office supplies** | 20 | Line items contain office keywords (`papir`, `toner`, `olovka`, `sveska`, `fascikla`, `kancelarija`) | SET_KONTO → 5120 (office supplies) |
| **Professional services** | 20 | Line items contain service keywords (`konsulta`, `pravne usluge`, `advokat`, `revizij`, `knjigovski`) | SET_KONTO → 5330 (professional services) |
| **Utilities** | 15 | Seller name matches utility provider pattern (`EPS`, `Elektroprivreda`, `Vodovod`, `Toplane`, `Infostan`) | SET_KONTO → 5131 (energy and utilities) |
| **Rent payments** | 15 | Line items contain rent keywords (`zakup`, `rent`, `najam`, `korišćenje prostora`) | SET_KONTO → 5230 (rent expenses) |

### Safety-Valve Templates (review flagging)

| Template | Priority | Conditions | Actions |
|----------|----------|------------|---------|
| **Large invoice review** | 1 | `total_amount` > 500,000 AND `currency` = RSD | FLAG_REVIEW → "Faktura prelazi 500.000 RSD" |
| **New supplier review** | 2 | `is_first_from_supplier` = true | FLAG_REVIEW → "Prvi put primamo fakturu od ovog dobavljača" |
| **Foreign supplier review** | 3 | `document_type` = INPUT_INVOICE AND `currency` ≠ RSD | FLAG_REVIEW → "Faktura u stranoj valuti — potrebna dodatna provera" |

Safety-valve templates are assigned the lowest priority numbers (1–3), ensuring they execute before any konto assignment rules. This guarantees that high-value, first-time, or foreign-currency invoices are always flagged for review even if other rules would otherwise auto-classify them.

---

## 9. Data Model

### 9.1 automation_rules Table

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | Primary key (generated via UUIDMixin) |
| organization_id | UUID | Foreign key → organizations; multi-tenant scoping |
| name | VARCHAR(255) | Not null |
| description | TEXT | Nullable |
| rule_type | VARCHAR(30) | Not null |
| priority | INTEGER | Not null, default 50 |
| conditions | JSONB | Not null; stores the condition tree |
| actions | JSONB | Not null; stores the action array |
| is_active | BOOLEAN | Not null, default true |
| created_by | UUID | Foreign key → users |
| updated_by | UUID | Foreign key → users, nullable |
| execution_count | INTEGER | Not null, default 0; incremented on each match |
| last_executed_at | TIMESTAMP | Nullable; updated on each match |
| created_at | TIMESTAMP | Auto-set (TimestampMixin) |
| updated_at | TIMESTAMP | Auto-updated (TimestampMixin) |

**Indexes:**
- `ix_automation_rules_org_active` — partial index on `organization_id` where `is_active = true`; optimizes the primary query path in `evaluate_rules()` which fetches only active rules
- `ix_automation_rules_type` — index on `rule_type`; supports type-based filtering in the list endpoint
- Standard index on `organization_id`

**Constraints:**
- `uq_rule_name_per_org` — unique constraint on `(organization_id, name)`; prevents duplicate rule names within an organization

### 9.2 rule_executions Table

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | Primary key |
| rule_id | UUID | Foreign key → automation_rules (CASCADE delete) |
| invoice_id | UUID | Foreign key → invoices (CASCADE delete) |
| accounting_intent_id | UUID | Foreign key → accounting_intents, nullable |
| conditions_matched | JSONB | Snapshot of matched condition tree at execution time |
| actions_applied | JSONB | Snapshot of applied actions at execution time |
| executed_at | TIMESTAMP | Server default: now() |
| execution_time_ms | INTEGER | Nullable; wall-clock time for rule evaluation |

**Indexes:** On `rule_id`, `invoice_id`, and `executed_at` for efficient querying of execution history by rule or by invoice.

**Cascade behavior:** Execution records are automatically deleted when the parent rule or invoice is deleted, preventing orphaned audit records.

---

## 10. API Layer

### 10.1 Endpoints

All endpoints require authentication. All data is scoped to the authenticated user's organization — a user cannot access, modify, or delete rules belonging to another organization.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/rules/templates` | Returns the nine pre-built templates. No database access; templates are defined in application code. |
| POST | `/api/v1/rules` | Creates a rule. Sets `created_by` to the authenticated user, `execution_count` to 0, and `is_active` to the provided value (default true). Returns 201. |
| GET | `/api/v1/rules` | Lists rules for the organization. Supports `?rule_type` and `?is_active` query parameters for filtering. Returns items ordered by priority ascending, then creation date ascending. Includes total count. |
| GET | `/api/v1/rules/{id}` | Returns a single rule. Returns 404 if the rule does not exist or belongs to a different organization. |
| PATCH | `/api/v1/rules/{id}` | Partially updates a rule. Only provided fields are modified. Sets `updated_by` to the authenticated user. Returns 404 for missing or unauthorized rules. |
| DELETE | `/api/v1/rules/{id}` | Permanently deletes a rule and its associated execution records (via CASCADE). Returns 204 on success, 404 for missing or unauthorized rules. |
| GET | `/api/v1/rules/{id}/executions` | Returns execution history for a rule, ordered by most recent first. Accepts `?limit` parameter (default 50, max 100). Verifies rule ownership before returning data. |

### 10.2 Organization Isolation

Every database query in the rules router includes an `organization_id` filter derived from the authenticated user's session. This is enforced at the query level — there is no application-layer check that could be bypassed. A user in Organization A receives a 404 (not 403) when attempting to access Organization B's rules, preventing information leakage about rule existence.

### 10.3 Condition/Action Validation

The API accepts conditions and actions as arbitrary JSON structures. Structural validation is deferred to evaluation time — if a rule contains an invalid field path or unsupported operator, it will simply not match (returning false) rather than causing an error. This design choice favors availability over strict validation, though the frontend enforces valid structures through its form builder.

---

## 11. Frontend Implementation

### 11.1 Architecture

The frontend follows the established application patterns:

- **Types** (`lib/types/rule.ts`) — TypeScript interfaces mirroring backend schemas
- **API service** (`lib/api/rules.ts`) — typed wrappers around the authenticated API client
- **State hook** (`hooks/useRuleList.ts`) — manages list state, filters, and CRUD operations
- **Page** (`app/(app)/rules/page.tsx`) — single-file page with all components defined inline

### 11.2 Page Components

**Rules list** — card-based layout (not a table) because rules contain nested conditions and actions that don't fit tabular format. Each card shows the rule name, type badge (color-coded), priority, active toggle, human-readable condition and action summaries, execution statistics, and action buttons.

**Rule form modal** — full-screen overlay for creating and editing rules. Contains basic fields (name, description, type, priority), a condition builder with field/operator/value rows, and an action builder with type-specific input fields.

**Condition builder** — supports a single logical group (AND/OR toggle) with flat condition rows. Each row provides a grouped field dropdown (organized by category), an operator dropdown (filtered to valid operators for the selected field type), and a value input that adapts to the operator (two inputs for `between`, comma-separated for `in`/`not_in`, hidden for `is_null`/`is_not_null`).

**Action builder** — each row has a type selector with type-specific fields: SET_KONTO shows side/number/description inputs, SET_VAT_TREATMENT shows a dropdown of treatment codes, FLAG_REVIEW shows a reason text input, AUTO_APPROVE has no additional fields.

**Templates modal** — displays all nine templates in a grid. Selecting a template closes the modal and opens the rule form pre-populated with the template's data.

**Execution history modal** — lists executions for a specific rule with timestamps, linked invoice IDs, applied actions, and execution duration.

### 11.3 Internationalization

All user-facing strings are externalized to translation files in three locales: Serbian Latin (`sr-Latn`), Serbian Cyrillic (`sr-Cyrl`), and English (`en`). The rules namespace contains approximately 80 translation keys covering UI labels, operator names, field group names, rule type labels, and user-facing messages.

---

## 12. Execution Audit Trail

Every time a rule matches an invoice during verification, the engine creates a RuleExecution record capturing:

- Which rule matched (by ID)
- Which invoice triggered it (by ID)
- The accounting intent it contributed to (by ID, if available)
- A snapshot of the conditions that were evaluated (preserving the exact state at evaluation time)
- A snapshot of the actions that were applied
- The wall-clock execution time in milliseconds

Additionally, the rule's own statistics are updated: `execution_count` is incremented and `last_executed_at` is set to the current timestamp. These statistics are visible on the rules list page, giving accountants immediate insight into which rules are actively firing and which may be obsolete.

---

## 13. Test Coverage

The test suite contains 63 tests organized across the following domains:

**Operator tests (18 tests)** — each of the 13 operators is tested for both matching and non-matching cases. Additional tests cover type coercion (Decimal vs. integer, string vs. numeric), invalid regex handling (graceful failure), and boundary conditions for `between` (inclusive bounds).

**Field resolution tests (5 tests)** — simple field lookup, nested dot-notation traversal, array accessor resolution, and null handling for missing paths.

**Condition logic tests (7 tests)** — AND semantics (all must match), OR semantics (any must match), nested combinations, empty groups (vacuous truth), and empty condition dictionaries.

**Action application tests (6 tests)** — each action type tested for correct modification behavior, including konto entry creation with proper debit/credit mapping, VAT treatment with automatic deductibility derivation, review reason accumulation, and custom field setting.

**Conflict resolution tests (2 tests)** — FLAG_FOR_REVIEW overriding AUTO_APPROVE, and AUTO_APPROVE preserved when no conflict exists.

**CRUD API tests (13 tests)** — create (201 response, initial statistics), list with filtering, get, update, delete, organization isolation (404 for cross-org access), and templates endpoint validation.

**Pipeline integration tests (5 tests)** — end-to-end verification that rules modify konta, VAT treatment, and review flags during the actual invoice verification flow, with `applied_rules` correctly populated on the AccountingIntent record.

**Accounting intelligence tests (9 tests)** — document classification, transaction type detection, VAT treatment determination, konta suggestion accuracy, VAT breakdown construction, and PDV book entry generation (KPR/KIR).

---

## 14. Worked Example

### Setup

An accounting office has configured three rules:

| Priority | Name | Type | Conditions | Actions |
|----------|------|------|-----------|---------|
| 10 | Gorivo — neodbitni PDV | VAT_TREATMENT | `line_items[].description` regex `gorivo\|benzin\|dizel` | SET_VAT_TREATMENT → NON_DEDUCTIBLE |
| 20 | Veliki iznos — pregled | FLAG_FOR_REVIEW | `total_amount` greater_than 500000 | FLAG_REVIEW → "Iznos prelazi 500.000 RSD" |
| 30 | Novi dobavljač — pregled | FLAG_FOR_REVIEW | `is_first_from_supplier` equals true | FLAG_REVIEW → "Novi dobavljač" |

### Invoice

A fuel receipt from NIS Petrol for 620,000 RSD. This is the first invoice from this supplier in the organization.

### Evaluation Trace

**Rule 10 (priority 10):** The engine resolves `line_items[].description`, producing a list of all line item descriptions. It applies the `regex` operator with pattern `gorivo|benzin|dizel` against each description. One line item contains "Gorivo Euro 5" — the case-insensitive regex matches. **Result: MATCH.** Action applied: `vat_treatment` set to NON_DEDUCTIBLE, `is_deductible` automatically set to false.

**Rule 20 (priority 20):** The engine resolves `total_amount`, obtaining 620000. It applies `greater_than` with value 500000. Both values are coerced to Decimal for comparison. 620000 > 500000 is true. **Result: MATCH.** Action applied: `requires_review` set to true, "Iznos prelazi 500.000 RSD" appended to review reasons.

**Rule 30 (priority 30):** The engine resolves `is_first_from_supplier`. During context building, the engine queried the invoices table and found zero prior invoices from this seller PIB — the field is true. The `equals` operator compares true == true. **Result: MATCH.** Action applied: `requires_review` remains true, "Novi dobavljač" appended to review reasons.

### Conflict Resolution

Both `requires_review` and no `auto_approve` are set — no conflict exists. The FLAG_FOR_REVIEW vs AUTO_APPROVE rule does not apply.

### Final AccountingIntent

The AI pipeline initially suggested DEDUCTIBLE_FULL VAT treatment. The rules engine overrode this:

- `vat_treatment`: NON_DEDUCTIBLE (overridden by Rule 10)
- `is_deductible`: false (derived from VAT treatment)
- `requires_review`: true (set by Rules 20 and 30)
- `review_reasons`: ["Iznos prelazi 500.000 RSD", "Novi dobavljač"]
- `applied_rules`: three entries recording each rule's ID, name, and actions

The accountant sees this invoice flagged for review with two reasons and the correct non-deductible VAT treatment — all applied automatically in under 5ms.
