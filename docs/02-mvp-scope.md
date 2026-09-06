# 02 — MVP Scope

## Scope decision

The MVP targets the **full original vision from day one**: a client can drop in contracts, invoices, HR documents, and emails together, unsorted, and query across all of them. This is a deliberately broader MVP than the narrowest possible slice (which would have been invoices + contracts only) — the tradeoff accepted here is more classification edge cases and more surface area to get right before the first demo, in exchange for the MVP actually matching the "drop literally anything" pitch instead of a narrower proof of concept.

To manage that risk, the **implementation roadmap** ([03-implementation-roadmap.md](./03-implementation-roadmap.md)) still builds and validates incrementally — invoices and contracts first, since together they exercise both pipelines (structured + semantic) end to end, then HR documents and emails are added as additional classification categories on top of the same pipeline rather than as separate architecture. The *scope target* is broad; the *build order* is incremental.

## In scope for MVP

- **Ingestion of four document types:** contracts, invoices, HR documents (employment contracts, onboarding paperwork), and emails (as exported files, e.g. `.eml` or pasted/forwarded text — live email inbox integration is out of scope, see below).
- **Automatic classification** of each dropped-in document into one of the above types (or an `unclassified` fallback with lower confidence, flagged for review rather than silently guessed).
- **Structured extraction** of invoices into a defined schema (vendor, date, amount, currency, line items) stored in Postgres.
- **Semantic indexing** of contracts, HR documents, and emails into the vector store with citation metadata (source file, date, parties).
- **A router agent** that answers both semantic and financial-aggregation questions, and compound questions requiring both, with sources cited in every answer.
- **Two access channels:** a web chat UI and a Slack bot (both provided by Onyx out of the box).
- **Single-tenant-per-deployment** isolation (one Docker Compose stack per client) — no in-app multi-user permissioning beyond "this whole bot belongs to this one client" for MVP (see non-goals in [00-overview.md](./00-overview.md)).
- **A visible disclaimer** on financial/quantitative answers and a way to inspect the underlying data (e.g. "show me the invoices this number came from").
- **A lightweight human review step** for low-confidence classifications during onboarding, rather than fully blind automation (see [05-risks-and-open-questions.md](./05-risks-and-open-questions.md)).

## Out of scope for MVP (explicitly deferred)

- Live inbox integration (IMAP/Gmail/Outlook sync) — start with exported/forwarded email files.
- Live folder sync (Google Drive/Dropbox connectors) — start with manual upload through a simple portal.
- Accounting software integrations (Oblio, SmartBill, SAGA).
- True on-premise/client-hosted delivery (start with you-hosted, isolated-per-client — see [01-architecture.md](./01-architecture.md)).
- Local/self-hosted LLM inference (start with a cloud API — see LLM strategy in [01-architecture.md](./01-architecture.md)).
- Multi-user, role-based permissions within a single client's bot (e.g. "employees can't see payroll documents") — the MVP assumes the deployed bot serves one trusted owner/small team; document-level access control inside a tenant is a real feature but a post-MVP one.
- Any language beyond Romanian and English documents.
- A formal eval harness dashboard (a golden test set should exist and be checked manually during development — see roadmap Phase 6 — but a tracked, automated eval pipeline with historical scoring is a fast-follow, not a blocker for the first working demo).

## Concrete example queries the MVP must answer correctly

These double as acceptance tests and as the seed of the eval golden set mentioned in [03-implementation-roadmap.md](./03-implementation-roadmap.md). Each should be tested against a realistic (anonymized or synthetic) set of documents covering all four types.

**Pure semantic (routed to `search_documents`):**
- "What did we agree with [Supplier X] about delivery terms?"
- "What's the notice period in [Employee Y]'s contract?"
- "Did we ever discuss pricing changes with [Supplier Z] over email?"

**Pure structured/financial (routed to `query_financials`):**
- "What was our most profitable month this year?"
- "How much did we spend on [Vendor]'s invoices in total?"
- "What's our average invoice amount?"

**Compound (requires both tools, composed):**
- "Which contracts were active during our best month?"
- "Are there any invoices from suppliers we don't have a signed contract with?" (this one is a genuinely good stress test — it requires cross-referencing structured invoice vendor names against the set of contracts found via semantic search)

**Should be refused or hedged, not hallucinated:**
- A question whose answer isn't grounded in any ingested document or extractable data point — the agent must say so rather than fabricate a plausible-sounding number or quote.

## Definition of done for MVP

The MVP is done when:
1. A single client's full document set (contracts + invoices + HR docs + emails) can be dropped in and classified automatically with a reasonable review workflow for low-confidence cases.
2. All of the example queries above are answered correctly, with citations, against that client's real (or realistic synthetic) data.
3. The bot is reachable through both the web chat UI and Slack.
4. The whole stack runs from one `docker-compose up` for a new client, hosted on the target EU infrastructure.
5. One real (or one convincingly realistic pilot) small business has used it and given feedback.
