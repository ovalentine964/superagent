#!/usr/bin/env bash
# ============================================================
# SUPERAGENT — Database Backup Script
# Supports: sqlite (default), redis
# Backups stored in ./backups/ with timestamp
# ============================================================
set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log()  { echo -e "${GREEN}[backup]${NC} $*"; }
warn() { echo -e "${YELLOW}[warn]${NC} $*"; }
err()  { echo -e "${RED}[error]${NC} $*" >&2; }

BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS="${RETENTION_DAYS:-30}"

# Load .env if present
if [ -f ".env" ]; then
    set -a
    # shellcheck disable=SC1091
    source .env
    set +a
fi

mkdir -p "$BACKUP_DIR"

# ---- SQLite Backup ----
backup_sqlite() {
    local db_path="${DATABASE_URL:-sqlite:///data/superagent.db}"
    # Extract path from sqlite:///path
    db_path="${db_path#sqlite:///}"

    if [ ! -f "$db_path" ]; then
        warn "SQLite database not found at $db_path — skipping"
        return
    fi

    local backup_file="$BACKUP_DIR/superagent_${TIMESTAMP}.db"

    log "Backing up SQLite database..."
    # Use sqlite3 .backup for a consistent snapshot (safe even if DB is in use)
    if command -v sqlite3 >/dev/null 2>&1; then
        sqlite3 "$db_path" ".backup '$backup_file'"
    else
        # Fallback: copy (less safe if DB is actively written)
        cp "$db_path" "$backup_file"
        warn "sqlite3 not found — used cp (less safe for active databases)"
    fi

    # Compress
    gzip "$backup_file"
    log "✅ SQLite backup: ${backup_file}.gz ($(du -h "${backup_file}.gz" | cut -f1))"
}

# ---- Redis Backup ----
backup_redis() {
    local redis_url="${REDIS_URL:-redis://localhost:6379/0}"

    if ! command -v redis-cli >/dev/null 2>&1; then
        warn "redis-cli not found — skipping Redis backup"
        return
    fi

    # Test connection
    if ! redis-cli -u "$redis_url" ping > /dev/null 2>&1; then
        warn "Cannot connect to Redis at $redis_url — skipping"
        return
    fi

    local backup_file="$BACKUP_DIR/redis_${TIMESTAMP}.rdb"

    log "Backing up Redis..."
    # Trigger BGSAVE and copy the RDB file
    redis-cli -u "$redis_url" BGSAVE > /dev/null 2>&1
    sleep 2  # wait for BGSAVE to complete

    # Find the RDB file (works for local Redis)
    local rdb_path
    rdb_path=$(redis-cli -u "$redis_url" CONFIG GET dir | tail -1)/dump.rdb

    if [ -f "$rdb_path" ]; then
        cp "$rdb_path" "$backup_file"
        gzip "$backup_file"
        log "✅ Redis backup: ${backup_file}.gz ($(du -h "${backup_file}.gz" | cut -f1))"
    else
        warn "Could not locate Redis RDB file — try: redis-cli -u $redis_url --rdb $backup_file"
        redis-cli -u "$redis_url" --rdb "$backup_file" 2>/dev/null || true
        if [ -f "$backup_file" ]; then
            gzip "$backup_file"
            log "✅ Redis backup: ${backup_file}.gz"
        fi
    fi
}

# ---- ChromaDB Backup ----
backup_chroma() {
    local chroma_dir="${CHROMA_DATA_DIR:-./data/chroma}"

    if [ ! -d "$chroma_dir" ]; then
        warn "ChromaDB data directory not found at $chroma_dir — skipping"
        return
    fi

    local backup_file="$BACKUP_DIR/chroma_${TIMESTAMP}.tar.gz"

    log "Backing up ChromaDB..."
    tar -czf "$backup_file" -C "$(dirname "$chroma_dir")" "$(basename "$chroma_dir")"
    log "✅ ChromaDB backup: $backup_file ($(du -h "$backup_file" | cut -f1))"
}

# ---- Cleanup old backups ----
cleanup_old() {
    log "Cleaning up backups older than $RETENTION_DAYS days..."
    local count
    count=$(find "$BACKUP_DIR" -name "*.gz" -mtime +"$RETENTION_DAYS" | wc -l)

    if [ "$count" -gt 0 ]; then
        find "$BACKUP_DIR" -name "*.gz" -mtime +"$RETENTION_DAYS" -delete
        log "Removed $count old backup(s)"
    else
        log "No old backups to clean up"
    fi
}

# ---- Main ----
TARGET="${1:-all}"

case "$TARGET" in
    sqlite)  backup_sqlite ;;
    redis)   backup_redis ;;
    chroma)  backup_chroma ;;
    all)
        backup_sqlite
        backup_redis
        backup_chroma
        ;;
    cleanup) cleanup_old ;;
    *)
        echo "Usage: $0 [sqlite|redis|chroma|all|cleanup]"
        exit 1
        ;;
esac

cleanup_old

# ---- Summary ----
echo ""
log "Backup summary:"
ls -lh "$BACKUP_DIR"/*.gz 2>/dev/null || log "No backups found"
echo ""
log "Total backup size: $(du -sh "$BACKUP_DIR" | cut -f1)"
