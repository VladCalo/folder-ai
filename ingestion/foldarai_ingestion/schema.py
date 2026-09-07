"""The classification output shape.

document_type is deliberately open text, not a closed enum. The four types
named in docs/01-architecture.md (contract, invoice, hr_document, email) were
illustrative examples for the MVP scope, not an exhaustive taxonomy - a real
client drop-in can contain anything (insurance policies, permits, bank
statements, meeting minutes, government correspondence, warranties, ...).
Classification should be as accurate and specific as a knowledgeable person
(or a general-purpose LLM) asked "what is this document?" - forcing it into
one of five buckets defeats that.

What the pipeline actually needs as a closed, functional decision is much
narrower: does this document carry structured financial data worth extracting
into Postgres (the Unstract path), or not (docs/01-architecture.md step 4).
That's the one true routing fork - everything else gets semantically indexed
(the Onyx path) regardless of its specific type, so it doesn't need its own
category to make that happen. contains_financial_data below is that signal.
"""
from typing import List, Optional

from pydantic import BaseModel, Field


class DocumentClassification(BaseModel):
    document_type: str
    short_description: str
    contains_financial_data: bool
    confidence: float = Field(ge=0.0, le=1.0)
    parties_involved: List[str]
    date_mentioned: Optional[str] = None


# JSON Schema handed to OpenRouter's response_format (see llm_client.py) to
# force the model's output into this exact shape, matching DocumentClassification.
CLASSIFICATION_JSON_SCHEMA = {
    "name": "document_classification",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "document_type": {
                "type": "string",
                "description": (
                    "A short, specific, natural label for what this document "
                    "actually is (e.g. 'employment contract', 'supplier "
                    "invoice', 'insurance policy', 'meeting minutes', 'bank "
                    "statement', 'business registration certificate') - not "
                    "limited to a fixed list."
                ),
            },
            "short_description": {
                "type": "string",
                "description": (
                    "One concise sentence describing what this specific "
                    "document is about - who it's between/for and what it "
                    "covers, in the same language as the document."
                ),
            },
            "contains_financial_data": {
                "type": "boolean",
                "description": (
                    "True if the document's primary content is structured "
                    "financial data worth extracting as line items into a "
                    "database (invoice, receipt, payroll statement, financial "
                    "report). False if it only incidentally mentions a price "
                    "or amount within narrative/legal content (e.g. a price "
                    "clause in a contract)."
                ),
            },
            "confidence": {
                "type": "number",
                "minimum": 0,
                "maximum": 1,
            },
            "parties_involved": {
                "type": "array",
                "items": {"type": "string"},
            },
            "date_mentioned": {
                "type": ["string", "null"],
            },
        },
        "required": [
            "document_type",
            "short_description",
            "contains_financial_data",
            "confidence",
            "parties_involved",
            "date_mentioned",
        ],
        "additionalProperties": False,
    },
}


# --- Structured extraction (Phase 2 stand-in - see extraction.py) ----------
#
# This is a direct LLM call, same pattern as classification above, standing
# in for Unstract until we come back and do the real integration (see
# ingestion/README.md "Deferred: Onyx and Unstract").


class InvoiceLineItem(BaseModel):
    description: str
    quantity: float
    unit_price: float
    line_total: float


class InvoiceExtraction(BaseModel):
    vendor_name: str
    customer_name: Optional[str] = None
    document_number: Optional[str] = None
    issue_date: Optional[str] = None
    currency: str
    subtotal_amount: Optional[float] = None
    tax_amount: Optional[float] = None
    total_amount: float
    line_items: List[InvoiceLineItem]
    extraction_confidence: float = Field(ge=0.0, le=1.0)


EXTRACTION_JSON_SCHEMA = {
    "name": "invoice_extraction",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "vendor_name": {"type": "string"},
            "customer_name": {"type": ["string", "null"]},
            "document_number": {"type": ["string", "null"]},
            "issue_date": {"type": ["string", "null"]},
            "currency": {"type": "string"},
            "subtotal_amount": {"type": ["number", "null"]},
            "tax_amount": {"type": ["number", "null"]},
            "total_amount": {"type": "number"},
            "line_items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "description": {"type": "string"},
                        "quantity": {"type": "number"},
                        "unit_price": {"type": "number"},
                        "line_total": {"type": "number"},
                    },
                    "required": ["description", "quantity", "unit_price", "line_total"],
                    "additionalProperties": False,
                },
            },
            "extraction_confidence": {"type": "number", "minimum": 0, "maximum": 1},
        },
        "required": [
            "vendor_name",
            "customer_name",
            "document_number",
            "issue_date",
            "currency",
            "subtotal_amount",
            "tax_amount",
            "total_amount",
            "line_items",
            "extraction_confidence",
        ],
        "additionalProperties": False,
    },
}
