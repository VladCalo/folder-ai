"""Postgres persistence: documents/invoices/invoice_line_items (structured
data, per docs/01-architecture.md's data model) plus document_chunks (the
pgvector-backed semantic index - our stand-in for Onyx, see
backend/README.md "Deferred: Onyx and Unstract").

Plain SQL via psycopg, no ORM - matches the "simple direct calls" approach
used throughout this codebase so far, and keeps the schema (below) fully
visible in one place instead of scattered across model classes.

tenant_id is on every table from the start even though this whole script
only ever uses one tenant right now (config.DEFAULT_TENANT_ID) - per
docs/01-architecture.md, cheap now, expensive to retrofit.
"""
from typing import List, Optional
from uuid import UUID

import psycopg

from .config import Settings

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    document_type TEXT NOT NULL,
    short_description TEXT NOT NULL,
    contains_financial_data BOOLEAN NOT NULL,
    classification_confidence DOUBLE PRECISION NOT NULL,
    parties_involved TEXT[] NOT NULL DEFAULT '{}',
    date_mentioned TEXT,
    needs_review BOOLEAN NOT NULL DEFAULT FALSE,
    raw_text TEXT NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, content_hash)
);

-- direction ('sale'/'purchase') is what makes profit computable at all: with
-- only total_amount, a SUM across a period adds revenue and expenses
-- together instead of subtracting one from the other - a real bug hit in
-- testing (a profit query summed everything as if additive, off by ~30k
-- RON). direction is computed by comparing the extracted vendor_name against
-- config.Settings.tenant_company_name at insert time (see
-- populate_sample_data.py) - this only works because there's exactly one
-- tenant right now with a known company name; a real multi-tenant version
-- needs this comparison done per-tenant, not hardcoded.
CREATE TABLE IF NOT EXISTS invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    vendor_name TEXT NOT NULL,
    customer_name TEXT,
    document_number TEXT,
    issue_date DATE,
    currency TEXT NOT NULL,
    subtotal_amount NUMERIC,
    tax_amount NUMERIC,
    total_amount NUMERIC NOT NULL,
    direction TEXT NOT NULL DEFAULT 'purchase' CHECK (direction IN ('sale', 'purchase')),
    extraction_confidence DOUBLE PRECISION NOT NULL,
    extracted_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS invoice_line_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_id UUID NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    quantity NUMERIC NOT NULL,
    unit_price NUMERIC NOT NULL,
    line_total NUMERIC NOT NULL
);

