# Sample data

A small, **entirely synthetic** Romanian document set for testing the ingestion,
classification, extraction, and router pipeline described in `docs/`. Per
`docs/03-implementation-roadmap.md` Phase 1 ("synthetic/anonymized is fine"), this
was generated rather than sourced from a real business — no public Romanian
invoice/contract dataset with real documents exists, and a synthetic set lets every
example query in `docs/02-mvp-scope.md` have a real, checkable answer instead of
requiring hand-labeling after the fact.

All entities, CUIs, addresses, and CNPs below are fictional.

## Layout

- **`dump/`** — the actual ingestion input: **31 files, flat, no subfolders,
  deliberately messy/uninformative filenames** (`fff.txt`, `Document nou (2).txt`,
  `final.txt`, `atasament (1).txt`, ...). This mirrors what a real client hand-off
  looks like — an unsorted dump, not pre-sorted folders — per
  `docs/01-architecture.md`'s "no manual sorting required" ingestion design.
  **Feed this folder to the ingestion pipeline, not a type-labeled one** —
  classification must work from parsed document content, not from filename or
  folder location. Note: every file here is real, parseable text (or one real
  `.xlsx`) — none of them are actually scanned images despite some earlier naming
  suggesting otherwise; deliberately messy filenames test unsorted-dump handling,
  not OCR (see Format note below).
- **`manifest.json`** — the answer key: one entry per file in `dump/` giving
  `contains_financial_data` (a real boolean — the one thing the pipeline actually
  needs to decide, since it gates the Unstract-vs-Onyx routing fork) plus a broad
  `category` label and identifying fields (partner, date, invoice totals,
  employee). `category` is for human/report eyeballing only — the classifier's
  own `document_type` output is deliberately open text (see
  `ingestion/foldarai_ingestion/schema.py`), so there's no fixed taxonomy to score
  it against; `category` is not what the classifier is scored on. Kept separate
  from `dump/`, never fed to the pipeline.

## The fictional company

**Atelierul Verde SRL** — a small custom-furniture workshop in Cluj-Napoca
(CUI RO12345678). It buys raw materials (wood, hardware, paint, transport) from
suppliers and sells custom furniture to businesses and individuals.

| `category` in `manifest.json` (reporting only) | Count | `contains_financial_data` |
|---|---|---|
| `invoice` | 19 (14 purchases, 5 sales) | `true` |
| `contract` | 4 | `false` |
| `hr_document` | 2 | `false` |
| `email` | 5 | `false` |
| `accounting_register` (spreadsheet — see below) | 1 | `true` |

## Entities

**Suppliers (furnizori):**
- **Lemn Prod SRL** — raw wood. Framework contract, 5-business-day delivery term,
  6 invoices across the year.
- **Feronerie Est SRL** — furniture hardware. Framework contract, 3-day delivery
  term, 4 invoices, plus an email thread about an 8% price increase.
- **Transport Nord SRL** — freight. Framework contract, 2 invoices.
- **Vopsele Rapid SRL** — paint/varnish. **Deliberately has invoices but no signed
  contract** (only a one-off price-quote email) — this is the stress-test case from
  `docs/02-mvp-scope.md` ("invoices from suppliers we don't have a signed contract
  with").

**Clients (clienți):**
- **Mobilier Deco SRL** — recurring client; a large showroom-furniture order in
  June makes June the clear best month. Also has a sales contract (24-month
  warranty, 30-day execution term).
- **Cabinet de Avocatură Ionescu** — one-off order.
- **Popescu Andrei** — individual client, one-off order.

**Employees (HR):**
- **Ioana Pop** — Tâmplar (carpenter), notice period **20 zile lucrătoare**.
- **Mihai Georgescu** — Agent vânzări (sales), notice period **30 zile lucrătoare**.

**Edge case — `Registru facturi 2025.xlsx`:** an accounting register spreadsheet
mirroring the invoices. It's not one of the originally-illustrative MVP document
types (contract/invoice/hr_document/email) — included specifically to test that
classification is genuinely open-ended rather than forcing a bad-fit label onto
anything outside a small fixed list. Expected: `document_type` something like
"accounting register" or "invoice register", `contains_financial_data: true`
(it clearly is financial data, worth extracting).

## Ground truth (for validating pipeline output)

Recomputed from the data in `generate.py` (`pip install openpyxl && python3
generate.py`, regenerates `dump/` and `manifest.json` in place) — regenerate
before trusting if you edit the underlying records.

| Question | Expected answer |
|---|---|
| Most profitable month in 2025? | **June (2025-06)**, profit ≈ **38,113.54 RON** |
| Average invoice amount (all 19)? | ≈ **8,149.43 RON** |
| Total spent with Lemn Prod SRL? | **39,801.32 RON** |
| Notice period, Ioana Pop's contract? | **20 zile lucrătoare** |
| Delivery term, Lemn Prod SRL contract? | **5 zile lucrătoare** |
| Any supplier with invoices but no contract? | **Vopsele Rapid SRL** |
| Contracts active during the best month (June)? | Lemn Prod, Feronerie Est, Transport Nord, Mobilier Deco (all have date ranges covering June 2025) |

Maps directly to the example queries in `docs/02-mvp-scope.md` — use these as the
seed of the Phase 6 golden test set.

## Format note

Documents in `dump/` are plain `.txt` (contracts/HR/invoices/emails) and one real
`.xlsx`, not real PDFs/scans — sufficient for testing classification, extraction,
and routing logic, since Unstructured.io parses text content regardless of
container format. This does **not** exercise OCR/scan-quality risk (flagged in
`docs/05-risks-and-open-questions.md`) — that needs real or scanned documents,
which is explicitly a Phase 8 (real pilot) concern, not a Phase 1-4 one.
