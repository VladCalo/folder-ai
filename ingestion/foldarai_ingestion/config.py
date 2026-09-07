"""Runtime configuration for the ingestion service.

Loaded from environment variables (see .env.example). Call load_dotenv()
yourself at your process's entrypoint before calling load_settings() — this
module has no import-time side effects on purpose.
"""
import os
from dataclasses import dataclass

DEFAULT_MODEL = "nvidia/nemotron-3-super-120b-a12b:free"


@dataclass(frozen=True)
class Settings:
    openrouter_api_key: str
    model: str = DEFAULT_MODEL
    request_timeout_seconds: int = 60


def load_settings() -> Settings:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY is not set. Copy ingestion/.env.example to "
            "ingestion/.env and fill in a real key, or export it directly."
        )
    model = os.environ.get("OPENROUTER_MODEL", DEFAULT_MODEL)
    return Settings(openrouter_api_key=api_key, model=model)
