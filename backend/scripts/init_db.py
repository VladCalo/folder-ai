#!/usr/bin/env python3
"""Creates the documents/invoices/invoice_line_items/document_chunks tables
in the folderai Postgres database if they don't already exist. Idempotent -
safe to run repeatedly.

Requires `kubectl -n postgres port-forward svc/postgres 5432:5432` running
against the admin@rpi5 context (see backend/README.md).
"""
import sys
from pathlib import Path

from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from foldarai import db  # noqa: E402
from foldarai.config import load_settings  # noqa: E402


def main() -> None:
    load_dotenv(BACKEND_ROOT / ".env")
    settings = load_settings()
    conn = db.connect(settings)
    try:
        db.init_schema(conn, settings.tenant_company_name)
        print("Schema OK: documents, invoices, invoice_line_items, document_chunks")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
