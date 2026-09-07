# Ingestion + router + Slack bot (fast end-to-end pass)

A thin, working version of the whole loop — ingest → classify → extract →
embed → route → answer, reachable from Slack — built to prove the pipeline
end to end quickly rather than to be the final architecture. See
**"Deferred: Onyx and Unstract"** below before assuming any of this is the
long-term design.

## ⚠️ Deferred: Onyx and Unstract

`docs/01-architecture.md` specifies **Onyx** (semantic search, chat/Slack UI,
embeddings) and **Unstract** (LLM-driven structured extraction) as the real
components for this. Neither is deployed. Instead, for this first
fast end-to-end pass:

| Docs' component | What's actually running instead | Where |
|---|---|---|
| Unstract (extraction) | One more direct LLM call, same pattern as classification | `foldarai_ingestion/extraction.py` |
| Onyx (embeddings) | A local embedding model (`intfloat/multilingual-e5-small`) writing straight into pgvector — no external API, avoids a second flaky free-tier dependency after the OpenRouter rate-limit issues | `foldarai_ingestion/embeddings.py` |
| Onyx (chat UI + Slack connector) | A small hand-rolled Slack app (Socket Mode) | `slack_bot.py`, `SLACK_BOT_SETUP.md` |
| LangGraph (router agent) | A fixed 3-step pipeline (route → run tool(s) → synthesize), not an agent loop — see the limitation noted in `router.py`'s docstring (sequential compound questions like "contracts active during our *best* month" need the semantic query to depend on the financial tool's result, which this can't do yet) | `foldarai_ingestion/router.py` |

**Come back and do the real integration** once this thin version proves the
loop works — swap in Onyx for embeddings/search/Slack/UI, Unstract for
extraction, and a real LangGraph agent for the router, per
`docs/01-architecture.md`. Also come back to: a dedicated read-only Postgres
role for the router's generated SQL (it currently runs as the `folderai`
owner role — see `router.py`'s `_validate_readonly_sql` docstring), and real
document chunking for long documents (`populate_sample_data.py` currently
embeds each whole document as a single chunk).

## Layout

- `foldarai_ingestion/config.py` — env settings: OpenRouter, Postgres, tenant id, Slack tokens
- `foldarai_ingestion/schema.py` — Pydantic models + JSON Schemas for classification and extraction output
- `foldarai_ingestion/prompts.py` — the classification and extraction system prompts
- `foldarai_ingestion/llm_client.py` — generic structured-output OpenRouter call: retry-with-backoff, cross-provider fallback chain, markdown-fence-stripping JSON parsing
- `foldarai_ingestion/parsing.py` — Unstructured.io wrapper (file → plain text)
- `foldarai_ingestion/classify.py` — classification (Phase 1)
- `foldarai_ingestion/extraction.py` — invoice field extraction (Phase 2 stand-in)
- `foldarai_ingestion/embeddings.py` — local embedding model (Onyx stand-in)
- `foldarai_ingestion/db.py` — Postgres schema + persistence + pgvector similarity search, plain SQL
- `foldarai_ingestion/router.py` — the two-tool router + answer synthesis (Phase 4 stand-in)
- `scripts/init_db.py` — creates the tables
- `scripts/populate_sample_data.py` — runs the full pipeline over `sample-data/dump/` into Postgres
- `scripts/run_classification_eval.py` — classification-only accuracy check against `sample-data/manifest.json`
- `scripts/ask.py` — ask the router a question from the CLI (no Slack needed)
- `slack_bot.py` / `SLACK_BOT_SETUP.md` — the Slack bot and how to set it up

## Setup

```bash
cd ingestion
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
directly (`scripts/ask.py`) against 3 of the documented example queries in
`docs/02-mvp-scope.md` — all correct, matching `sample-data/README.md`'s
ground truth exactly:
- "Most profitable month in 2025?" → June, 38,113.54 RON (exact match)
- "Notice period, Ioana Pop's contract?" → 20 zile lucrătoare, correctly cited to the source file
- "Total spent with Lemn Prod SRL?" → 39,801.32 RON (exact match)

Note: the system clock is well past `sample-data/`'s 2025 timeframe, so
phrase test questions with an explicit year ("in 2025") - an unscoped "this
year" resolves against the real current date and correctly finds nothing.

Not yet tested: the compound/refusal example queries, and the Slack bot
itself (needs your own Slack app credentials - see `SLACK_BOT_SETUP.md`).

## Classification-only eval

```bash
python scripts/run_classification_eval.py
```

Scores `contains_financial_data` against `sample-data/manifest.json` (real
ground truth, ≥90% target) and prints `document_type`/`short_description`
per file for manual eyeballing (open text isn't auto-scored — see
`foldarai_ingestion/schema.py`). Already run for real once — 100% on
`contains_financial_data`, qualitatively accurate open-text labels.
`OPENROUTER_MODEL` in `.env` is currently `nvidia/nemotron-3-super-120b-a12b:free`
(a starting guess, not a final decision — see `docs/05-risks-and-open-questions.md`).
