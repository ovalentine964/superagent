# SUPERAGENT — Production Docker Image
# Multi-stage build for smaller final image

# ── Stage 1: Build ──────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Stage 2: Production ────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Create non-root user
RUN groupadd -r superagent && \
    useradd -r -g superagent -d /app -s /sbin/nologin superagent && \
    mkdir -p /app/data /app/workspace/memory /app/workspace/skills && \
    chown -R superagent:superagent /app

# Copy application code
COPY agents/ agents/
COPY memory/ memory/
COPY tools/ tools/
COPY gateway/ gateway/
COPY data/ data/
COPY config.yaml .
COPY setup.py .

# Set ownership
RUN chown -R superagent:superagent /app

# Switch to non-root user
USER superagent

# Environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"

# Expose API port
EXPOSE 8080

# Default command
CMD ["python", "-m", "superagent.main"]
