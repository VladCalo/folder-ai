# 03 — Implementation Roadmap

This is the build order from an empty repo to the MVP defined in [02-mvp-scope.md](./02-mvp-scope.md). Each phase has a goal, concrete tasks, and exit criteria — an implementation agent should be able to pick up one phase and execute it without needing the rest of this document explained.

Build order is incremental even though the MVP's target scope is broad (see [02-mvp-scope.md](./02-mvp-scope.md)): prove the hybrid structured+semantic architecture end to end on the two document types that exercise both pipelines (invoices, contracts) before adding the remaining classification categories (HR documents, emails), which reuse the same pipeline rather than requiring new architecture.

---

### Phase 0 — Environment and infrastructure skeleton

**Goal:** every underlying open-source component runs standalone before any custom code is written.

- Set up the repo structure (suggested: `/ingestion`, `/router`, `/infra` for Docker Compose files, `/docs` — this planning folder can move under `/docs` once implementation starts).
- Stand up Postgres, Qdrant (or confirm `pgvector` extension approach instead), Onyx, and Unstract each via their own official Docker images, wired together in one `docker-compose.yml`.
- Verify: Onyx's web UI loads and can answer a question over a manually uploaded test document. Unstract's UI/API can run a basic extraction workflow against a sample invoice. Postgres and the vector store are reachable from a local script.
- **Exit criteria:** all four services run together via `docker-compose up`, each independently verified working with its own default example, no custom code involved yet.

### Phase 1 — Ingestion pipeline: parsing and classification

**Goal:** any dropped-in file becomes parsed text plus a reliable `document_type` label.

- Build a small ingestion service (Python/FastAPI) that accepts an uploaded file, calls Unstructured.io to parse it into elements, and stores the raw parsed text.
- Build the classification step: one LLM call (structured output / function-calling with a fixed schema: `{document_type, confidence, parties_involved, date_mentioned}`) against the parsed text (or just its first page/first N elements, for cost and latency).
- Assemble a small labeled test set (10-20 documents per type: contract, invoice, HR document, email) — synthetic/anonymized is fine — and measure classification accuracy against it before moving on.
- Add the low-confidence review path: anything below a chosen confidence threshold is flagged rather than silently routed.
- **Exit criteria:** ≥90% correct classification on the test set across all four document types, with low-confidence cases correctly flagged instead of silently misrouted.

### Phase 2 — Structured extraction path (invoices)

**Goal:** invoices become trustworthy rows in Postgres.

- Configure an Unstract workflow for invoices with the schema defined in [01-architecture.md](./01-architecture.md) (vendor, date, amount, currency, line items).
- Write the extracted JSON into the `invoices` / `invoice_line_items` tables, tagged with `tenant_id` and a link back to the source `documents` row.
- Validate extraction accuracy against the same labeled test set's invoices — check amounts and dates specifically, since these feed financial aggregation answers downstream and errors here are the highest-consequence failure mode in the whole system.
- **Exit criteria:** extracted invoice totals and dates are verified correct against ground truth for the test set; extraction confidence is stored per record so low-confidence extractions can be flagged the same way low-confidence classifications are.

### Phase 3 — Semantic path (contracts, then HR docs and emails)

**Goal:** qualitative documents are chunked, embedded, and retrievable with citations.

- Route classified contracts into Onyx's ingestion (via its API/connector for uploaded files), tagged with the same metadata (document type, date, parties, tenant).
- Verify retrieval quality on the semantic example queries from [02-mvp-scope.md](./02-mvp-scope.md) — check that answers cite the correct source document, not just that they sound plausible.
- Once contracts work end to end, add HR documents and then emails as additional classification categories through the identical pipeline — this should require no new architecture, only extending the classification schema and adding test documents of each type.
- **Exit criteria:** all semantic example queries from [02-mvp-scope.md](./02-mvp-scope.md) answered correctly with correct citations, across all three qualitative document types.

### Phase 4 — Router agent

**Goal:** one agent correctly decides between semantic search, SQL query, or both, and composes multi-part answers.

