"""Local embedding model for semantic search - a deliberate stand-in for
Onyx's embedding pipeline (docs/01-architecture.md), so search_documents
works without deploying Onyx or depending on another external API (after the
OpenRouter free-tier rate-limit fight, a second flaky network dependency for
embeddings specifically wasn't worth it - this runs entirely locally/offline
once the model is downloaded once).

intfloat/multilingual-e5-small: small (~470MB), reasonable Romanian support,
and specifically trained for asymmetric retrieval (a "query: " prefix for
questions, "passage: " for indexed text) - which is exactly this use case.
Not benchmarked against alternatives; revisit if semantic search quality
turns out to be the weak link once the router is tested against real
queries. See backend/README.md "Deferred: Onyx and Unstract".

384-dimensional output - the pgvector column this writes into must be
vector(384) (see db.py's schema).
"""
from typing import List

EMBEDDING_MODEL_NAME = "intfloat/multilingual-e5-small"
EMBEDDING_DIMENSIONS = 384

_model = None


def _get_model():
    global _model
    if _model is None:
        # Imported lazily - sentence-transformers/torch are slow to import
        # and not needed by every script that touches this package.
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _model


def embed_passage(text: str) -> List[float]:
    """For text being indexed (document chunks)."""
    return _get_model().encode(f"passage: {text}", normalize_embeddings=True).tolist()


def embed_query(text: str) -> List[float]:
    """For a user's search question."""
    return _get_model().encode(f"query: {text}", normalize_embeddings=True).tolist()
