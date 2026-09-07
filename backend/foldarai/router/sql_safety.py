"""Read-only safety check for LLM-generated SQL, applied in tools.py before
a generated query is ever executed. Isolated in its own module on purpose -
security-sensitive validation logic deserves to be easy to find, read in
full, and audit on its own, separate from the prompt/orchestration code
around it.

This is defense in depth, not the real fix: the `folderai` Postgres role
currently has full owner rights on the database (see k3s-rpi5's
apps/folderai/db-init-job.yaml) - a generated query executes with those
privileges. The actual fix is a dedicated read-only role for this tool
specifically, which is a "come back to this" item, not done yet (see
backend/README.md "Deferred: Onyx and Unstract").
"""
import re

_FORBIDDEN_KEYWORDS = [
    "insert", "update", "delete", "drop", "alter", "truncate",
    "grant", "revoke", "create", "copy", "call", "execute", "merge",
]


class SqlSafetyError(RuntimeError):
    """Raised when a generated query fails this check - never executed."""


def validate_readonly_sql(sql: str) -> None:
    normalized = sql.strip().rstrip(";").strip()
    if not re.match(r"(?is)^select\b", normalized):
        raise SqlSafetyError(f"Generated query is not a SELECT statement: {sql!r}")
    if ";" in normalized:
        raise SqlSafetyError(f"Generated query contains multiple statements: {sql!r}")
    lowered = normalized.lower()
    for word in _FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{word}\b", lowered):
            raise SqlSafetyError(f"Generated query contains forbidden keyword {word!r}: {sql!r}")
    if "%(tenant_id)s" not in sql:
        raise SqlSafetyError(f"Generated query is missing the required tenant_id filter: {sql!r}")