- Build the LangGraph ReAct agent with the two tools described in [01-architecture.md](./01-architecture.md): `search_documents` (wraps Onyx's retrieval API) and `query_financials` (a text-to-SQL agent — LangChain's SQL agent toolkit or Vanna.ai — against the Postgres tables from Phase 2).
- Write clear, distinct tool descriptions — this is what the LLM uses to decide which tool to call, so ambiguous descriptions directly cause routing mistakes.
- Test against **all** the example queries in [02-mvp-scope.md](./02-mvp-scope.md), including the compound ones and the "should refuse" case. The compound and refusal cases are the ones most likely to fail first and are worth disproportionate testing time.
- **Exit criteria:** every example query in [02-mvp-scope.md](./02-mvp-scope.md) is answered correctly, including correctly refusing to answer the ungrounded question rather than fabricating a response.

### Phase 5 — UI and channels

**Goal:** a client can actually use this without you running scripts for them.

- Wire the router agent in as the backend behind Onyx's chat UI and Slack bot (Onyx supports custom/pluggable backends and agents — confirm the current integration point in its docs at implementation time, since this is exactly the kind of detail that shifts between versions).
- Add a simple upload portal for the ingestion pipeline (doesn't need to be polished — a basic authenticated file upload is sufficient for MVP).
- Ensure every answer displays its source(s): document name/link for semantic answers, the underlying query/rows for financial answers.
- Add the disclaimer language for financial/quantitative answers.
- **Exit criteria:** a non-technical person can upload documents through the portal and ask questions through Slack or the web chat without any manual intervention from you.

### Phase 6 — Evaluation harness (lightweight, MVP-appropriate)

**Goal:** confidence that answers are trustworthy, and a way to measure regressions as the pipeline changes.

- Turn the example queries and labeled test documents from earlier phases into a small persistent golden test set (question, expected answer or expected cited source, expected tool route).
- Run this set after any change to the classification prompt, extraction schema, or router tool descriptions — manually at MVP stage is acceptable; an automated CI-style eval run (e.g. with RAGAS or a custom scorer) is a natural fast-follow once this is proven valuable.
- This is also the single highest-leverage piece of the project for the portfolio/CV story (see the original framing in project discovery) — it demonstrates the difference between a demo and a system whose accuracy is actually measured.
- **Exit criteria:** a documented, re-runnable golden test set exists and passes at an acceptable rate before onboarding a real client.

### Phase 7 — Multi-tenant packaging and deployment

**Goal:** ship a new client stack quickly and safely.

- Parameterize the Docker Compose bundle so a new client's isolated stack (their own Postgres, vector store, Onyx instance, router service) can be provisioned from one command/script, with `tenant_id` wired through consistently (this was already reflected in the data model in [01-architecture.md](./01-architecture.md) — don't retrofit it later).
- Deploy the first instance to the target EU infrastructure (e.g. Hetzner) as described in [01-architecture.md](./01-architecture.md).
- Set up basic backup (database dumps) and monitoring (is the stack up, are LLM API calls failing) — minimal but non-zero; this is client data, not a personal side project.
- **Exit criteria:** a second, independent client stack can be stood up from the same tooling without manual one-off changes to the first.

### Phase 8 — Pilot with a real client

**Goal:** validate the whole thing against reality, not synthetic test data.

- Onboard one real (or one very realistic volunteer pilot) Romanian small business.
- Run their actual documents through the full pipeline, review classification/extraction accuracy on real messy data (which will differ from the clean test set — expect this and budget time for it), and gather direct feedback on both the answers and the onboarding experience.
- Feed anything learned back into the golden test set from Phase 6.
- **Exit criteria:** the pilot client is using the bot for real questions and confirms the answers are accurate and useful; feedback is incorporated.

---

## Notes for implementation agents

- Phases 0-4 are the technical core and can mostly be built and tested without a real client or real business documents — use synthetic/anonymized Romanian-language sample documents throughout.
- Do not modify Unstract's own source code (see the AGPL note in [01-architecture.md](./01-architecture.md)) — treat it strictly as an external service called over its API.
- `tenant_id` scoping (Postgres rows and vector metadata) should be present from Phase 1 onward even though the MVP deploys one isolated stack per client — it's cheap to add now and expensive to retrofit if the deployment model ever changes.
- Prioritize getting invoice date/amount extraction accuracy right in Phase 2 above almost everything else in the roadmap — it's the input to every financial answer downstream, and it's the failure mode most likely to produce a confidently wrong answer to a business owner.
