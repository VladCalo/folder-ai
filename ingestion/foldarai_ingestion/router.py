"""Router: given a user's question, decides whether to run the financial
tool (text-to-SQL over Postgres), the semantic tool (pgvector similarity
search), or both, then synthesizes one final answer with citations - or
refuses if nothing grounds an answer. Implements the two-tool design from
docs/01-architecture.md's query pipeline.

DELIBERATELY NOT LangGraph/a ReAct agent for this first pass: a fixed
three-step pipeline (route decision -> run selected tool(s), financial then
semantic -> synthesize) covers every documented example query in
docs/02-mvp-scope.md except the hardest compound case (see the note on that
below), without needing an actual agent loop. This is a simplification
worth revisiting - see ingestion/README.md "Deferred: Onyx and Unstract" and
the docs/01-architecture.md router design this stands in for.

KNOWN LIMITATION - true sequential compound questions: "which contracts
were active during our best month" needs the semantic search query itself
to depend on the financial tool's *result* (which month), decided only
after that tool runs. This router picks both tools' queries up front in one
routing call, so it can't do that - the semantic_query for a question like
that will be under-specified. This is exactly the kind of multi-step
tool-calling a real agent loop (LangGraph, per the original design) handles
naturally. Come back to this once the LangGraph router is worth building
for real - flagged here rather than silently accepted.
"""
import json
import re
from typing import List, Optional

import psycopg
from pydantic import BaseModel

from . import db, embeddings
from .config import Settings
from .llm_client import OpenRouterError, call_structured

ROUTE_SYSTEM_PROMPT = """You are the routing layer of FoldarAI, a document-
intelligence assistant for a small business. Given a user's question, decide
which of two tools are needed to answer it:

- financial tool: runs a SQL query against structured invoice data (vendor,
  date, amount, line items). Use for questions about revenue, expenses,
  invoice totals, profitability, spending by vendor, most/least profitable
  periods, averages, counts.
- semantic tool: searches the text of contracts, HR documents, emails, and
  other narrative documents. Use for questions about agreements, terms,
  conditions, correspondence, policies - anything answered by finding and
  reading a specific document.

Some questions need both (e.g. a question that requires first finding a
period financially, then finding documents relevant to that period). Some
questions need neither, if they clearly cannot be answered from this
business's own documents (e.g. general knowledge questions, tax/legal
advice) - FoldarAI only answers from the client's own documents.

Return a JSON object:
- use_financial_tool / use_semantic_tool: booleans.
- financial_question: if use_financial_tool, a self-contained restatement of
  what to look up financially. Else null.
- semantic_query: if use_semantic_tool, a self-contained restatement of what
  to search for. Else null.
"""

ROUTE_JSON_SCHEMA = {
    "name": "route_decision",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "use_financial_tool": {"type": "boolean"},
            "use_semantic_tool": {"type": "boolean"},
            "financial_question": {"type": ["string", "null"]},
            "semantic_query": {"type": ["string", "null"]},
        },
        "required": [
            "use_financial_tool", "use_semantic_tool",
            "financial_question", "semantic_query",
        ],
        "additionalProperties": False,
    },
}

SQL_SYSTEM_PROMPT_TEMPLATE = """You write a single read-only PostgreSQL
SELECT query to answer a financial question about a small business, against
this schema:

{schema}

Rules:
- Exactly one SELECT statement. No semicolons, no other statement types.
- Use ONLY the tables and columns listed above. There is no "tenants" table
  or any other table beyond what's listed - tenant_id is already a plain
  text column directly on invoices/invoice_line_items/documents, never a
  foreign key requiring a join or lookup.
- Every query MUST filter by tenant using exactly the placeholder
  %(tenant_id)s, compared directly against that column - e.g.
  "WHERE i.tenant_id = %(tenant_id)s". Never hardcode a tenant id, never
  omit this filter, never look it up from another table.
- Amounts are NUMERIC, issue_date is DATE. Use standard PostgreSQL syntax.
- For any question involving profit, net income, or "how much did we make":
  you MUST separate by direction (see schema above) and subtract - never
  just SUM(total_amount) across all rows, that adds revenue and expenses
  together instead of netting them.

Return a JSON object: {{"sql": "<the query>"}}.
"""

SQL_JSON_SCHEMA = {
    "name": "sql_query",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {"sql": {"type": "string"}},
        "required": ["sql"],
        "additionalProperties": False,
    },
}

