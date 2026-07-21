# SUPERAGENT Deployment Guide

## Overview

SUPERAGENT is a merged OpenClaw + Hermes agent system designed for bootstrap deployment at $12–22/month. The stack:

| Component | Role | Cost |
|-----------|------|------|
| **FastAPI app** | Agent core (Telegram, LLM routing, tools) | — |
| **Redis** | Sessions, caching, rate limiting | $0–10/mo |
| **ChromaDB** | Vector memory / RAG | $0 (self-hosted) |
| **OpenRouter** | LLM API gateway | $5–15/mo |
| **Render** | Hosting | $7–17/mo |

---

## Quick Deploy (Render — Recommended)

### 1. Prerequisites

- GitHub account
- [Render account](https://dashboard.render.com/signup)
- [OpenRouter API key](https://openrouter.ai/keys)
- Telegram bot token from [@BotFather](https://t.me/BotFather)

### 2. Deploy

```bash
# Clone and push to your GitHub
git clone <your-repo-url>
cd superagent
git push origin main
```

1. Go to [Render Dashboard](https://dashboard.render.com) → **New** → **Blueprint**
2. Connect your GitHub repo
3. Render reads `render.yaml` and creates services automatically
4. Set secrets in the Render dashboard:
   - `OPENROUTER_API_KEY`
   - `TELEGRAM_BOT_TOKEN`

### 3. Post-Deploy

```bash
# Set Telegram webhook
curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook?url=https://superagent.onrender.com/webhook/telegram"

# Verify health
curl https://superagent.onrender.com/health
```

---

## Docker Deploy (Self-Hosted)

### Production

```bash
# Copy and edit environment
cp .env.example .env
# Edit .env with your secrets

# Build and start
docker compose up --build -d

# Check status
docker compose ps
docker compose logs -f app
```

### Development

```bash
# Start with hot-reload
docker compose -f docker-compose.dev.yml up

# Run in background
docker compose -f docker-compose.dev.yml up -d
```

### Stop

```bash
docker compose down           # keep data volumes
docker compose down -v        # ⚠️ deletes volumes too
```

---

## Local Development

```bash
# First-time setup
bash scripts/setup.sh

# Activate virtualenv
source .venv/bin/activate

# Run with hot-reload
python -m uvicorn app.main:app --reload --port 8000

# Run tests
pytest tests/ -v
```

---

## CI/CD

### GitHub Actions

Two workflows in `.github/workflows/`:

| Workflow | Trigger | What it does |
|----------|---------|-------------|
| `test.yml` | PRs and `develop` pushes | Lint → Test → Docker build test |
| `deploy.yml` | Push to `main` | Lint → Test → Build → Push → Deploy |

### Required GitHub Secrets

| Secret | Where to get it |
|--------|----------------|
| `RENDER_DEPLOY_HOOK_URL` | Render Dashboard → Service → Settings → Deploy Hook |

`GITHUB_TOKEN` is auto-provided for container registry pushes.

---

## Database Management

### SQLite (Default)

```bash
# Backup
bash scripts/backup.sh sqlite

# Backup everything (sqlite + redis + chroma)
bash scripts/backup.sh all

# Cleanup old backups (default: >30 days)
RETENTION_DAYS=7 bash scripts/backup.sh cleanup
```

Backups are stored in `./backups/` as compressed `.gz` files.

### Migrations

```bash
# Run migrations
python app/db/migrate.py

# Or via Alembic (if using)
alembic upgrade head
alembic revision --autogenerate -m "description"
```

---

## Monitoring

### Health Check

```bash
# Full health check (checks redis, db, chroma, llm config)
curl http://localhost:8000/health

# Readiness probe (for k8s/load balancer)
curl http://localhost:8000/health/ready

# Liveness probe (always 200 if alive)
curl http://localhost:8000/health/live
```

### Metrics

```bash
# JSON metrics
curl http://localhost:8000/metrics

# Prometheus format
curl http://localhost:8000/metrics/prometheus
```

Tracked metrics:
- `http.requests` — total request count
- `http.latency_ms` — request latency (p50/p95/p99)
- `llm.calls` — LLM API call count
- `llm.cost_usd` — cumulative LLM spend
- `llm.latency_ms` — LLM response latency
- `llm.cache_hits` / `llm.cache_misses` — semantic cache effectiveness

---

## Cost Optimization

### LLM Spend

1. **Use budget models by default:** Qwen3.5 9B ($0.17/1M input), GPT-OSS 20B ($0.05)
2. **Enable semantic caching** in Redis — avoid duplicate LLM calls
3. **Use OpenRouter** for automatic failover to cheapest provider
4. **Monitor with Helicone** (free tier: 100K requests/month)

### Hosting

| Tier | Stack | Monthly |
|------|-------|---------|
| **Minimum** | Render Free + Redis Free + SQLite | $0 (sleeps after 15min) |
| **Starter** | Render Starter + Redis Free | $7 |
| **Production** | Render Starter + Redis Starter + 1GB disk | $17.25 |
| **Self-hosted** | VPS (DigitalOcean/Hetzner) + Docker | $5–10 |

### Redis Savings

Use [Upstash](https://upstash.com) (serverless Redis, 10K commands/day free) instead of Render Redis:
- Set `REDIS_URL` to your Upstash URL
- Saves $10/month

---

## Troubleshooting

### App won't start

```bash
# Check logs
docker compose logs app
# or on Render: Dashboard → Logs

# Common issues:
# - Missing OPENROUTER_API_KEY or TELEGRAM_BOT_TOKEN
# - Port conflict (change APP_PORT in .env)
# - SQLite file permissions
```

### Telegram bot not responding

```bash
# 1. Check webhook is set
curl "https://api.telegram.org/bot${TOKEN}/getWebhookInfo"

# 2. Check app logs for incoming requests
docker compose logs app | grep telegram

# 3. Re-set webhook
curl "https://api.telegram.org/bot${TOKEN}/setWebhook?url=https://your-app.onrender.com/webhook/telegram"
```

### High LLM costs

```bash
# Check metrics
curl http://localhost:8000/metrics | python -m json.tool

# Review Helicone dashboard for per-model breakdown
# Switch to cheaper models in config
```

### Redis connection refused

```bash
# Check Redis is running
docker compose ps redis
docker compose logs redis

# Test connection
redis-cli -u $REDIS_URL ping
```

---

## Architecture Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| **Platform** | Render | Simple git-push deploy, $7/mo always-on |
| **Database** | SQLite (dev) / Postgres (scale) | Zero-config for bootstrap, migrate when needed |
| **Cache** | Redis (Upstash or Render) | Industry standard, free tier available |
| **LLM Gateway** | OpenRouter | Single key, auto-failover, usage tracking |
| **Vector DB** | ChromaDB | Self-hosted, free, good enough for RAG |
| **Framework** | FastAPI | Async, auto-docs, Python ecosystem |
| **Container** | Docker multi-stage | Small images (~150MB), fast deploys |
| **CI/CD** | GitHub Actions | Free for public repos, tight GitHub integration |
