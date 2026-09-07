# Slack bot setup

I can't create a Slack app for you (it needs your Slack account/workspace
admin access) - these are the manual steps. UI labels may drift slightly
from what you see; the shape (Socket Mode + bot token + app token + event
subscriptions) has been stable for a long time.

1. Go to https://api.slack.com/apps → **Create New App** → **From scratch**.
   Name it (e.g. "FoldarAI Dev"), pick your workspace.
2. **Socket Mode**: Settings → Socket Mode → toggle on. This prompts you to
   create an **App-Level Token** with the `connections:write` scope — copy
   it (starts with `xapp-`) into `SLACK_APP_TOKEN` in `ingestion/.env`.
3. **Bot Token Scopes**: OAuth & Permissions → Scopes → Bot Token Scopes →
   add `app_mentions:read`, `chat:write`, `im:history`, `im:read`, `im:write`.
4. **Event Subscriptions**: toggle on → Subscribe to bot events → add
   `app_mention` and `message.im`.
5. **Install to Workspace**: OAuth & Permissions → Install to Workspace →
   authorize. Copy the **Bot User OAuth Token** (starts with `xoxb-`) into
   `SLACK_BOT_TOKEN` in `ingestion/.env`.
6. Invite the bot to a channel (`/invite @FoldarAI Dev`) or just DM it
   directly - both work per `slack_bot.py`'s event handlers.
7. Run it (with the venv active and `sample-data/` already populated -
   see `README.md`):
   ```bash
   python slack_bot.py
   ```
8. Ask it something in Slack, e.g. "What was our most profitable month this
   year?" or "What's the notice period in Ioana Pop's contract?"

Runs via Socket Mode - no public URL, ingress, or Cloudflare tunnel needed
for this local-dev pass.
