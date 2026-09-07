"""Generic structured-output OpenRouter call, plus the classification call
built on top of it.

Deliberately plain HTTP requests, not LangChain/LangGraph: each call here is
one request in, one structured JSON object out - no multi-step reasoning, no
tool orchestration, no state across turns. That style of problem (deciding
between tools, composing a multi-part answer) only shows up in router.py,
where a framework would actually earn its keep - see the note there.

Also deliberately not using the `reasoning` param or streaming - `reasoning`
(thinking tokens) is for step-by-step deliberation these calls don't need,
and streaming is for a live UI, not a batch backend call.

Retries with backoff, plus a fallback chain across models from *different*
upstream providers: free-tier models on OpenRouter share a pool across all
OpenRouter users hitting that specific provider (Google AI Studio for Gemma,
NVIDIA's endpoint for Nemotron, ...) - so a 429/502 here is expected under
free-tier use, not a bug, and can affect an entire provider at once. Retrying
the same model handles a brief blip; falling back to a different provider
handles a provider being down for a while, which is what we actually hit in
testing (Google AI Studio, then NVIDIA's endpoint, both returning transient
errors back to back).

Note OpenRouter itself can return a provider error as HTTP 200 with an
`error` key in the body (not just as a non-2xx status), and some free models
ignore strict response_format and wrap their JSON in ```json fences anyway
(observed from minimax/minimax-m3:free in testing) - both handled below.
"""
import json
import re
import time

import requests

from .config import Settings

OPENROUTER_CHAT_COMPLETIONS_URL = "https://openrouter.ai/api/v1/chat/completions"

ATTEMPTS_PER_MODEL = 3
INITIAL_BACKOFF_SECONDS = 3
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

# Tried in order after settings.model, on different upstream providers so one
# provider being overloaded doesn't take out the whole chain. Not
# exhaustively vetted for quality yet - this is about getting a resilient
# first real run, see docs/05-risks-and-open-questions.md on the model choice
# itself still being open.
FALLBACK_MODELS = [
    "minimax/minimax-m3:free",
    "liquid/lfm-2.5-2.6b:free",
    "google/gemma-4-26b-a4b-it:free",
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
]

# Strips a leading/trailing markdown code fence with ANY language tag
# (```json, ```sql, ...) or none - observed both ```json (minimax,
# classification) and ```sql (minimax, router SQL generation) in testing.
_FENCE_RE = re.compile(r"^```(?:\w+)?\s*|\s*```$", re.IGNORECASE | re.MULTILINE)


class OpenRouterError(RuntimeError):
    """Raised when every candidate model has exhausted its retries, or a
    response that doesn't parse into valid JSON."""


def call_structured(
    system_prompt: str,
    user_content: str,
    json_schema: dict,
    settings: Settings,
) -> dict:
    """One structured-output call. Returns the parsed JSON dict - callers
    validate it into their own Pydantic model (see schema.py)."""
    candidates = [settings.model] + [m for m in FALLBACK_MODELS if m != settings.model]
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]

    last_error: Exception | None = None
    for i, model in enumerate(candidates):
        try:
            return _call_with_model(model, messages, json_schema, settings)
        except OpenRouterError as exc:
            last_error = exc
            if i < len(candidates) - 1:
                print(f"    {model} failed ({exc}) - falling back to {candidates[i + 1]}")

    raise OpenRouterError(f"All candidate models failed. Last error: {last_error}")


def _call_with_model(
    model: str, messages: list, json_schema: dict, settings: Settings
) -> dict:
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0,
        "response_format": {
            "type": "json_schema",
            "json_schema": json_schema,
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
                return _parse_json(content)
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


def _parse_json(content: str) -> dict:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # Some free models ignore strict response_format and wrap JSON in
    # markdown fences anyway - strip and retry.
    stripped = _FENCE_RE.sub("", content.strip())
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    # Last resort: a model can also add prose before/after a fenced block
    # (observed: an explanatory paragraph after the closing ```), so the
    # fence-stripped string still isn't valid JSON on its own even though a
    # real JSON object is in there. Grab the outermost {...} and try that.
    # Naive (breaks if a string value itself contains unbalanced braces),
    # but a reasonable last attempt before giving up.
    start, end = content.find("{"), content.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(content[start : end + 1])
        except json.JSONDecodeError:
            pass

    raise OpenRouterError(f"Model did not return valid JSON: {content!r}")


def truncate(text: str, max_chars: int = 6000) -> str:
    # Enough of a document to identify what it is / extract its key fields -
    # docs/01-architecture.md suggests "its parsed text, or just the first
    # page/element, for speed and cost". A flat char cap is a simple
    # stand-in for that; revisit if it clips signal for longer documents once
    # real accuracy numbers are in.
    return text[:max_chars]
