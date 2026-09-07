"""Parsing step: turns any dropped-in file into plain text via Unstructured.io.

Uses partition() (format auto-detected from file content, not filename/
extension) - real client dumps have unreliable filenames (see
sample-data/README.md), so classification must work from parsed content.
"""
from pathlib import Path

from unstructured.partition.auto import partition


def parse_document_text(path: Path) -> str:
    elements = partition(filename=str(path))
    return "\n".join(el.text for el in elements if getattr(el, "text", None))
