"""The two tools the router (answer.py) can call: the financial tool
(text-to-SQL over Postgres) and the semantic tool (pgvector similarity
search). Implements the two-tool design from docs/01-architecture.md's
query pipeline (`query_financials` / `search_documents`).

Kept separate from answer.py so the routing/synthesis orchestration stays
readable on its own, and each tool is easy to find, read, and (eventually)
test independently of the other.

DEFERRED: search_documents here is our own pgvector query, not Onyx's
retrieval API - see backend/README.md "Deferred: Onyx and Unstract". This
is the exact call site to swap when that integration happens.
"""
from .. import db, embeddings
from ..config import Settings
from ..llm_client import call_structured
from ..prompts import FINANCIAL_SCHEMA_DESCRIPTION, FINANCIAL_SQL_SYSTEM_PROMPT_TEMPLATE
from ..schema import SQL_JSON_SCHEMA
from .sql_safety import validate_readonly_sql


def run_financial_tool(question: str, conn, settings: Settings) -> dict:
    """query_financials: generates a read-only SQL query, validates it, runs
    it for real against the invoices/invoice_line_items tables, and returns
    the query alongside its rows (the query itself is the audit trail /
    citation for the answer this feeds into)."""
    prompt = FINANCIAL_SQL_SYSTEM_PROMPT_TEMPLATE.format(schema=FINANCIAL_SCHEMA_DESCRIPTION)
    data = call_structured(prompt, question, SQL_JSON_SCHEMA, settings)
    sql = data["sql"]
    validate_readonly_sql(sql)
    rows = db.run_readonly_query(conn, sql, settings.tenant_id)
    return {"sql": sql, "rows": rows}


def run_semantic_tool(query: str, conn, settings: Settings) -> dict:
    """search_documents: embeds the query the same way documents were
    embedded at ingest time, then finds the closest chunks by cosine
    similarity."""
    query_vector = embeddings.embed_query(query)
    chunks = db.semantic_search(
        conn, tenant_id=settings.tenant_id, query_embedding=query_vector, top_k=5
    )
    return {"query": query, "chunks": chunks}
