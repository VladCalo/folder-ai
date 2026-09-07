"""The query side: given a user's question, decide which tool(s) to run and
synthesize a grounded answer. See foldarai.ingestion for the ingest-time
side, and foldarai's top-level modules for infra shared by both.
"""
from .answer import answer_question

__all__ = ["answer_question"]
