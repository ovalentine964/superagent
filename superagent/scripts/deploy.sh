#!/usr/bin/env bash
# ============================================================
# SUPERAGENT — Deployment Script
# Supports: render (default), docker, local
# ============================================================
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log()  { echo -e "${GREEN}[deploy]${NC} $*"; }
warn() { echo -e "${YELLOW}[warn]${NC} $*"; }
err()  { echo -e "${RED}[error]${NC} $*" >&2; }

DEPLOY_TARGET="${1:-render}"
BRANCH="${2:-main}"

usage() {
    echo "Usage: $0 [render|docker|local] [branch]"
    echo ""
    echo "  render  — Trigger Render deploy via webhook (default)"
    echo "  docker  — Build and deploy Docker image locally"
    echo "  local   — Run locally with uvicorn"
    exit 1
}

# ---- Pre-flight checks ----
log "Pre-flight checks..."

# Check .env exists
if [ ! -f ".env" ] && [ "$DEPLOY_TARGET" != "render" ]; then
    err ".env file not found. Run scripts/setup.sh first."
    exit 1
fi

# Load .env if it exists
if [ -f ".env" ]; then
    set -a
    # shellcheck disable=SC1091
    source .env
    set +a
fi

case "$DEPLOY_TARGET" in
    render)
        # ---- Render deploy via webhook ----
        if [ -z "${RENDER_DEPLOY_HOOK_URL:-}" ]; then
            err "RENDER_DEPLOY_HOOK_URL not set."
            err "Get it from: Render Dashboard → Service → Settings → Deploy Hook"
            exit 1
        fi

        log "Pushing to $BRANCH..."
        git push origin "$BRANCH"

        log "Triggering Render deploy..."
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
            -X POST "$RENDER_DEPLOY_HOOK_URL" \
            -H "Accept: application/json")

        if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "201" ]; then
            log "✅ Deploy triggered successfully (HTTP $HTTP_CODE)"
            log "Monitor at: https://dashboard.render.com"
        else
            err "Deploy trigger failed (HTTP $HTTP_CODE)"
            exit 1
        fi
        ;;

    docker)
        # ---- Docker deploy ----
        command -v docker >/dev/null 2>&1 || { err "docker not found"; exit 1; }

        log "Building Docker image..."
        docker build -t superagent:latest -t superagent:"$(git rev-parse --short HEAD)" .

        log "Stopping existing containers..."
        docker compose down 2>/dev/null || true

        log "Starting services..."
        docker compose up -d

        log "Waiting for health check..."
        sleep 10

        if curl -sf http://localhost:${APP_PORT:-8000}/health > /dev/null 2>&1; then
            log "✅ Deployment successful — app is healthy"
            docker compose ps
        else
            err "Health check failed. Check logs: docker compose logs app"
            exit 1
        fi
        ;;

    local)
        # ---- Local run ----
        command -v python3 >/dev/null 2>&1 || { err "python3 not found"; exit 1; }

        if [ -d ".venv" ]; then
            # shellcheck disable=SC1091
            source .venv/bin/activate
        fi

        log "Starting SUPERAGENT locally on port ${APP_PORT:-8000}..."
        python -m uvicorn app.main:app \
            --host 0.0.0.0 \
            --port "${APP_PORT:-8000}" \
            --reload \
            --log-level "${LOG_LEVEL:-debug}"
        ;;

    *)
        usage
        ;;
esac
