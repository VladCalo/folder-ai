"""Structured invoice-field extraction: vendor/date/amount/line-items out of
a document already flagged contains_financial_data=True by classify.py.

This is a direct LLM call, same pattern as classification - a deliberate
stand-in for Unstract (docs/01-architecture.md's real extraction component)
so we can get the whole ingest -> extract -> store -> query loop working end
to end fast. See ingestion/README.md's "Deferred: Onyx and Unstract" section
before treating this as the final design - it has no dual-LLM-consensus, no
document-layout awareness, and hasn't been checked against real messy
invoices the way docs/03-implementation-roadmap.md Phase 2 calls for.
"""
from .config import Settings
from .llm_client import call_structured, truncate
from .prompts import EXTRACTION_SYSTEM_PROMPT
from .schema import EXTRACTION_JSON_SCHEMA, InvoiceExtraction


def extract_invoice_fields(text: str, settings: Settings) -> InvoiceExtraction:
    data = call_structured(
        EXTRACTION_SYSTEM_PROMPT, truncate(text), EXTRACTION_JSON_SCHEMA, settings
    )
    return InvoiceExtraction.model_validate(data)
