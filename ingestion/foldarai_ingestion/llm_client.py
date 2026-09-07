"""OpenRouter chat-completions call for document classification.

Deliberately a plain HTTP request, not LangChain/LangGraph: classification is
one request in, one structured JSON object out - no multi-step reasoning, no
tool orchestration, no state across turns. LangGraph is reserved for the
Phase 4 router agent (docs/01-architecture.md), which genuinely needs an
agentic loop deciding between search_documents/query_financials. This step
doesn't, so a framework here would be pure overhead.

Also deliberately not using the `reasoning` param or streaming:
- `reasoning` (thinking tokens) is for problems that need step-by-step
  deliberation. Classifying what a document is from its own text doesn't need
  that, and turning it on would only add latency/cost.
- Streaming is for incrementally displaying tokens to a live UI. This is a
  batch backend call with no one watching it type, so there's nothing to
  stream to - we just want the final JSON object.

Retries with backoff, plus a fallback chain across models from *different*
upstream providers: free-tier models on OpenRouter share a pool across all
OpenRouter users hitting that specific provider (Google AI Studio for Gemma,
NVIDIA's endpoint for Nemotron, ...) - so a 429/502 here is expected under
free-tier use, not a bug, and can affect an entire provider at once. Retrying
the same model handles a brief blip; falling back to a different provider
handles a provider being down/overloaded for a while, which is what we
actually hit in testing (Google AI Studio, then NVIDIA's endpoint, both
returning transient errors back to back).

Note OpenRouter itself can return a provider error as HTTP 200 with an
`error` key in the body (not just as a non-2xx status) - _post_once() checks
both.
"""
import json
import time

import requests

from .config import Settings
from .schema import CLASSIFICATION_JSON_SCHEMA, DocumentClassification

OPENROUTER_CHAT_COMPLETIONS_URL = "https://openrouter.ai/api/v1/chat/completions"

_SYSTEM_PROMPT = """You classify business documents (mostly Romanian, some
English) for FoldarAI, a document-intelligence assistant for small
businesses. A client can drop in literally anything generated or received in
the course of running a business - invoices, contracts of every kind
(employment, supply, lease, service, NDA...), HR paperwork, correspondence/
emails, bank statements, insurance policies, permits and licenses,
certificates, meeting minutes, price quotes, purchase orders, tax documents,
warranties, and things not listed here. Do not assume it's one of a small
fixed set of categories.

Read the document text and return exactly one JSON object matching the given
schema.

- document_type: answer as precisely and specifically as you would if a
  person handed you this document and asked "what is this?". Use a short,
  natural label (roughly 2-6 words), in Romanian if the document is Romanian
  and that reads more naturally, otherwise in English. Do not limit yourself
  to a fixed list - be as accurate here as you would be for any document,
  business-related or not.
- short_description: one concise sentence, in the same language as the
  document, saying what this specific document is about (who it's between/
  for, what it covers) - not a generic definition of the document_type.
- contains_financial_data: true only if the document's primary content is
  structured financial data meant to be extracted as line items into a
  database (an invoice, receipt, payroll statement, financial report/
  register). False if it's a document that merely mentions a price or amount
  as part of narrative or legal content (e.g. a price clause inside a
  contract, or an email referencing a cost).
- parties_involved: the company/person names that are actual parties to the
  document (suppliers, clients, employees, signatories, correspondents) - not
  every name that happens to appear in the text.
- date_mentioned: the single most relevant date for the document (contract
  signing date, invoice issue date, employment start date, letter date) in
  YYYY-MM-DD format if it can be determined, otherwise null.
- confidence: how certain you are about document_type specifically, 0 to 1.
"""


ATTEMPTS_PER_MODEL = 3
INITIAL_BACKOFF_SECONDS = 3
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

# Tried in order after settings.model, on different upstream providers so one
# provider being overloaded doesn't take out the whole chain. Not
# exhaustively vetted for classification quality yet - this is about getting
# a resilient first real run, see docs/05-risks-and-open-questions.md on the
# model choice itself still being open.
FALLBACK_MODELS = [
    "minimax/minimax-m3:free",
    "liquid/lfm-2.5-2.6b:free",
    "google/gemma-4-26b-a4b-it:free",
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
]


class OpenRouterError(RuntimeError):
    """Raised when every candidate model has exhausted its retries, or a
    response that doesn't parse into a valid DocumentClassification."""


def classify_document_text(
    text: str, settings: Settings
) -> DocumentClassification:
    candidates = [settings.model] + [m for m in FALLBACK_MODELS if m != settings.model]
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": _truncate(text)},
    ]

    last_error: Exception | None = None
    for i, model in enumerate(candidates):
        try:
            return _classify_with_model(model, messages, settings)
        except OpenRouterError as exc:
            last_error = exc
            if i < len(candidates) - 1:
                print(f"    {model} failed ({exc}) - falling back to {candidates[i + 1]}")

    raise OpenRouterError(f"All candidate models failed. Last error: {last_error}")


def _classify_with_model(
    model: str, messages: list, settings: Settings
) -> DocumentClassification:
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0,
        "response_format": {
            "type": "json_schema",
            "json_schema": CLASSIFICATION_JSON_SCHEMA,
        },
    }

    backoff = INITIAL_BACKOFF_SECONDS
    last_error_text = None

    for attempt in range(1, ATTEMPTS_PER_MODEL + 1):
        response = requests.post(
            OPENROUTER_CHAT_COMPLETIONS_URL,
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
            },
            data=json.dumps(payload),
            timeout=settings.request_timeout_seconds,
        )

        body = None
        if response.status_code == 200:
            body = response.json()
            body_error = body.get("error") if isinstance(body, dict) else None
            if body_error is None:
                try:
                    content = body["choices"][0]["message"]["content"]
                except (KeyError, IndexError) as exc:
                    raise OpenRouterError(
                        f"Unexpected OpenRouter response shape: {body}"
                    ) from exc
                return _parse_classification(content)
            # HTTP 200 but an error object embedded in the body - OpenRouter
            # does this for some provider-passthrough failures.
            last_error_text = f"(200 w/ embedded error): {body_error}"
        else:
            last_error_text = f"({response.status_code}): {response.text}"

        is_retryable = response.status_code in RETRYABLE_STATUS_CODES or (
            body is not None and body.get("error") is not None
        )
        if is_retryable and attempt < ATTEMPTS_PER_MODEL:
            print(
                f"    {model}: {last_error_text} - retrying in {backoff}s "
                f"(attempt {attempt}/{ATTEMPTS_PER_MODEL})"
            )
            time.sleep(backoff)
            backoff *= 2
            continue

        raise OpenRouterError(f"{model} request failed {last_error_text}")

    raise OpenRouterError(
        f"{model} request failed after {ATTEMPTS_PER_MODEL} attempts: {last_error_text}"
    )


def _parse_classification(content: str) -> DocumentClassification:
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise OpenRouterError(f"Model did not return valid JSON: {content!r}") from exc
    return DocumentClassification.model_validate(data)


def _truncate(text: str, max_chars: int = 6000) -> str:
    # Classification only needs enough of the document to identify its type -
    # docs/01-architecture.md explicitly suggests "its parsed text, or just
    # the first page/element, for speed and cost". A flat char cap is a
    # simple stand-in for that; revisit if it clips signal for longer
    # contracts once real accuracy numbers are in.
    return text[:max_chars]
