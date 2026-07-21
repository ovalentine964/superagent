#!/usr/bin/env bash
# ============================================================
# SUPERAGENT — First-Time Setup Script
# Run once after cloning the repo
# ============================================================
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[superagent]${NC} $*"; }
warn() { echo -e "${YELLOW}[warn]${NC} $*"; }
err()  { echo -e "${RED}[error]${NC} $*" >&2; }

# ---- Check prerequisites ----
log "Checking prerequisites..."

command -v python3 >/dev/null 2>&1 || { err "python3 not found. Install Python 3.11+"; exit 1; }
command -v docker >/dev/null 2>&1 || warn "docker not found — local Docker setup will be skipped"

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
log "Python version: $PYTHON_VERSION"

# ---- Create virtual environment ----
if [ ! -d ".venv" ]; then
    log "Creating virtual environment..."
    python3 -m venv .venv
else
    log "Virtual environment already exists"
fi

# Activate
# shellcheck disable=SC1091
source .venv/bin/activate
log "Activated .venv"

# ---- Upgrade pip ----
log "Upgrading pip..."
pip install --upgrade pip --quiet

# ---- Install dependencies ----
log "Installing production dependencies..."
pip install -r requirements.txt --quiet

if [ -f "requirements-dev.txt" ]; then
    log "Installing dev dependencies..."
    pip install -r requirements-dev.txt --quiet
fi

# ---- Create .env from template ----
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        log "Created .env from .env.example — edit it with your secrets"
    else
        log "No .env.example found — creating minimal .env"
        cat > .env << 'EOF'
# SUPERAGENT Environment Variables
# Fill in your actual values below

APP_ENV=development
APP_PORT=8000
LOG_LEVEL=DEBUG
SECRET_KEY=change-me-to-a-random-string
DATABASE_URL=sqlite:///data/superagent.db
REDIS_URL=redis://localhost:6379/0

# Get your key at https://openrouter.ai/keys
OPENROUTER_API_KEY=sk-or-v1-your-key-here

# Get from @BotFather on Telegram
TELEGRAM_BOT_TOKEN=your-bot-token-here

# Optional
HELICONE_API_KEY=
SENTRY_DSN=
EOF
        log "Created minimal .env — edit it with your secrets"
    fi
else
    warn ".env already exists — skipping"
fi

# ---- Create data directories ----
log "Creating data directories..."
mkdir -p data logs tmp

# ---- Initialize database ----
log "Running database migrations (if any)..."
if [ -f "app/db/migrate.py" ]; then
    python app/db/migrate.py
    log "Migrations complete"
else
    log "No migration script found — database will be initialized on first run"
fi

# ---- Docker setup (optional) ----
if command -v docker >/dev/null 2>&1; then
    log "Docker found. To start the full stack:"
    echo ""
    echo "  Development:  docker compose -f docker-compose.dev.yml up"
    echo "  Production:   docker compose up --build"
    echo ""
fi

# ---- Pre-commit hooks (optional) ----
if command -v pre-commit >/dev/null 2>&1; then
    log "Installing pre-commit hooks..."
    pre-commit install
else
    log "pre-commit not found — skipping hooks (install with: pip install pre-commit)"
fi

# ---- Done ----
echo ""
log "✅ Setup complete!"
echo ""
echo "  Next steps:"
echo "  1. Edit .env with your API keys"
echo "  2. Run locally:   source .venv/bin/activate && python -m uvicorn app.main:app --reload"
echo "  3. Run with Docker: docker compose -f docker-compose.dev.yml up"
echo "  4. Run tests:     pytest tests/ -v"
echo ""
