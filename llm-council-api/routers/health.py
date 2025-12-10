"""
Health check endpoints for Kubernetes/Docker orchestration.

Provides /health (liveness) and /ready (readiness) probes.
"""

import asyncio
from fastapi import APIRouter, Response, status

from db import get_database
from core.cache import get_redis_client
from core.circuit_breaker import get_circuit_breaker_status

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """
    Liveness Probe

    Returns 200 if the application is running.
    Used by Kubernetes to know if the pod should be restarted.
    """
    return {"status": "healthy", "service": "llm-council-api"}


@router.get("/ready")
async def readiness_check(response: Response):
    """
    Readiness Probe

    Returns 200 if the application is ready to serve traffic.
    Checks:
    - MongoDB connection
    - Redis connection (optional)
    - Circuit breaker status

    Used by Kubernetes to know if the pod should receive traffic.
    """
    checks = {"mongodb": "unknown", "redis": "unknown", "circuit_breaker": "unknown"}

    is_ready = True

    # Check MongoDB
    try:
        db = await get_database()
        await asyncio.wait_for(db.command("ping"), timeout=2.0)
        checks["mongodb"] = "healthy"
    except asyncio.TimeoutError:
        checks["mongodb"] = "timeout"
        is_ready = False
    except Exception as e:
        checks["mongodb"] = f"unhealthy: {str(e)[:50]}"
        is_ready = False

    # Check Redis (optional - not required for readiness)
    try:
        redis_client = get_redis_client()
        if redis_client is not None:
            redis_client.ping()
            checks["redis"] = "healthy"
        else:
            checks["redis"] = "disabled"
    except Exception as e:
        checks["redis"] = f"unavailable: {str(e)[:50]}"
        # Don't fail readiness if Redis is down (we have fallback)

    # Check Circuit Breaker
    try:
        breaker_status = get_circuit_breaker_status("openrouter")
        checks["circuit_breaker"] = breaker_status.get("state", "unknown")

        # If circuit is open, we're not fully ready
        if breaker_status.get("state") == "open":
            is_ready = False
    except Exception as e:
        checks["circuit_breaker"] = f"error: {str(e)[:50]}"

    # Set response status
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {"status": "ready" if is_ready else "not_ready", "checks": checks}


@router.get("/metrics")
async def metrics_endpoint():
    """
    Prometheus Metrics Endpoint

    Exports metrics in Prometheus format for monitoring.
    """
    try:
        from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

        metrics = generate_latest()
        return Response(content=metrics, media_type=CONTENT_TYPE_LATEST)
    except ImportError:
        return {
            "error": "Prometheus client not installed",
            "message": "Install prometheus-client to enable metrics",
        }
