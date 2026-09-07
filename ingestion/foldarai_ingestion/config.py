"""Runtime configuration for the ingestion service.

Loaded from environment variables (see .env.example). Call load_dotenv()
yourself at your process's entrypoint before calling load_settings() — this
module has no import-time side effects on purpose.
"""
import os
from dataclasses import dataclass

DEFAULT_MODEL = "nvidia/nemotron-3-super-120b-a12b:free"

# Single fixed tenant for this local test/demo. The real deployment model is
# one isolated stack per client (docs/01-architecture.md) - this constant is
# a stand-in until multi-tenant packaging (Phase 7) exists. tenant_id is
# still threaded through every table/row now regardless, per that doc's
# "cheap to add now, expensive to retrofit" rule.
DEFAULT_TENANT_ID = "atelierul-verde-demo"

# The tenant's own legal/company name as it appears on its documents - used
# to tell a sale from a purchase (see db.py's invoices.direction column):
# an invoice where this business is the vendor is revenue, where it's the
# customer is an expense. A real multi-tenant deployment needs this
# per-tenant, not a single constant - flagged, not solved, here.
DEFAULT_TENANT_COMPANY_NAME = "Atelierul Verde SRL"


@dataclass(frozen=True)
class Settings:
    openrouter_api_key: str
    model: str = DEFAULT_MODEL
    request_timeout_seconds: int = 60
    tenant_id: str = DEFAULT_TENANT_ID
    tenant_company_name: str = DEFAULT_TENANT_COMPANY_NAME

    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "folderai"
    db_user: str = "folderai"
    db_password: str = ""

    slack_bot_token: str = ""
    slack_app_token: str = ""

    @property
    def db_dsn(self) -> str:
        return (
            f"host={self.db_host} port={self.db_port} dbname={self.db_name} "
            f"user={self.db_user} password={self.db_password}"
        )


def load_settings() -> Settings:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY is not set. Copy ingestion/.env.example to "
            "ingestion/.env and fill in a real key, or export it directly."
        )
    return Settings(
        openrouter_api_key=api_key,
        model=os.environ.get("OPENROUTER_MODEL", DEFAULT_MODEL),
        tenant_id=os.environ.get("TENANT_ID", DEFAULT_TENANT_ID),
        tenant_company_name=os.environ.get(
            "TENANT_COMPANY_NAME", DEFAULT_TENANT_COMPANY_NAME
        ),
        db_host=os.environ.get("DB_HOST", "localhost"),
        db_port=int(os.environ.get("DB_PORT", "5432")),
        db_name=os.environ.get("DB_NAME", "folderai"),
        db_user=os.environ.get("DB_USER", "folderai"),
        db_password=os.environ.get("DB_PASSWORD", ""),
        slack_bot_token=os.environ.get("SLACK_BOT_TOKEN", ""),
        slack_app_token=os.environ.get("SLACK_APP_TOKEN", ""),
    )
