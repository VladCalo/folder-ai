#!/usr/bin/env python3
"""Runs the full ingest pipeline over sample-data/dump/ and writes the
result into Postgres: classify -> persist documents row -> if
contains_financial_data, extract invoice fields -> persist invoices/
invoice_line_items -> always embed the document and persist a chunk (see
embeddings.py) for semantic search.

Idempotent: each file's content hash is checked against existing `documents`
rows for this tenant before reprocessing, so re-running after adding new
files to sample-data/dump/ only processes what's new.

Requires `kubectl -n postgres port-forward svc/postgres 5432:5432` running
against the admin@rpi5 context, and scripts/init_db.py already run once.

Usage:
    python scripts/populate_sample_data.py
"""
import hashlib
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

INGESTION_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = INGESTION_ROOT.parent
sys.path.insert(0, str(INGESTION_ROOT))

from foldarai_ingestion import db, embeddings  # noqa: E402
from foldarai_ingestion.classify import classify_document_text  # noqa: E402
from foldarai_ingestion.config import load_settings  # noqa: E402
from foldarai_ingestion.extraction import extract_invoice_fields  # noqa: E402
from foldarai_ingestion.llm_client import OpenRouterError  # noqa: E402
from foldarai_ingestion.parsing import parse_document_text  # noqa: E402

DUMP_DIR = REPO_ROOT / "sample-data" / "dump"
LOW_CONFIDENCE_THRESHOLD = 0.7
DELAY_BETWEEN_FILES_SECONDS = 1


def main() -> None:
    load_dotenv(INGESTION_ROOT / ".env")
    settings = load_settings()
    conn = db.connect(settings)

    files = sorted(DUMP_DIR.iterdir())
    processed, skipped, failed = 0, 0, 0

    for i, path in enumerate(files):
        if not path.is_file():
            continue
        if i > 0:
            time.sleep(DELAY_BETWEEN_FILES_SECONDS)

        text = parse_document_text(path)
        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()

        existing = db.find_document_by_hash(conn, settings.tenant_id, content_hash)
        if existing:
            print(f"[SKIP] {path.name} - already ingested (document {existing})")
            skipped += 1
            continue

        try:
            classification = classify_document_text(text, settings)
        except OpenRouterError as exc:
            print(f"[FAIL] {path.name} - classification error: {exc}")
            failed += 1
            continue

        needs_review = classification.confidence < LOW_CONFIDENCE_THRESHOLD
        doc_id = db.insert_document(
            conn,
            tenant_id=settings.tenant_id,
            filename=path.name,
            content_hash=content_hash,
            document_type=classification.document_type,
            short_description=classification.short_description,
            contains_financial_data=classification.contains_financial_data,
            classification_confidence=classification.confidence,
            parties_involved=classification.parties_involved,
            date_mentioned=classification.date_mentioned,
            needs_review=needs_review,
            raw_text=text,
        )

        extracted_note = ""
        if classification.contains_financial_data:
            try:
                extraction = extract_invoice_fields(text, settings)
                # This business is the vendor -> money received (sale);
                # otherwise it's the one paying (purchase). See db.py's
                # invoices.direction column - this is what makes profit
                # computable at all (a plain SUM(total_amount) conflates
                # revenue and expenses).
                direction = (
                    "sale"
                    if settings.tenant_company_name.lower() in extraction.vendor_name.lower()
                    else "purchase"
                )
                db.insert_invoice(
                    conn,
                    tenant_id=settings.tenant_id,
                    document_id=doc_id,
                    vendor_name=extraction.vendor_name,
                    customer_name=extraction.customer_name,
                    document_number=extraction.document_number,
                    issue_date=extraction.issue_date,
                    currency=extraction.currency,
                    subtotal_amount=extraction.subtotal_amount,
                    tax_amount=extraction.tax_amount,
                    total_amount=extraction.total_amount,
                    direction=direction,
                    extraction_confidence=extraction.extraction_confidence,
                    line_items=[li.model_dump() for li in extraction.line_items],
                )
                extracted_note = (
                    f", extracted total={extraction.total_amount} "
                    f"{extraction.currency} ({direction})"
                )
            except OpenRouterError as exc:
                extracted_note = f", extraction FAILED: {exc}"

        # Whole document as one chunk - documents here are short. Real
        # chunking (splitting long documents into ~overlapping windows) is
        # a "come back to this" item once real, longer documents show up -
        # see embeddings.py and ingestion/README.md.
        embedding = embeddings.embed_passage(text)
        db.insert_chunk(
            conn,
            tenant_id=settings.tenant_id,
            document_id=doc_id,
            chunk_index=0,
            chunk_text=text,
            embedding=embedding,
        )

        print(
            f"[OK  ] {path.name} -> {classification.document_type!r} "
            f"(financial={classification.contains_financial_data}){extracted_note}"
        )
        processed += 1

    conn.close()
    print(f"\nProcessed: {processed}  Skipped (already ingested): {skipped}  Failed: {failed}")


if __name__ == "__main__":
    main()
