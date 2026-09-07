# Backend — ingestion + router + Slack bot (fast end-to-end pass)

A thin, working version of the whole loop — ingest → classify → extract →
embed → route → answer, reachable from Slack — built to prove the pipeline
end to end quickly rather than to be the final architecture. See
**"Deferred: Onyx and Unstract"** below before assuming any of this is the
long-term design.

Named `backend/`, not `ingestion/`, because it holds both halves of
`docs/03-implementation-roadmap.md`'s suggested `/ingestion` and `/router`
split, plus the Slack bot — see Layout below for how those map to the
`foldarai` package's structure.

## ⚠️ Deferred: Onyx and Unstract

`docs/01-architecture.md` specifies **Onyx** (semantic search, chat/Slack UI,
embeddings) and **Unstract** (LLM-driven structured extraction) as the real
components for this. Neither is deployed. Instead, for this first
fast end-to-end pass:

| Docs' component | What's actually running instead | Where |
|---|---|---|
| Unstract (extraction) | One more direct LLM call, same pattern as classification | `foldarai/ingestion/extraction.py` |
| Onyx (embeddings) | A local embedding model (`intfloat/multilingual-e5-small`) writing straight into pgvector — no external API, avoids a second flaky free-tier dependency after the OpenRouter rate-limit issues | `foldarai/embeddings.py` |
| Onyx (chat UI + Slack connector) | A small hand-rolled Slack app (Socket Mode) | `slack_bot.py`, `SLACK_BOT_SETUP.md` |
| LangGraph (router agent) | A fixed 3-step pipeline (route → run tool(s) → synthesize), not an agent loop — see the limitation noted in `foldarai/router/answer.py`'s docstring (sequential compound questions like "contracts active during our *best* month" need the semantic query to depend on the financial tool's result, which this can't do yet) | `foldarai/router/answer.py` |

**Come back and do the real integration** once this thin version proves the
loop works — swap in Onyx for embeddings/search/Slack/UI, Unstract for
extraction, and a real LangGraph agent for the router, per
`docs/01-architecture.md`. Also come back to: a dedicated read-only Postgres
role for the router's generated SQL (it currently runs as the `folderai`
owner role — see `foldarai/router/sql_safety.py`'s docstring), and real
document chunking for long documents (`populate_sample_data.py` currently
embeds each whole document as a single chunk).

## Layout

`foldarai/` is one Python package, split into subpackages by *when* code
runs — `ingestion/` (triggered by a document arriving) vs. `router/`
(triggered by a question arriving) — with genuinely shared infra at the
package's top level. Within each part, files are organized by *kind of
thing*: every system prompt lives in `prompts.py`, every data shape in
`schema.py`, regardless of which part uses it — keeps each concern in
exactly one place and keeps orchestration modules short enough to read top
to bottom.

**Shared** (used by both ingestion and the router):
- `foldarai/config.py` — env settings: OpenRouter, Postgres, tenant id + company name, Slack tokens
- `foldarai/schema.py` — every Pydantic model + JSON Schema (classification, extraction, and the router's route/SQL/answer shapes)
- `foldarai/prompts.py` — every system prompt (classification, extraction, and the router's route/SQL/synthesis prompts)
- `foldarai/llm_client.py` — generic structured-output OpenRouter call: retry-with-backoff, cross-provider fallback chain, markdown-fence-stripping JSON parsing
- `foldarai/db.py` — Postgres schema + persistence + pgvector similarity search, plain SQL
- `foldarai/embeddings.py` — local embedding model (Onyx stand-in) — writes at ingest time, reads at query time, hence shared rather than living in either subpackage

**`foldarai/ingestion/`** (runs when a document arrives):
- `parsing.py` — Unstructured.io wrapper (file → plain text)
- `classify.py` — classification (Phase 1)
- `extraction.py` — invoice field extraction (Phase 2 stand-in for Unstract)

**`foldarai/router/`** (runs when a question arrives):
- `sql_safety.py` — the read-only/tenant-scoping check on generated SQL, isolated since security-sensitive code deserves to be easy to find and audit on its own
- `tools.py` — the two tools (`run_financial_tool`, `run_semantic_tool`) — the exact call sites to swap when Onyx/Unstract get integrated for real
- `answer.py` — orchestration only: route decision → run tool(s) → synthesize (Phase 4 stand-in)

**Entry points:**
- `scripts/init_db.py` — creates the tables
- `scripts/populate_sample_data.py` — runs the full pipeline over `sample-data/dump/` into Postgres
- `scripts/run_classification_eval.py` — classification-only accuracy check against `sample-data/manifest.json`
- `scripts/ask.py` — ask the router a question from the CLI (no Slack needed)
- `slack_bot.py` / `SLACK_BOT_SETUP.md` — the Slack bot and how to set it up

## Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt   # includes sentence-transformers/torch - takes a few minutes
cp .env.example .env              # already done locally if .env exists
```

Postgres is on the rpi5 cluster, not local — reach it via port-forward
(separate terminal, kept running):
```bash
kubectl config use-context admin@rpi5
kubectl -n postgres port-forward svc/postgres 5432:5432
```

## Run it end to end

```bash
python scripts/init_db.py
python scripts/populate_sample_data.py     # classify + extract + embed all of sample-data/dump/
python scripts/ask.py "What was our most profitable month this year?"
```

Then, once you've set up a Slack app (`SLACK_BOT_SETUP.md`):
```bash
python slack_bot.py
```

## Status: validated end to end

All 31 `sample-data/dump/` files ingested successfully. Tested the router
directly (`scripts/ask.py`) against all 5 documented example-query
categories in `docs/02-mvp-scope.md`:
- Pure financial: "Most profitable month in 2025?" → June, 38,113.54 RON (exact match)
- Pure semantic: "Notice period, Ioana Pop's contract?" → 20 zile lucrătoare, correctly cited to the source file
- Financial aggregation: "Total spent with Lemn Prod SRL?" → 39,801.32 RON (exact match)
- Compound: "Which contracts were active during our best month?" → correctly **refused** rather than fabricate an answer (the known router limitation - the financial sub-query came back inconclusive - but it degraded safely instead of confidently guessing)
- Refusal: "How much do we pay for office rent in Bucharest?" → correctly refused, citing that no document mentions rent

All correct or safely-refusing, no hallucinated numbers/facts observed.

Note: the system clock is well past `sample-data/`'s 2025 timeframe, so
phrase test questions with an explicit year ("in 2025") - an unscoped "this
year" resolves against the real current date and correctly finds nothing.

Not yet tested: the Slack bot itself (needs your own Slack app credentials
- see `SLACK_BOT_SETUP.md`).

Restructured (`ingestion/` → `backend/`, package split into
`foldarai/ingestion/` + `foldarai/router/`) after this was validated —
re-verified working with the same 3 questions post-restructure.

## Classification-only eval

```bash
python scripts/run_classification_eval.py
```

Scores `contains_financial_data` against `sample-data/manifest.json` (real
ground truth, ≥90% target) and prints `document_type`/`short_description`
per file for manual eyeballing (open text isn't auto-scored — see
`foldarai/schema.py`). Already run for real once — 100% on
`contains_financial_data`, qualitatively accurate open-text labels.
`OPENROUTER_MODEL` in `.env` is currently `nvidia/nemotron-3-super-120b-a12b:free`
(a starting guess, not a final decision — see `docs/05-risks-and-open-questions.md`).
