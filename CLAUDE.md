# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository state

This repo currently contains **no implementation code** — only the planning package for FoldarAI in `docs/`. There is no build system, lint config, test suite, or `docker-compose.yml` yet. Do not assume commands like `npm test` or `docker-compose up` work; they don't exist until Phase 0 of the roadmap is built (see below). When implementation starts, this file should be updated with real build/lint/test commands.

## What FoldarAI is

FoldarAI is a self-serve document intelligence assistant for Romanian small businesses: drop in a folder of business documents (contracts, invoices, HR files, emails), and query them via chat/Slack. It answers both qualitative questions (retrieved via semantic search over document text) and quantitative/financial questions (computed from structured data extracted from those same documents), with a router agent deciding automatically which path — or both — a question needs.

The full plan lives in `docs/`, written to be read in order:

| Doc | Covers |
|---|---|
| `docs/00-overview.md` | The problem, target user, why the gap is real, explicit non-goals |
| `docs/01-architecture.md` | Components/licenses, system diagram, ingestion/query pipelines, data model, LLM strategy, deployment model |
| `docs/02-mvp-scope.md` | In/out of scope, concrete example queries the MVP must answer, definition of done |
| `docs/03-implementation-roadmap.md` | Phase-by-phase build plan (Phase 0 → Phase 8) with exit criteria per phase |
| `docs/04-business-context.md` | Target customer, competitive landscape, pricing/margin math, go-to-market |
| `docs/05-risks-and-open-questions.md` | Licensing nuances, accuracy/privacy risks, decisions still open |

**Read the relevant doc before proposing architecture or scope changes** — most "obvious" alternatives (narrower MVP, different vector store, building a router by hand instead of via LLM tool-calling) were already considered and the reasoning is recorded there.

## Architecture (once implementation starts)

**Design principle: compose proven open-source components; build only the glue.** Don't reimplement parsing, OCR, extraction, or semantic search — those are solved by existing components below. The genuinely custom work is the classification/routing layer and multi-tenant packaging.

| Component | Role | License | Constraint |
|---|---|---|---|
| Unstructured.io | Parses 60+ file types into typed elements (OCR, layout) | Apache 2.0 | — |
| Unstract | LLM-driven structured extraction to JSON schema | AGPL-3.0 (OSS edition) | **Call over its API only — never fork/modify its source.** Network-copyleft only triggers on modifying+redistributing it. |
| Onyx (formerly Danswer) | Semantic search, chat UI, Slack bot | MIT (Community Edition) | CE has everything needed; paid tier only gates SSO/SAML (irrelevant at this scale) |
| Postgres | Structured financial data + tenant metadata; optionally the vector store via `pgvector` | PostgreSQL License | — |
| Qdrant (or `pgvector`) | Vector store for embedded chunks | Apache 2.0 | Choice still open — see `docs/05-risks-and-open-questions.md` |
| LangGraph | Router agent (ReAct tool-calling over `search_documents` / `query_financials`) | MIT | This is the custom "brain" — built on top of, not replaced |
| Docker / Docker Compose | One stack per client | Apache 2.0 | — |

**Routing is native LLM tool-calling, not a hand-built classifier.** The router agent gets two tools with clear natural-language descriptions and decides itself which to call, in what order, and how to compose multi-step answers (e.g. "which contracts drove our best month?" → `query_financials` then `search_documents` then synthesize). Tool descriptions are what the LLM uses to route — ambiguous descriptions directly cause routing bugs.

**Every answer must cite its source** — the document(s) for semantic answers, the SQL query/rows for financial answers. This is a hard requirement, not UI polish: see the hallucination-risk discussion in `docs/05-risks-and-open-questions.md`.

**`tenant_id` scoping** must be present on every Postgres row and vector-store metadata entry from the first line of ingestion code, even though the MVP deploys one fully isolated stack (separate containers/DBs) per client. Cheap to add now, expensive to retrofit.

**Do not modify Unstract's source.** Call it strictly as an external service over its API — see the AGPL note above.

## Build order

Implementation is incremental even though the MVP's target scope is broad (all four document types from day one). Build order, per `docs/03-implementation-roadmap.md`:

0. Stand up Postgres, Qdrant/pgvector, Onyx, Unstract via Docker Compose — verify each independently, no custom code.
1. Ingestion service: parse (Unstructured.io) + classify (`document_type`, confidence, parties, date) via one LLM call. Target ≥90% accuracy on a labeled test set; flag low-confidence rather than silently misroute.
2. Structured extraction (invoices → Postgres via Unstract). Get date/amount extraction right above almost everything else — it's the input to every financial answer downstream and the highest-consequence failure mode.
3. Semantic path (contracts, then HR docs, then emails into Onyx/vector store) — later document types reuse the same pipeline, no new architecture.
4. Router agent (LangGraph ReAct, two tools) — test against every example query in `docs/02-mvp-scope.md`, especially the compound and "should refuse" cases.
5. UI/channels (Onyx web chat + Slack), upload portal, source citations, financial-answer disclaimer.
6. Lightweight eval harness — turn example queries + labeled docs into a re-runnable golden set; re-run after any prompt/schema/router change.
7. Multi-tenant packaging — parameterize Compose bundle so a second client stack stands up with no manual one-off changes.
8. Real pilot client.

## Non-goals (do not build these into the MVP)

- Tax/legal advice — answers are scoped to the client's own documents only.
- A bookkeeping/accounting system replacement, or accounting-software integrations (Oblio, SmartBill, SAGA).
- Any language/market beyond Romanian + English, RON currency.
- Live inbox sync (IMAP/Gmail) or live folder sync (Drive/Dropbox) — MVP uses manual upload / exported files.
- Multi-user role-based permissions within one client's deployment (e.g. hiding payroll docs from some employees).
- SSO/SAML, enterprise audit tooling, true client-hosted on-prem delivery — all explicitly deferred past MVP.
