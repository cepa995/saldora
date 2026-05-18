# M20 — Accountant Meeting Agenda

**Goal of the meeting:** turn the hospitality-forms layer from a deferred specification into a concrete set of column-level requirements + a monthly workflow we can ship against.

**Goal of *this document*:** give the accountant a strawman to push back on. Open-ended discovery interviews underperform; concrete artifacts elicit specific corrections.

**Pre-meeting reading** (the accountant doesn't need to read these; the agency lead and Saldora team do):

- [Research notes](./M20_research_notes.md) — once we paste the regulation findings into the repo, they'll live here.
- [SRS §4.19](./SRS.md#419-hospitality-legal-forms-m20-partial) — obligation matrix, prescribed column structures, current build status per form.
- [SRS §1 (current thesis)](./SRS.md) — why forms are the wedge and why we're waiting for the meeting before committing column-level specs.
- [Architecture §13 (deferred non-features)](../dev/architecture.md) — the "wait, don't guess" stance explained alongside the other deliberate non-features.

---

## Pre-meeting checklist (before the accountant arrives)

- [ ] **At least three hospitality clients** classified in the system, covering different `(legal_form, bookkeeping_system)` cells:
  - One DOO restaurant (dvojno implied).
  - One preduzetnik café on prosto knjigovodstvo.
  - One preduzetnik on dvojno (if the agency has one) — to confirm the carve-out works at runtime, not just in the matrix.
- [ ] **Real invoices in each client's `Fakture` tab** — at least 5 verified, including one with line items in multiple VAT rates (so kalkulacija column 10 has variety to show).
- [ ] **Product catalog populated** with selling prices + margins for at least 10 items belonging to one of the clients — so the kalkulacija report has end-to-end data to render.
- [ ] **Both Pravna forma and Sistem knjigovodstva set** for every demo client; the obligation card collapses to an "unclassified" prompt otherwise, which is a worse demo.
- [ ] **A printout of one legally-correct kalkulacija and one legally-correct DPU** the agency produces today (in Excel, or whatever their current tool is). We compare ours to theirs column by column.
- [ ] **A printout of one KEP page** from one of the agency's current hospitality clients. Same exercise — the legal form is only 5 columns but the *content* (zaduženje/razduženje source rows) is where reality lives.

---

## The hour, in order

Total budget: ~60 minutes. Two thirds is the accountant reacting to what we built; one third is open-ended workflow discovery.

### 0 → 5 min — Frame the meeting

Two-sentence pitch:

> "We've built the OCR + line-item pipeline and the classification model. Today we want you to tell us which forms are obligatory for which client profile, and what the column structure of each form needs to be. We've made guesses; please push back where we got it wrong."

State explicitly that **wrong guesses are the point of the meeting** — every "no, that column is different" the accountant gives saves a week of post-launch rework.

### 5 → 15 min — Validate the obligation matrix

Open `/klijenti/[id]` for the DOO restaurant. Point at the header chips: `DOO`, `Dvojno`. Scroll to the obligation card. The card shows:

| Form | Status |
|---|---|
| Kalkulacija | Available (pre-meeting) |
| KEP | Post-meeting |
| Cenovnik | Post-meeting |
| Popis | Post-meeting |
| DPU | **Not required** |
| PK-1 | **Not required** |

Ask:

1. Is this matrix correct for DOOs on dvojno?
2. Is **Mišljenje MF 011-00-761/2018-16** the legal basis you'd cite to a tax inspector, or is there a stronger one?
3. Do you ever produce DPU voluntarily for a DOO restaurant (e.g. internal control), or is "not required" literally "not produced"?

Switch to the preduzetnik café (prosto). Same card, different rows now show as required (DPU, PK-1). Ask:

4. Is the matrix correct for preduzetnici on prosto?
5. Do preduzetnici ever opt into dvojno? If so, are their obligations identical to a DOO's (i.e., we model `preduzetnik + dvojno` the same as `DOO`)?

Switch to the preduzetnik on dvojno. Confirm the carve-out fires. Ask:

6. Anything else we missed? Foreign-owned subsidiaries, social-enterprise structures, etc.?

**Expected outputs of this segment:**
- Definitive yes/no on every cell of the matrix.
- Any additional `legal_form` values we should add (`udruženje`, `zadruga`, etc.).
- Documentation of the legal-basis citation we use in customer support.

### 15 → 30 min — Walk the kalkulacija column structure

Open the kalkulacija report (existing endpoint, simplified columns today). Side-by-side with the accountant's printed kalkulacija from the same supplier invoice. Walk the 13 prescribed columns one by one:

1. Redni broj — does our auto-numbering match how they sequence it (per kalkulacija document or per fiscal year)?
2. Naziv robe — do they group by VAT rate within a single kalkulacija document, or one product per row regardless of VAT?
3. Jedinica mere — how often does the unit need manual override (Saldora extracts from the invoice, but suppliers are inconsistent)?
4. Nabavljena količina — straight from the line item; show ours matches theirs.
5. Nabavna cena po jedinici mere — net of rabat or gross? We currently extract the net. Confirm.
6. Nabavna vrednost — col 4 × col 5; show ours computes this.
7. **Zavisni troškovi** — the open question. How often is it non-zero in practice? When non-zero, what's the source (transport invoice from a different supplier, internal allocation, flat percentage)?
8. **Razlika u ceni (marža)** — applied to (col 6 + col 7). Per-product or per-client default? We have a `default_margin_pct` on the product catalog; is per-product right, or per-category, or both?
9. Prodajna vrednost bez PDV — sum of 6+7+8.
10. Stopa PDV — extracted from the invoice line.
11. Iznos PDV — col 9 × col 10.
12. Prodajna vrednost sa PDV — col 9 + col 11.
13. Prodajna cena po jedinici mere — col 12 ÷ col 4.

For each column, ask:
- Is this right?
- Is this where you actually look first when checking a kalkulacija (so we know what to surface at the top)?
- Is the formula correct, or do you do a different roll-up?

**Expected outputs of this segment:**
- A signed-off 13-column kalkulacija spec, with formulas.
- A decision on how to model markup (per-product default, per-client override, per-category default).
- A decision on `zavisni troškovi` UX (first-class field on every line vs. one-off override).
- A linkage spec: kalkulacija columns 6+7 → PK-1 col 12; col 8 → PK-1 col 14; col 11 → PK-1 col 15; col 12 → PK-1 col 16. Confirm this is how the agency actually transfers numbers today.

### 30 → 40 min — Walk the DPU / Šank lista column structure

Switch to the preduzetnik client. Open the DPU report. Side-by-side with their printed DPU. Walk:

- Col 5: Opening stock — where does it come from on day 1 of a new period (carried from previous day's col 8, or fresh popis)?
- Col 6: Received during the day — straight from invoices dated that day. Confirm.
- Col 7: Sum (col 5 + col 6) — confirm.
- Col 8: Closing stock by popis at end of day — **the central manual step**. Does the bookkeeper enter this from a paper count, a separate system, a fiscal POS export?
- Col 9: Consumed (col 7 − col 8) — automatic.
- Col 10: Sale price per unit with PDV — comes from kalkulacija column 13 / cenovnik. Confirm.
- Cols 11-12: Realised promet from konzumacija (drinks vs food, on-premises). Where does this come from — fiscal Z-report, manual entry, both?
- Col 13: Sale value of received quantities (col 6 × col 10) — automatic.

Ask:
- Is end-of-day popis literally daily, or is it weekly with daily estimates in between?
- For col 8 (closing popis), do bookkeepers ever skip a day and back-fill the missing row from sales data?

**Expected outputs of this segment:**
- A signed-off 9-column DPU spec.
- A decision on the daily-popis UX: full data entry per day, photo upload of the bar count, or fiscal-POS sync.
- A statement on how `kalkulacija → DPU col 10` links — instant when kalkulacija is regenerated, or snapshot per period?

### 40 → 50 min — KEP, cenovnik, popis

These three are unbuilt. We can't show a demo; instead, watch the accountant produce one of them today.

Ask the accountant to **share screen and walk through producing a KEP entry for a real client this week**. Capture:

- What tool? Excel? Their accounting software? Both?
- What's the input data — a daily Z-report from the POS, fiskalni račun stack, supplier invoices for the day?
- How is `zaduženje` (col 4) computed? It should equal the kalkulacija's col 12 (prodajna vrednost sa PDV) — confirm in practice.
- How is `razduženje` (col 5) computed? Fiscal-POS daily total + fakture issued + other prescribed events. What's the order of operations?
- How are corrections (greška/storno) entered?
- How does popis flow into KEP as višak/manjak?
- How frequent is the entry — daily, weekly, monthly?
- What's the pain point? (Look for the next 10× UX win.)

Same for cenovnik (probably trivial — Word document or POS export?) and popis (probably annual, manual count + Excel valuation).

**Expected outputs of this segment:**
- Workflow capture for KEP, cenovnik, popis.
- Confidence on whether KEP needs a fiscal-POS ingestion path (M20 sub-issue) or a Z-report upload widget (much simpler).
- Sense of whether popis should be a one-shot annual workflow or a recurring monthly one.

### 50 → 60 min — Monthly close + close-out

Last question. Without prompting: ask the accountant to **describe their month-end close for one hospitality client, in order, start to finish**. Listen for:

- Which form is generated first?
- Which forms are mailed/handed to the client, vs kept internally?
- What gets posted to MiniMax (or whatever GL system)?
- Where are the gotchas (the things they always have to check twice)?
- How long does the close take per client?

This becomes the spine of M21 (close checklist).

Then: thanks, offer them an early-access beta, schedule a follow-up after the spec is drafted.

---

## After the meeting

Within 24 hours:

- [ ] Convert each "Expected outputs of this segment" into a concrete artifact:
  - Updated obligation matrix in `app/services/hospitality_forms.py` (if anything moved).
  - Column specs for kalkulacija and DPU as docstrings inside `app/services/hospitality_forms_specs.py` (new file).
  - Workflow capture as a markdown doc under `docs/M20_workflows/`.
- [ ] Open GitHub issues for M20.1 (kalkulacija column refit), M20.2 (DPU column refit), M20.3 (KEP form generator), M20.4 (cenovnik generator), M20.5 (popis workflow). Each issue references the column spec / workflow capture and uses the agency's exact terminology.
- [ ] Email the accountant the meeting notes + a one-page summary; ask for any corrections within a week. Lock the spec.
- [ ] Add the new `legal_form` values (if any) to `LegalForm` literal in `apps/api/app/schemas/client.py` + the matching i18n keys.
- [ ] Add a `M20_meeting_recap.md` doc in `docs/` capturing the answers per question above — so the next person who joins the team sees the rationale, not just the spec.

---

## Notes on what *not* to do during the meeting

- **Don't ask for opinions on product design.** Ask only for facts about how forms work today and how the accountant actually produces them. Saldora's job is to translate workflow → software, not crowd-source UX.
- **Don't try to demo everything.** The DPU/kalkulacija walk is the dense part; the rest is observation, not demo.
- **Don't lock the spec in the meeting.** Send notes after, get written confirmation, then lock. People say things in a 60-minute window they reconsider with a day's distance.
- **Don't promise dates.** "We'll ship X by Y" anchors expectations the team can't always hit. Promise "we'll be back with a column-level spec for your review within 2 weeks" — that's true and binding without committing the engineering team.
