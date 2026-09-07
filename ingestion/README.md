# Ingestion service (Phase 1)

Parse + classify: turns a dropped-in file into plain text (Unstructured.io)
and one structured label via a single OpenRouter LLM call. See
`docs/03-implementation-roadmap.md` Phase 1 and `docs/01-architecture.md`'s
ingestion pipeline section for the design this implements.

Plain HTTP calls, no LangChain/agent framework, no RAG — classification is a
single request/response, not a multi-step reasoning loop. See
`foldarai_ingestion/llm_client.py` for why.

**Classification is open-ended, not a fixed taxonomy.** `document_type` is
free text — the model answers "what is this document?" as specifically and
accurately as it can (a real client dump can contain anything: insurance
policies, permits, bank statements, meeting minutes, correspondence with
authorities, not just the 4 types used as MVP examples in `docs/02-mvp-scope.md`).
The one thing the pipeline actually needs as a closed decision is
`contains_financial_data` — whether this document should also go through
Unstract's structured extraction (the Unstract-vs-Onyx fork in
`docs/01-architecture.md` step 4). See `foldarai_ingestion/schema.py` for the
full reasoning.

## Layout

- `foldarai_ingestion/config.py` — env-based settings (`OPENROUTER_API_KEY`, `OPENROUTER_MODEL`)
- `foldarai_ingestion/schema.py` — the classification output shape (Pydantic model + JSON Schema for `response_format`): open-text `document_type` + `short_description`, plus the one real routing boolean `contains_financial_data`
- `foldarai_ingestion/llm_client.py` — the OpenRouter chat-completions call, with retry-with-backoff and a cross-provider fallback chain (`FALLBACK_MODELS`) since free-tier providers (Google AI Studio, NVIDIA's endpoint, ...) hit real transient overload in testing
- `foldarai_ingestion/parsing.py` — Unstructured.io wrapper (file → plain text)
- `foldarai_ingestion/classify.py` — parse + classify one file, flags low-confidence results for review
- `scripts/run_classification_eval.py` — runs classification over `sample-data/dump/`, scores `contains_financial_data` against `sample-data/manifest.json` (real ground truth, ≥90% target), and prints `document_type`/`short_description` for every file for manual eyeballing (open text isn't auto-scored — that's a qualitative call)

## Setup

```bash
cd ingestion
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # already done locally if .env exists — fill in a real OPENROUTER_API_KEY otherwise
```

## Run the classification eval

```bash
python scripts/run_classification_eval.py
```

Prints `document_type`/`short_description` per file (eyeball these against
`sample-data/README.md`'s entity list — that's the real "is this as accurate
as ChatGPT" check), plus `contains_financial_data` accuracy against the
`manifest.json` ground truth and whether it clears the ≥90% bar. Not yet run
for real — this is scaffolding; the model choice (`OPENROUTER_MODEL` in
`.env`, currently `nvidia/nemotron-3-super-120b-a12b:free` after
`google/gemma-4-31b-it:free` turned out to be congested — Google AI Studio's
shared free pool, not specific to this project) is a starting guess to
validate empirically here, not a final decision (see
`docs/05-risks-and-open-questions.md`).

## Not built yet

- No HTTP API (FastAPI) wrapping this — right now it's a library + CLI eval
  script, tested against `sample-data/`. Roadmap Phase 1 calls for a small
  FastAPI service accepting uploads; add that once classification accuracy
  is actually validated, rather than before.
- No Postgres persistence of `documents` rows yet (Phase 1/2 data model in
  `docs/01-architecture.md`).
- No structured extraction (Unstract, Phase 2) or semantic indexing (Onyx,
  Phase 3) — this only covers parse + classify.
