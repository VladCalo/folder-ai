#!/usr/bin/env python3
"""Slack bot: relays questions to answer_question() and replies with the
answer plus grounding/sources. Uses Socket Mode (no public URL/ingress
needed) - fine for this local-dev pass; see SLACK_BOT_SETUP.md to create the
Slack app and get the two tokens this needs.

DEFERRED: this is a small hand-rolled bot, not Onyx's built-in Slack
connector - see backend/README.md "Deferred: Onyx and Unstract".
"""
import sys
from pathlib import Path

from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

BACKEND_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_ROOT))

from foldarai import db  # noqa: E402
from foldarai.config import Settings, load_settings  # noqa: E402
from foldarai.router import answer_question  # noqa: E402

FINANCIAL_DISCLAIMER = (
    "\n\n_FoldarAI answers are generated from this business's own documents "
    "and are not tax or legal advice._"
)


def build_app(settings: Settings) -> App:
    app = App(token=settings.slack_bot_token)

    @app.event("app_mention")
    def handle_mention(event, say):
        _handle_question(event, say, settings)

    @app.event("message")
    def handle_dm(event, say):
        # Only direct messages (channel_type "im"), and never reply to the
        # bot's own messages or other bots - avoids reply loops.
        if event.get("channel_type") == "im" and not event.get("bot_id"):
            _handle_question(event, say, settings)

    return app


def _handle_question(event: dict, say, settings: Settings) -> None:
    text = event.get("text", "")
    # app_mention events include the leading "<@BOTID> " - strip it.
    question = text.split(">", 1)[-1].strip() if text.startswith("<@") else text.strip()
    if not question:
        return

    conn = db.connect(settings)
    try:
        result = answer_question(question, conn, settings)
    except Exception as exc:  # noqa: BLE001 - a bad question must not kill the bot process
        say(f"Something went wrong answering that: {exc}")
        return
    finally:
        conn.close()

    reply = result.answer
    if result.sources:
        reply += "\n\n*Sources:* " + ", ".join(result.sources)
    if not result.grounded:
        reply += "\n\n_(Could not find enough in your documents to answer this confidently.)_"
    if "invoice records" in result.sources:
        reply += FINANCIAL_DISCLAIMER

    say(reply)


def main() -> None:
    load_dotenv(BACKEND_ROOT / ".env")
    settings = load_settings()
    if not settings.slack_bot_token or not settings.slack_app_token:
        raise RuntimeError(
            "SLACK_BOT_TOKEN and SLACK_APP_TOKEN must be set in backend/.env "
            "- see SLACK_BOT_SETUP.md to create a Slack app and get them."
        )

    app = build_app(settings)
    print("FoldarAI Slack bot starting (Socket Mode)...")
    SocketModeHandler(app, settings.slack_app_token).start()


if __name__ == "__main__":
    main()
