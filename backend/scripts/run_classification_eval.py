#!/usr/bin/env python3
"""Runs classification over sample-data/dump/ and checks it against
sample-data/manifest.json.

document_type is open text (see foldarai/schema.py) - there's no
fixed taxonomy to score exact-match accuracy against, by design. So this
script scores what's actually well-defined ground truth:

- contains_financial_data: a real boolean, directly comparable - this is the
  Phase 1 exit criterion analogue (docs/03-implementation-roadmap.md's
  ">=90% classification accuracy" target, reinterpreted for an open-text
  document_type as ">=90% correct on the one routing decision that actually
  gates pipeline behavior").
- document_type / short_description: printed for every file so you can
  eyeball whether they're actually specific and correct (the "as good as
  asking ChatGPT" bar) - not auto-scored, since that's a qualitative judgment
  call, not a string-equality one.

Usage:
    cd backend
    python -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    python scripts/run_classification_eval.py

Already run for real once (see backend/README.md's "Status" section).
"""
import json
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(BACKEND_ROOT))

from foldarai.config import load_settings  # noqa: E402
from foldarai.ingestion import classify_file  # noqa: E402
from foldarai.llm_client import OpenRouterError  # noqa: E402

SAMPLE_DATA_DIR = REPO_ROOT / "sample-data"
DUMP_DIR = SAMPLE_DATA_DIR / "dump"
MANIFEST_PATH = SAMPLE_DATA_DIR / "manifest.json"

FINANCIAL_ACCURACY_TARGET = 0.90
# Free-tier models are rate-limited; a small gap between the 31 sequential
# requests here is cheap insurance against tripping a per-minute limit.
DELAY_BETWEEN_REQUESTS_SECONDS = 2


def main() -> None:
    load_dotenv(BACKEND_ROOT / ".env")
    settings = load_settings()

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    financial_correct = 0
    flagged_low_confidence = 0
    errors = 0
    results = []

    for i, entry in enumerate(manifest):
        filename = entry["filename"]
        expected_financial = entry["contains_financial_data"]
        path = DUMP_DIR / filename

        if i > 0:
            time.sleep(DELAY_BETWEEN_REQUESTS_SECONDS)

        try:
            classification, needs_review = classify_file(path, settings)
        except OpenRouterError as exc:
            errors += 1
            print(f"[ERR ] {filename}\n        {exc}")
            results.append({"filename": filename, "error": str(exc)})
            continue

        financial_match = classification.contains_financial_data == expected_financial
        financial_correct += int(financial_match)
        flagged_low_confidence += int(needs_review)

        results.append(
            {
                "filename": filename,
                "expected_category": entry.get("category"),
                "predicted_document_type": classification.document_type,
                "predicted_description": classification.short_description,
                "expected_contains_financial_data": expected_financial,
                "predicted_contains_financial_data": classification.contains_financial_data,
                "financial_match": financial_match,
                "confidence": classification.confidence,
                "needs_review": needs_review,
            }
        )

        marker = "OK  " if financial_match else "MISS"
        print(
            f"[{marker}] {filename}\n"
            f"        expected_category={entry.get('category')!r}  "
            f"financial: expected={expected_financial} predicted={classification.contains_financial_data}\n"
            f"        document_type={classification.document_type!r}  "
            f"confidence={classification.confidence:.2f}"
            + (" (flagged for review)" if needs_review else "") + "\n"
            f"        description: {classification.short_description}"
        )

    attempted = len(manifest) - errors
    financial_accuracy = financial_correct / attempted if attempted else 0.0
    print(f"\ncontains_financial_data accuracy: {financial_correct}/{attempted} = {financial_accuracy:.1%}"
          + (f"  ({errors} file(s) errored, excluded)" if errors else ""))
    print(f"Flagged low-confidence: {flagged_low_confidence}/{attempted}")
    print(
        f"Financial-routing exit bar (>= {FINANCIAL_ACCURACY_TARGET:.0%}): "
        + ("PASS" if financial_accuracy >= FINANCIAL_ACCURACY_TARGET else "FAIL")
    )
    print(
        "\ndocument_type/short_description are not auto-scored (open text by "
        "design) - eyeball the printed labels above against sample-data/README.md's "
        "entity list to judge classification quality."
    )


if __name__ == "__main__":
    main()
