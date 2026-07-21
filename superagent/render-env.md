# Render Environment Variables Setup Guide

## Quick Start

1. Push your repo to GitHub
2. Go to [Render Dashboard](https://dashboard.render.com) → **New** → **Blueprint**
3. Select your repo — Render reads `render.yaml` automatically
4. Fill in the secrets below

---

## Required Variables (set in Render Dashboard)

These must be set manually — they are secrets and not committed to git.

### `OPENROUTER_API_KEY`

- **Where to get it:** [openrouter.ai/keys](https://openrouter.ai/keys)
- **What it does:** Routes LLM requests to the cheapest/fastest model provider
- **Format:** `sk-or-v1-xxxxxxxxxxxx`
- **Cost impact:** This is your primary LLM spend — budget models cost $0.05–0.30/1M tokens

### `TELEGRAM_BOT_TOKEN`

- **Where to get it:** Message [@BotFather](https://t.me/BotFather) on Telegram → `/newbot`
- **What it does:** Authenticates your Telegram bot for sending/receiving messages
- **Format:** `123456789:ABCdefGHIjklMNOpqrSTUvwxYZ`
- **After deploy:** Set the webhook URL:
  ```
  https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://superagent.onrender.com/webhook/telegram
  ```

### `SECRET_KEY`

- **Auto-generated** by Render if you use `generateValue: true` in render.yaml
- **What it does:** Signs sessions, JWT tokens, and internal cryptographic operations
- **If manual:** Generate with `python -c "import secrets; print(secrets.token_urlsafe(64))"`

---

## Optional Variables

### `HELICONE_API_KEY`

- **Where to get it:** [helicone.ai](https://helicone.ai) (free tier: 100K requests/month)
- **What it does:** Tracks LLM API costs, latency, and cache hit rates
- **How to use:** Add as header `Helicone-Auth: Bearer <key>` to OpenRouter requests

### `SENTRY_DSN`

- **Where to get it:** [sentry.io](https://sentry.io) (free tier: 5K events/month)
- **What it does:** Captures unhandled exceptions and performance traces
- **Format:** `https://xxx@xxx.ingest.sentry.io/xxx`

### `CHROMA_URL`

- **Default:** Not needed if running ChromaDB locally in Docker
- **For Render:** ChromaDB isn't on Render's blueprint — use a hosted instance or run it separately
- **Alternative:** Use [Chroma Cloud](https://www.trychroma.com/) or self-host on Fly.io

---

## Render-Specific Notes

| Setting | Value |
|---------|-------|
| **Render Port** | Render sets `PORT` env var. Your app must listen on `$PORT` (defaults to 10000) |
| **Region** | `oregon` (US West) or `frankfurt` (EU) — choose based on user proximity |
| **Disk** | 1GB persistent disk mounted at `/app/data` for SQLite + vector DB |
| **Auto-deploy** | Every push to `main` triggers a new deploy |
| **Build time** | ~3-5 min (Docker build with cached layers) |

## Cost Breakdown (Render)

| Service | Plan | Monthly Cost |
|---------|------|-------------|
| Web Service | Starter (512MB) | $7 |
| Redis | Starter (256MB) | $10 |
| Disk (1GB) | — | $0.25 |
| **Total** | | **$17.25** |

> **Budget tip:** Use Redis Free (25MB) for development/small scale → **$7.25/mo total**.
> The free Redis tier has no persistence — fine for caching, not for critical state.

---

## After Deployment

1. **Health check:** Visit `https://superagent.onrender.com/health`
2. **Set Telegram webhook:**
   ```bash
   curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook?url=https://superagent.onrender.com/webhook/telegram"
   ```
3. **Test the bot:** Send a message to your bot on Telegram
4. **Check logs:** Render Dashboard → Logs tab
5. **Monitor costs:** OpenRouter dashboard → Usage tab