-- 384 dims to match embeddings.EMBEDDING_DIMENSIONS
-- (intfloat/multilingual-e5-small). No ANN index yet (HNSW etc.) - at
-- dozens/hundreds of chunks a sequential scan is instant; add one once
-- volume actually warrants it, not before.
CREATE TABLE IF NOT EXISTS document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INT NOT NULL,
    chunk_text TEXT NOT NULL,
    embedding vector(384) NOT NULL
);
"""


def connect(settings: Settings) -> psycopg.Connection:
    return psycopg.connect(settings.db_dsn)


def init_schema(conn: psycopg.Connection, tenant_company_name: str) -> None:
    with conn.cursor() as cur:
        cur.execute(SCHEMA_SQL)  # plain multi-statement SQL, no params
    conn.commit()
    _migrate_invoice_direction(conn, tenant_company_name)


def _migrate_invoice_direction(conn: psycopg.Connection, tenant_company_name: str) -> None:
    """Backfills `direction` for a database populated before that column
    existed (a fresh CREATE TABLE already has it via its DEFAULT/CHECK).
    Each statement runs separately - psycopg doesn't support multiple
    statements in one parameterized execute() call.
    """
    with conn.cursor() as cur:
        cur.execute("ALTER TABLE invoices ADD COLUMN IF NOT EXISTS direction TEXT")
        cur.execute(
            """
            UPDATE invoices SET direction = 'sale'
            WHERE direction IS NULL AND vendor_name ILIKE %s
            """,
            (f"%{tenant_company_name}%",),
        )
        cur.execute("UPDATE invoices SET direction = 'purchase' WHERE direction IS NULL")
        cur.execute("ALTER TABLE invoices ALTER COLUMN direction SET NOT NULL")
        cur.execute("ALTER TABLE invoices ALTER COLUMN direction SET DEFAULT 'purchase'")
    conn.commit()


def _vector_literal(embedding: List[float]) -> str:
    return "[" + ",".join(f"{v:.8f}" for v in embedding) + "]"


def find_document_by_hash(
    conn: psycopg.Connection, tenant_id: str, content_hash: str
) -> Optional[UUID]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM documents WHERE tenant_id = %s AND content_hash = %s",
            (tenant_id, content_hash),
        )
        row = cur.fetchone()
        return row[0] if row else None


def insert_document(
    conn: psycopg.Connection,
    *,
    tenant_id: str,
    filename: str,
    content_hash: str,
    document_type: str,
    short_description: str,
    contains_financial_data: bool,
    classification_confidence: float,
    parties_involved: List[str],
    date_mentioned: Optional[str],
    needs_review: bool,
    raw_text: str,
) -> UUID:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO documents (
                tenant_id, filename, content_hash, document_type,
                short_description, contains_financial_data,
                classification_confidence, parties_involved, date_mentioned,
                needs_review, raw_text
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                tenant_id, filename, content_hash, document_type,
                short_description, contains_financial_data,
                classification_confidence, parties_involved, date_mentioned,
                needs_review, raw_text,
            ),
        )
        doc_id = cur.fetchone()[0]
    conn.commit()
    return doc_id


def insert_invoice(
    conn: psycopg.Connection,
    *,
    tenant_id: str,
    document_id: UUID,
    vendor_name: str,
    customer_name: Optional[str],
    document_number: Optional[str],
    issue_date: Optional[str],
    currency: str,
    subtotal_amount: Optional[float],
    tax_amount: Optional[float],
    total_amount: float,
    direction: str,
    extraction_confidence: float,
    line_items: List[dict],
) -> UUID:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO invoices (
                tenant_id, document_id, vendor_name, customer_name,
                document_number, issue_date, currency, subtotal_amount,
                tax_amount, total_amount, direction, extraction_confidence
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                tenant_id, document_id, vendor_name, customer_name,
                document_number, issue_date, currency, subtotal_amount,
                tax_amount, total_amount, direction, extraction_confidence,
            ),
        )
        invoice_id = cur.fetchone()[0]
        for item in line_items:
            cur.execute(
                """
                INSERT INTO invoice_line_items
                    (invoice_id, description, quantity, unit_price, line_total)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (invoice_id, item["description"], item["quantity"],
                 item["unit_price"], item["line_total"]),
            )
    conn.commit()
    return invoice_id


def insert_chunk(
    conn: psycopg.Connection,
    *,
    tenant_id: str,
    document_id: UUID,
    chunk_index: int,
    chunk_text: str,
    embedding: List[float],
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO document_chunks
                (tenant_id, document_id, chunk_index, chunk_text, embedding)
            VALUES (%s, %s, %s, %s, %s::vector)
            """,
            (tenant_id, document_id, chunk_index, chunk_text, _vector_literal(embedding)),
        )
    conn.commit()


def semantic_search(
    conn: psycopg.Connection,
    *,
    tenant_id: str,
    query_embedding: List[float],
    top_k: int = 5,
) -> List[dict]:
    """Returns the top_k chunks by cosine distance, with their source
    document's filename/type for citation."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT d.filename, d.document_type, c.chunk_text,
                   c.embedding <=> %s::vector AS distance
            FROM document_chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE c.tenant_id = %s
            ORDER BY distance ASC
            LIMIT %s
            """,
            (_vector_literal(query_embedding), tenant_id, top_k),
        )
        rows = cur.fetchall()
    return [
        {"filename": r[0], "document_type": r[1], "chunk_text": r[2], "distance": float(r[3])}
        for r in rows
    ]


def run_readonly_query(conn: psycopg.Connection, sql: str, tenant_id: str) -> List[dict]:
    """Executes a single SELECT statement. See sql_safety.py for the checks
    applied to `sql` before it reaches here (called from tools.py) - this
    function itself does not re-validate, callers must.
    """
    with conn.cursor() as cur:
        cur.execute(sql, {"tenant_id": tenant_id})
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
    return [dict(zip(columns, row)) for row in rows]
