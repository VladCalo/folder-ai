"""Ties parsing + the classification LLM call together into "classify one
dropped-in file" - the Phase 1 unit of work from docs/03-implementation-roadmap.md.
"""
from pathlib import Path
from typing import Tuple

from .config import Settings
from .llm_client import call_structured, truncate
from .parsing import parse_document_text
from .prompts import CLASSIFICATION_SYSTEM_PROMPT
from .schema import CLASSIFICATION_JSON_SCHEMA, DocumentClassification

# Below this, flag for human review instead of trusting the label - per
# docs/02-mvp-scope.md: low-confidence classifications must be flagged, never
# silently misrouted. Not yet calibrated against real data (see
# docs/05-risks-and-open-questions.md) - revisit once the eval script has
# real accuracy/confidence numbers to tune against.
LOW_CONFIDENCE_THRESHOLD = 0.7


def classify_document_text(text: str, settings: Settings) -> DocumentClassification:
    data = call_structured(
        CLASSIFICATION_SYSTEM_PROMPT, truncate(text), CLASSIFICATION_JSON_SCHEMA, settings
    )
    return DocumentClassification.model_validate(data)


def classify_file(path: Path, settings: Settings) -> Tuple[DocumentClassification, bool]:
    """Returns (classification, needs_review)."""
    text = parse_document_text(path)
    classification = classify_document_text(text, settings)
    needs_review = classification.confidence < LOW_CONFIDENCE_THRESHOLD
    return classification, needs_review
