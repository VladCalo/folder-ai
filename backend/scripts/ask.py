#!/usr/bin/env python3
"""Ask the router a question directly from the CLI - no Slack needed. Same
answer_question() the Slack bot calls, so this is the fast way to
test/iterate on routing and answer quality.

Usage:
    python scripts/ask.py "What was our most profitable month this year?"
"""
import sys
from pathlib import Path

from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from foldarai import db  # noqa: E402
from foldarai.config import load_settings  # noqa: E402
from foldarai.router import answer_question  # noqa: E402


def main() -> None:
    if len(sys.argv) < 2:
        print('Usage: python scripts/ask.py "your question"')
        sys.exit(1)
    question = sys.argv[1]

    load_dotenv(BACKEND_ROOT / ".env")
    settings = load_settings()
    conn = db.connect(settings)
    try:
        result = answer_question(question, conn, settings)
    finally:
        conn.close()

    print(f"\nQ: {question}\n")
    print(result.answer)
    print(f"\ngrounded={result.grounded}  sources={result.sources}")


if __name__ == "__main__":
    main()
