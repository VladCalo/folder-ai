# 00 — Overview

## The problem

Small Romanian businesses and solo entrepreneurs accumulate a pile of documents as a byproduct of just operating: signed contracts, supplier invoices, employee paperwork, email threads, meeting notes, drafts of ideas. None of it is organized. Most of it is never looked at again unless something goes wrong (a dispute, a tax audit, a "wait, what did we agree to?" moment).

Two things they can't currently do without real effort:

1. **Ask a qualitative question about their own documents** — "What did we agree with Supplier X about delivery terms?" "What's in the employment contract with [employee]?" — and get an answer with the actual source cited, instead of digging through folders themselves or paying someone to.
2. **Ask a quantitative question that requires aggregating numbers across many documents** — "What was our most profitable month?" "How much did we spend on packaging this year?" — which requires the numbers to have been extracted from the documents into a structured, queryable form in the first place. Most small businesses without proper bookkeeping software have no such structured record at all; the numbers only exist scattered across PDFs.

General-purpose tools don't solve this. ChatGPT/Claude have no access to a business's private documents. And the tools that *do* combine structured and unstructured analysis are built and priced for hedge funds and audit teams (see [04-business-context.md](./04-business-context.md) for the competitive landscape), not for a shop owner or a freelancer.

## Who this is for

- Solo entrepreneurs and micro/small businesses in Romania (roughly 1–50 employees) with no dedicated IT department and no full-time accountant on staff (or one who only touches formal bookkeeping, not the surrounding paperwork).
- Businesses that already have a real folder of digital documents (or scanned paper ones) — this is not for a business starting from zero paperwork.
- Businesses sensitive to where their data lives — contracts and financials are exactly the kind of content an owner is uneasy uploading to a generic cloud AI tool with no data-residency guarantees. This is a real selling point, not a footnote (see the deployment model in [01-architecture.md](./01-architecture.md)).

## Why this is a genuine gap, not a rebuilt wheel

This was checked deliberately before committing to the idea (full detail in [04-business-context.md](./04-business-context.md)):

- **Onyx** (open source, MIT-licensed Community Edition) is an excellent, self-hostable semantic search + chat + Slack bot over documents. It does not do structured financial extraction or SQL-style aggregation — it cannot answer "what was our most profitable month."
- **Unstructured.io** and **Unstract** (open source document parsing/extraction tools) solve the ingestion and structured-extraction half well, but are infrastructure components, not a product — nobody has wired them together with a semantic search tool and a query router into one thing a small business owner can just use.
- **Hebbia, AlphaSense, DataSnipper, SageX** and similar tools genuinely do combine structured and unstructured analysis — but they are enterprise-priced, built for financial analysts and auditors, and assume a level of technical sophistication and budget a small Romanian business does not have.

The gap is specific: **no self-hostable, affordable, zero-configuration product exists where a small business owner drops an unsorted folder of mixed documents in and gets one bot that correctly answers both kinds of questions.** That's what FoldarAI is.

None of the individual techniques are novel — document classification, structured extraction, vector search, and text-to-SQL agentic routing are all solved problems with mature open-source tooling (see [01-architecture.md](./01-architecture.md)). The engineering and product work is in **composing** them correctly and packaging the result for a customer segment the existing tools ignore.

## Product vision (elevator pitch)

> Drop everything — contracts, invoices, HR files, emails, notes — into one place. FoldarAI reads it, sorts it, and turns it into a chatbot (web + Slack) that answers your questions with sources, whether the answer lives in a sentence of a contract or has to be computed from a hundred invoices.

## What FoldarAI explicitly is NOT (non-goals)

Being clear about scope boundaries matters as much as the vision — this keeps the MVP buildable and keeps the product story honest to customers.

- **Not a tax/legal advice bot.** It answers questions about *the business's own documents*. It does not attempt to be an authority on Romanian tax law or give legal advice, and should carry a visible disclaimer to that effect wherever relevant. (General legal/tax knowledge is already well covered by general-purpose LLMs — see the earlier discussion that ruled this out as the core product.)
- **Not a bookkeeping/accounting system replacement.** FoldarAI extracts data *from* documents; it does not replace a proper accounting system, generate invoices, file taxes, or handle payroll. If a client already uses accounting software (Oblio, SmartBill, SAGA), FoldarAI should eventually integrate with it rather than compete with it.
- **Not initially multi-country or multi-language beyond Romanian + English.** The Romanian market, Romanian-language documents, and RON currency handling are the initial and only target for the MVP.
- **Not a real-time collaborative document editor or DMS (document management system).** It's a read/query layer over documents the business already has, not a place to author or manage them going forward (though it needs to handle new documents being added over time).
- **Not aiming for enterprise features on day one.** SSO/SAML, granular org-chart-based permissions, and audit-log compliance tooling are enterprise-tier concerns (this is explicitly what Onyx's paid Enterprise Edition gates) — irrelevant for a business with a handful of employees. Basic per-client isolation is sufficient for the MVP; see [05-risks-and-open-questions.md](./05-risks-and-open-questions.md) for when this assumption would need revisiting.
