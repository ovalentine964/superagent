"""
SUPERAGENT — Basic Metrics Collection
Lightweight, in-process metrics without external dependencies.

Usage:
    from superagent.monitoring.metrics import MetricsCollector, metrics_router
    app.include_router(metrics_router)

    # Track stuff
    collector = MetricsCollector()
    collector.increment("llm.calls")
    collector.observe("llm.latency_ms", 234)
"""

import time
import threading
import os
from collections import defaultdict
from datetime import datetime, timezone

try:
    from fastapi import APIRouter
except ImportError:
    APIRouter = None

router = APIRouter(tags=["metrics"]) if APIRouter else None


class MetricsCollector:
    """Thread-safe in-process metrics collector."""

    def __init__(self):
        self._lock = threading.Lock()
        self._counters = defaultdict(float)
        self._gauges = defaultdict(float)
        self._histograms = defaultdict(list)
        self._last_reset = time.monotonic()

    # ---- Counter: only goes up ----
    def increment(self, name: str, value: float = 1.0):
        with self._lock:
            self._counters[name] += value

    # ---- Gauge: can go up or down ----
    def gauge(self, name: str, value: float):
        with self._lock:
            self._gauges[name] = value

    # ---- Histogram: observations (latency, size, etc.) ----
    def observe(self, name: str, value: float):
        with self._lock:
            # Keep last 1000 observations per metric
            if len(self._histograms[name]) >= 1000:
                self._histograms[name].pop(0)
            self._histograms[name].append(value)

    # ---- Timer context manager ----
    def timer(self, name: str):
        """Usage: with collector.timer("llm.latency_ms"): call_llm()"""
        return _Timer(self, name)

    def snapshot(self) -> dict:
        """Get current metrics snapshot."""
        with self._lock:
            histograms = {}
            for name, values in self._histograms.items():
                if values:
                    sorted_v = sorted(values)
                    n = len(sorted_v)
                    histograms[name] = {
                        "count": n,
                        "min": round(sorted_v[0], 2),
                        "max": round(sorted_v[-1], 2),
                        "mean": round(sum(sorted_v) / n, 2),
                        "p50": round(sorted_v[n // 2], 2),
                        "p95": round(sorted_v[int(n * 0.95)], 2),
                        "p99": round(sorted_v[int(n * 0.99)], 2),
                    }

            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "uptime_seconds": round(time.monotonic() - self._last_reset, 1),
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histograms": histograms,
            }

    def reset(self):
        """Reset all metrics (e.g., for a new collection window)."""
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()
            self._last_reset = time.monotonic()


class _Timer:
    """Context manager for timing operations."""

    def __init__(self, collector: MetricsCollector, name: str):
        self._collector = collector
        self._name = name

    def __enter__(self):
        self._start = time.monotonic()
        return self

    def __exit__(self, *args):
        elapsed_ms = (time.monotonic() - self._start) * 1000
        self._collector.observe(self._name, elapsed_ms)


# ---- Default global collector ----
collector = MetricsCollector()


# ---- Auto-tracking middleware ----
def create_metrics_middleware(app):
    """Attach to FastAPI app to auto-track request counts and latency."""

    @app.middleware("http")
    async def track_requests(request, call_next):
        path = request.url.path
        method = request.method

        # Skip health checks and metrics endpoints
        if path in ("/health", "/health/ready", "/health/live", "/metrics"):
            return await call_next(request)

        collector.increment("http.requests")
        collector.increment(f"http.requests.{method}")

        with collector.timer("http.latency_ms"):
            response = await call_next(request)

        collector.increment(f"http.status.{response.status_code}")

        if response.status_code >= 500:
            collector.increment("http.errors.5xx")
        elif response.status_code >= 400:
            collector.increment("http.errors.4xx")

        return response


# ---- LLM-specific tracking helpers ----
class LLMTracker:
    """Convenience wrapper for tracking LLM API calls."""

    @staticmethod
    def track_call(model: str, input_tokens: int, output_tokens: int,
                   cost_usd: float, latency_ms: float, cached: bool = False):
        collector.increment("llm.calls")
        collector.increment(f"llm.calls.{model}")
        collector.increment("llm.tokens.input", input_tokens)
        collector.increment("llm.tokens.output", output_tokens)
        collector.increment("llm.cost_usd", cost_usd)
        collector.observe("llm.latency_ms", latency_ms)

        if cached:
            collector.increment("llm.cache_hits")
        else:
            collector.increment("llm.cache_misses")

    @staticmethod
    def track_error(model: str, error_type: str):
        collector.increment("llm.errors")
        collector.increment(f"llm.errors.{error_type}")
        collector.increment(f"llm.errors.{model}")


# ---- FastAPI Router ----
if router is not None:
    @router.get("/metrics")
    async def metrics_endpoint():
        """Prometheus-compatible JSON metrics endpoint."""
        return collector.snapshot()

    @router.post("/metrics/reset")
    async def metrics_reset():
        """Reset all metrics counters (useful for debugging)."""
        collector.reset()
        return {"status": "reset"}


# ---- Prometheus text format export ----
def to_prometheus_format() -> str:
    """Export metrics in Prometheus text exposition format."""
    lines = []
    snap = collector.snapshot()

    for name, value in snap["counters"].items():
        safe_name = name.replace(".", "_").replace("-", "_")
        lines.append(f"# TYPE superagent_{safe_name} counter")
        lines.append(f"superagent_{safe_name} {value}")

    for name, value in snap["gauges"].items():
        safe_name = name.replace(".", "_").replace("-", "_")
        lines.append(f"# TYPE superagent_{safe_name} gauge")
        lines.append(f"superagent_{safe_name} {value}")

    for name, stats in snap["histograms"].items():
        safe_name = name.replace(".", "_").replace("-", "_")
        lines.append(f"# TYPE superagent_{safe_name} summary")
        for quantile in ["min", "p50", "p95", "p99", "max"]:
            lines.append(f'superagent_{safe_name}{{quantile="{quantile}"}} {stats[quantile]}')
        lines.append(f"superagent_{safe_name}_count {stats['count']}")

    return "\n".join(lines) + "\n"


# ---- Standalone usage ----
if __name__ == "__main__":
    # Demo: print current metrics
    import json
    collector.increment("demo.counter", 5)
    collector.observe("demo.latency_ms", 42.5)
    collector.observe("demo.latency_ms", 100.3)
    print(json.dumps(collector.snapshot(), indent=2))
