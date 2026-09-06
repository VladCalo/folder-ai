# 04 — Business Context

## Target customer

Solo entrepreneurs and small/micro businesses in Romania (roughly 1-50 employees) that:
- Already have a real body of digital (or scanned) documents — contracts, invoices, HR paperwork, email correspondence.
- Don't have a dedicated IT department or a full-time accountant who already digitizes and organizes everything (a bookkeeper handling formal filings is common; someone who's turned the surrounding paperwork into a queryable system is not).
- Are sensitive to where sensitive business data (contracts, financials) ends up — a real, usable selling point given the EU-hosted, isolated-per-client deployment model in [01-architecture.md](./01-architecture.md).

## Competitive landscape (why this is a real gap)

| Tool | What it does | Why it doesn't fill this gap |
|---|---|---|
| **ChatGPT / Claude (general use)** | General knowledge, including generic tax/legal information | No access to a business's private documents at all. |
| **Onyx** (open source) | Excellent self-hosted semantic search, chat, and Slack bot over documents | No structured financial extraction or SQL-style aggregation — cannot answer "what was our most profitable month." |
| **Hebbia, AlphaSense, DataSnipper, SageX** | Genuinely combine structured and unstructured document analysis | Priced and built for hedge funds, equity research, and audit firms — enterprise budgets, analyst-level configuration, not a fit for a shop owner. |
| **Unstructured.io / Unstract (raw)** | Solve parsing and structured extraction well | Infrastructure components, not a product — nobody has wired them into a semantic-search-plus-router product a small business owner can just use. |

The gap: **no self-hostable, affordable, zero-configuration product where a small business drops in an unsorted folder of mixed documents and gets one bot answering both qualitative and quantitative questions.** This was validated by direct research during project planning, not assumed.

## Delivery models

Two models using the same underlying Docker Compose bundle (full detail in [01-architecture.md](./01-architecture.md)):

1. **You-hosted, isolated-per-client (MVP default).** You deploy and operate one isolated stack per client on EU infrastructure (e.g. Hetzner). Billed as a normal monthly subscription. You retain control for updates and support — the practical starting point for a solo builder.
2. **True on-premise, client-hosted (later, premium tier).** The client runs the same bundle on their own infrastructure. Strongest privacy pitch, but real support burden (debugging on infrastructure you don't control, client technical competence varies) — introduce once there's a working product and a support process, not at MVP stage.

## Cost structure (per client, model 1)

| Cost item | Estimate | Notes |
|---|---|---|
| Hosting (VPS running that client's isolated stack) | ~€15-30/month | E.g. a Hetzner CPX-class instance. Shrinks per-client as multiple clients' containers are consolidated onto larger shared servers at scale (still logically isolated by container/database). |
| LLM API usage | ~€1-10/month | Cloud API (GPT-4o-mini class: ~$0.15/$0.60 per million input/output tokens), scales with actual query volume. Cheap enough at small-business query volume that self-hosting a GPU to avoid it doesn't pay off until volume is much higher across many clients (see [01-architecture.md](./01-architecture.md) LLM strategy). |
| **Total infrastructure cost per client** | **~€20-40/month** | This is cost of goods sold (COGS) — not profit, and not the number to charge the client. |
| Your time | Not a monthly cash cost, but the real scarce resource | Onboarding (initial ingestion, classification tuning, review) is mostly one-time labor per client; ongoing support is smaller but recurring. Must be accounted for even though it isn't a line item. |

## Pricing

**Do not price at the infrastructure cost estimate (€15-30/month) — that would leave zero or negative margin once LLM costs are added, and zero contribution to your time.**

A workable structure:
- **One-time onboarding fee** (~€150-300 equivalent) covering the initial ingestion/classification-tuning labor per client.
- **Monthly subscription** priced at roughly **2-3x all-in infrastructure cost** to leave real margin for ongoing support and iteration — a starting anchor around **€40-100/month (≈200-500 RON)** is plausible and still well under enterprise-tool pricing.

Worked example: if all-in cost per client is ~€25/month and the subscription is priced at €60/month, gross profit is **~€35/month per client** before accounting for your own support/maintenance time — improving further as hosting becomes more efficient per client with scale.

**This anchor is a starting point, not a validated price.** The right way to firm it up is talking to 5-10 real target customers about what this problem currently costs them (in time, or in what they already pay a bookkeeper/accountant to dig through paperwork) and pricing against that value, not just cost-plus.

## Go-to-market (open, needs validation)

Not yet researched in depth — flagged here as the next planning gap once the technical MVP direction is set:
- Likely channels: local accountant/bookkeeper networks (they see this exact pain firsthand and could be referral partners), small-business associations, Romanian entrepreneur communities (Facebook groups, local business meetups).
- The first pilot client (Phase 8 in [03-implementation-roadmap.md](./03-implementation-roadmap.md)) should double as the first real market-validation data point — both for pricing and for which document types/questions matter most in practice.
