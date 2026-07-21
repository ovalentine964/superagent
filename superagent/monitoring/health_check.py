"""
SUPERAGENT — Health Check Endpoint
Lightweight, dependency-free health check for Docker/Render/load balancers.

Usage:
    from superagent.monitoring.health_check import health_router
    app.include_router(health_router)
"""

import time
import os
import json
from datetime import datetime, timezone

try:
    from fastapi import APIRouter, Response
except ImportError:
    # Fallback: plain WSGI-compatible health check
    APIRouter = None

# Track when the process started
_START_TIME = time.monotonic()
_START_UTC = datetime.now(timezone.utc).isoformat()

router = APIRouter(tags=["health"]) if APIRouter else None


def _check_redis() -> dict:
    """Check Redis connectivity."""
    redis_url = os.getenv("REDIS_URL", "")
    if not redis_url:
        return {"status": "not_configured"}

    try:
        import redis as redis_lib
        r = redis_lib.from_url(redis_url, socket_timeout=2)
        r.ping()
        return {"status": "healthy", "latency_ms": _measure_latency(r.ping)}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


def _check_database() -> dict:
    """Check database connectivity."""
    db_url = os.getenv("DATABASE_URL", "")
    if not db_url:
        return {"status": "not_configured"}

    if "sqlite" in db_url:
        db_path = db_url.split("///")[-1] if "///" in db_url else "data/superagent.db"
        if os.path.exists(db_path):
            size_mb = os.path.getsize(db_path) / (1024 * 1024)
            return {"status": "healthy", "size_mb": round(size_mb, 2)}
        return {"status": "unhealthy", "error": f"File not found: {db_path}"}

    if "postgresql" in db_url or "postgres" in db_url:
        try:
            import psycopg2
            conn = psycopg2.connect(db_url, connect_timeout=2)
            conn.close()
            return {"status": "healthy"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    return {"status": "unknown_driver"}


def _check_chroma() -> dict:
    """Check ChromaDB connectivity."""
    chroma_url = os.getenv("CHROMA_URL", "")
    if not chroma_url:
        return {"status": "not_configured"}

    try:
        import httpx
        resp = httpx.get(f"{chroma_url}/api/v1/heartbeat", timeout=3)
        if resp.status_code == 200:
            return {"status": "healthy"}
        return {"status": "unhealthy", "error": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


def _check_llm() -> dict:
    """Check LLM API key presence (don't actually call it)."""
    key = os.getenv("OPENROUTER_API_KEY", "")
    if not key:
        return {"status": "not_configured"}
    if key.startswith("sk-or-") or key.startswith("sk-"):
        return {"status": "configured"}
    return {"status": "invalid_format"}


def _measure_latency(fn_result) -> float:
        start = time.monotonic()
        _ = fn_result
        return round((time.monotonic() - start) * 1000, 2)


def get_health_status() -> dict:
    """Full health check — call from any framework."""
    uptime_seconds = round(time.monotonic() - _START_TIME, 1)

    checks = {
        "redis": _check_redis(),
        "database": _check_database(),
        "chroma": _check_chroma(),
        "llm": _check_llm(),
    }

    # Overall status: healthy only if no check is "unhealthy"
    unhealthy = [k for k, v in checks.items() if v.get("status") == "unhealthy"]
    overall = "degraded" if unhealthy else "healthy"

    return {
        "status": overall,
        "version": os.getenv("APP_VERSION", "unknown"),
        "environment": os.getenv("APP_ENV", "unknown"),
        "started_at": _START_UTC,
        "uptime_seconds": uptime_seconds,
        "checks": checks,
        "unhealthy_services": unhealthy or None,
    }


# ---- FastAPI Router (auto-registered if imported) ----
if router is not None:
    @router.get("/health")
    async def health_endpoint(response: Response):
        """Health check endpoint for Docker, Render, and load balancers."""
        status = get_health_status()

        # Return 503 if degraded (unhealthy downstream services)
        if status["status"] == "degraded":
            response.status_code = 503

        return status

    @router.get("/health/ready")
    async def readiness(response: Response):
        """Kubernetes-style readiness probe."""
        status = get_health_status()
        if status["status"] == "unhealthy":
            response.status_code = 503
            return {"ready": False}
        return {"ready": True}

    @router.get("/health/live")
    async def liveness():
        """Kubernetes-style liveness probe — always 200 if process is alive."""
        return {"alive": True, "uptime": round(time.monotonic() - _START_TIME, 1)}


# ---- Standalone usage (python monitoring/health_check.py) ----
if __name__ == "__main__":
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import sys

    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000

    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path in ("/health", "/health/ready", "/health/live"):
                status = get_health_status()
                code = 200 if status["status"] != "degraded" else 503
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(status, indent=2).encode())
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, *args):
            pass  # Suppress access logs

    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    print(f"Health check server on :{port}/health")
    server.serve_forever()
