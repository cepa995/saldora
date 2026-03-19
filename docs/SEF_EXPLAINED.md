# SEF (eFaktura) — How It Fits Into Saldora

## What is SEF?

**SEF (Sistem Elektronskih Faktura)** is Serbia's mandatory government e-invoicing system. Since 2023, every B2B and B2G invoice in Serbia must go through SEF. When a supplier sends your company an invoice, it arrives in SEF — not as a paper document or email attachment, but as structured XML data.

## The Problem for Accountants Today

Right now, a typical Serbian accountant's workflow looks like this:

1. Log into SEF portal, see new incoming invoices
2. Log into MiniMax (or their accounting software), manually re-enter the invoice data
3. Classify it (KPR/KIR, VAT treatment, konta)
4. Maybe also receive a PDF copy via email, file it somewhere
5. Cross-check everything manually

This is **tedious, error-prone, and duplicated work**. The data already exists in structured form in SEF, yet accountants are manually copy-pasting it into their accounting software.

## How Saldora Solves This

Saldora sits **between SEF and MiniMax**, automating the entire pipeline:

```
SEF (eFaktura)  →  Saldora  →  MiniMax (accounting)
    [source]       [intelligence]     [destination]
```

**The flow:**

1. **Sync** — Saldora pulls new invoices from SEF automatically (polling every 15 minutes)
2. **Review** — Accountant sees them in `/sef-inbox`, clicks "Process"
3. **Intelligence** — Saldora auto-classifies: input/output invoice, VAT treatment (deductible/non-deductible), suggests konta numbers, applies automation rules
4. **Export** — One click exports to MiniMax with correct accounting entries

**What the accountant does NOT have to do anymore:**

- Manually type invoice numbers, amounts, PIB, dates
- Look up the correct VAT treatment
- Figure out which konta to use
- Re-enter data into MiniMax

## Why Not Just Use SEF Directly?

SEF is a **government portal** — it stores and transmits invoices but does NOT:

- Classify invoices for accounting (KPR/KIR, konta)
- Determine VAT treatment (deductible, non-deductible, partial)
- Connect to accounting software like MiniMax
- Apply business rules (e.g., "all invoices from supplier X go to konto 5210")
- Provide OCR for scanned/PDF invoices that arrive outside SEF

Saldora adds the **intelligence layer** that SEF lacks.

## Why Not Just Use MiniMax Directly?

MiniMax is **accounting software** — it records transactions but does NOT:

- Pull invoices from SEF automatically
- Extract data from PDF/scanned invoices via OCR
- Auto-classify document types and VAT treatment
- Validate PIB numbers against APR
- Detect duplicate invoices
- Apply automation rules

Saldora is the **bridge** that connects these two systems.

## Two Input Channels

Saldora accepts invoices from two sources:

```
1. SEF (structured XML)     →  High accuracy, no OCR needed
2. PDF/scan upload (OCR)    →  For invoices not in SEF (foreign, older, etc.)
```

Both channels feed into the same pipeline: Review → Accounting Intent → Export.

## Technical Details

- **SEF does NOT support webhooks** — Saldora must poll for new invoices
- **UBL 2.1 XML** is the standard format for SEF invoices
- **Dual status model**: Saldora tracks both an internal status (`new → pending → processed`) and the raw SEF status (`DELIVERED → SEEN → APPROVED`)
- **DemoSefClient** allows development and testing without real SEF API credentials
- **Multi-tenant**: Each organization has its own SEF connection and credentials

## The Complete Pipeline

```
┌─────────┐     ┌──────────────┐     ┌─────────────┐     ┌─────────┐
│   SEF   │────▶│  SEF Inbox   │────▶│  Saldora  │────▶│ MiniMax │
│eFaktura │     │  /sef-inbox  │     │  /invoices  │     │ Export  │
└─────────┘     └──────────────┘     └─────────────┘     └─────────┘
                  Sync & Review       Auto-classify        Push to
                                      VAT, konta,          accounting
                                      rules engine         software

┌─────────┐     ┌──────────────┐          │
│  PDF /  │────▶│  OCR Upload  │──────────┘
│  Scan   │     │  /invoices   │
└─────────┘     └──────────────┘
```