SYNTHESIS_SYSTEM_PROMPT = """You are FoldarAI's answer-composer. You're
given the original question plus whatever tool results were gathered:
financial_result (the SQL query and the rows it returned) and/or
semantic_result (the search query and matching document chunks) - either
may be null if that tool wasn't used, or may contain an "error" key if it
failed.

Answer ONLY using the provided tool results - never invent numbers, dates,
vendor names, or facts not present in them. If the tool results don't
actually contain enough to answer the question, or are null/empty/errored,
set grounded to false and say so honestly instead of guessing - this is a
hard requirement, not a style preference (financial/legal answers that
sound plausible but aren't backed by real data are worse than no answer).

Cite your sources in the answer text itself:
- Financial answers: mention it's based on the invoice records.
- Semantic answers: name the specific source document filename(s) the
  answer came from.

Return a JSON object:
- answer: the final answer text, in the same language as the question.
- grounded: true if backed by the tool results, false if refusing/hedging.
- sources: source identifiers used (document filenames for semantic hits,
  "invoice records" for financial data) - empty list if grounded is false.
"""

SYNTHESIS_JSON_SCHEMA = {
    "name": "router_answer",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "answer": {"type": "string"},
            "grounded": {"type": "boolean"},
            "sources": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["answer", "grounded", "sources"],
        "additionalProperties": False,
    },
}

_FORBIDDEN_SQL_KEYWORDS = [
    "insert", "update", "delete", "drop", "alter", "truncate",
    "grant", "revoke", "create", "copy", "call", "execute", "merge",
]


class RouterError(RuntimeError):
    """Raised when a generated SQL query fails the read-only/tenant-scoping
    safety check - never executed."""


class RouteDecision(BaseModel):
    use_financial_tool: bool
    use_semantic_tool: bool
    financial_question: Optional[str] = None
    semantic_query: Optional[str] = None


class RouterAnswer(BaseModel):
    answer: str
    grounded: bool
    sources: List[str]


def _validate_readonly_sql(sql: str) -> None:
    """Defense in depth against a generated query doing something other than
    reading this tenant's own rows. The folderai Postgres role currently has
    full owner rights on the database (see k3s-rpi5 apps/folderai/db-init-job.yaml)
    - the real fix is a dedicated read-only role for this tool, which is a
    "come back to this" item, not done yet. This check is the interim
    safety net, not a substitute for that.
    """
    normalized = sql.strip().rstrip(";").strip()
    if not re.match(r"(?is)^select\b", normalized):
        raise RouterError(f"Generated query is not a SELECT statement: {sql!r}")
    if ";" in normalized:
        raise RouterError(f"Generated query contains multiple statements: {sql!r}")
    lowered = normalized.lower()
    for word in _FORBIDDEN_SQL_KEYWORDS:
        if re.search(rf"\b{word}\b", lowered):
            raise RouterError(f"Generated query contains forbidden keyword {word!r}: {sql!r}")
    if "%(tenant_id)s" not in sql:
        raise RouterError(f"Generated query is missing the required tenant_id filter: {sql!r}")


def _decide_route(question: str, settings: Settings) -> RouteDecision:
    data = call_structured(ROUTE_SYSTEM_PROMPT, question, ROUTE_JSON_SCHEMA, settings)
    return RouteDecision.model_validate(data)


def _run_financial_tool(question: str, conn, settings: Settings) -> dict:
    prompt = SQL_SYSTEM_PROMPT_TEMPLATE.format(schema=db.FINANCIAL_SCHEMA_DESCRIPTION)
    data = call_structured(prompt, question, SQL_JSON_SCHEMA, settings)
    sql = data["sql"]
    _validate_readonly_sql(sql)
    rows = db.run_readonly_query(conn, sql, settings.tenant_id)
    return {"sql": sql, "rows": rows}


def _run_semantic_tool(query: str, conn, settings: Settings) -> dict:
    query_vector = embeddings.embed_query(query)
    chunks = db.semantic_search(
        conn, tenant_id=settings.tenant_id, query_embedding=query_vector, top_k=5
    )
    return {"query": query, "chunks": chunks}


def answer_question(question: str, conn, settings: Settings) -> RouterAnswer:
    route = _decide_route(question, settings)

    financial_result = None
    if route.use_financial_tool:
        try:
            financial_result = _run_financial_tool(
                route.financial_question or question, conn, settings
            )
        except (RouterError, OpenRouterError, psycopg.Error) as exc:
            # A generated query can be syntactically fine (passes
            # _validate_readonly_sql) but semantically wrong - e.g. it
            # referenced a table/column that doesn't exist. That's a real
            # failure mode we hit in testing (the model invented a `tenants`
            # table), not hypothetical - must not crash the whole answer.
            conn.rollback()  # failed query leaves the transaction aborted
            financial_result = {"error": str(exc)}

    semantic_result = None
    if route.use_semantic_tool:
        try:
            semantic_result = _run_semantic_tool(
                route.semantic_query or question, conn, settings
            )
        except (OpenRouterError, psycopg.Error) as exc:
            conn.rollback()
            semantic_result = {"error": str(exc)}

    synthesis_input = json.dumps(
        {
            "question": question,
            "financial_result": financial_result,
            "semantic_result": semantic_result,
        },
        default=str,
    )
    data = call_structured(
        SYNTHESIS_SYSTEM_PROMPT, synthesis_input, SYNTHESIS_JSON_SCHEMA, settings
    )
    return RouterAnswer.model_validate(data)
