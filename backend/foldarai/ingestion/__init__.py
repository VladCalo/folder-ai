"""The ingestion side: parse a dropped-in file, classify it, and (if it
carries financial data) extract structured fields from it. Everything here
runs at ingest time - see foldarai.router for the query-time side, and
foldarai's top-level modules (config, db, schema, prompts, llm_client,
embeddings) for infra shared by both.
"""
from .classify import classify_document_text, classify_file
from .extraction import extract_invoice_fields
from .parsing import parse_document_text

__all__ = [
    "classify_document_text",
    "classify_file",
    "extract_invoice_fields",
    "parse_document_text",
]
