# FoldarAI

**Drop your business documents in a folder. Ask anything. Get answers with sources — whether the question is "what did we agree with Supplier X" or "what was our most profitable month."**

FoldarAI is a self-serve document intelligence assistant for Romanian small businesses and solo entrepreneurs. It ingests whatever a business already has lying around — contracts, invoices, HR files, emails, notes — automatically classifies and structures it, and answers questions over it through a chat interface and a Slack bot. It answers both qualitative questions (retrieved from document text) and quantitative/financial questions (computed from structured data extracted out of those same documents), routed automatically to whichever is correct.

This folder is the planning package for the project: the problem it solves, the architecture, the MVP scope, the build roadmap, the business/pricing model, and the open risks. It's written to serve two purposes at once:

1. **A thinking tool for the founder** — to pressure-test the idea and have an actual plan instead of a vague pitch.
2. **An implementation brief for engineering agents** — concrete enough that an agent (human or AI) could pick up any one document and start building without needing the full backstory re-explained.

## Reading order

| Doc | What it covers |
|---|---|
| [00-overview.md](./00-overview.md) | The problem, who it's for, why it's a real gap and not "yet another RAG demo," what FoldarAI explicitly is *not* |
| [01-architecture.md](./01-architecture.md) | Full technical architecture: components, licenses, data flow, data model, LLM strategy, deployment model |
| [02-mvp-scope.md](./02-mvp-scope.md) | What's in and out of the MVP, concrete example queries the MVP must answer correctly, definition of done |
| [03-implementation-roadmap.md](./03-implementation-roadmap.md) | Phased build plan from an empty repo to a working MVP, with exit criteria per phase |
| [04-business-context.md](./04-business-context.md) | Target customer, competitive landscape, pricing model and margin math, delivery models, go-to-market |
| [05-risks-and-open-questions.md](./05-risks-and-open-questions.md) | Licensing nuances, accuracy/privacy risks, and decisions still to be made before/during the build |

## One-paragraph summary

Every existing tool solves half of this problem. Onyx (open source, MIT) does excellent semantic search and chat over documents, but has no structured financial analytics. Enterprise tools that *do* combine structured and unstructured analysis (Hebbia, AlphaSense, DataSnipper) are priced and built for hedge funds and audit firms, not a shop owner with a folder of invoices. FoldarAI fills that specific, real, unfilled gap: an affordable, self-hosted-per-client, fully open-source-stack product that automatically classifies whatever a small business drops in, extracts the numbers into a real database, keeps the narrative content searchable, and uses an LLM tool-calling agent to route each question to the right retrieval method — automatically composing an answer from both when a question needs it.
