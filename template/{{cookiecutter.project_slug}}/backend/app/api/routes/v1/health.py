"""Health check endpoints.

Provides Kubernetes-compatible health check endpoints:
- /health - Simple liveness check
- /health/live - Detailed liveness probe
- /health/ready - Readiness probe with dependency checks
"""
{%- if cookiecutter.use_database or cookiecutter.enable_redis %}
# ruff: noqa: I001 - Imports structured for Jinja2 template conditionals
{%- endif %}

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse
{%- if cookiecutter.use_postgresql or cookiecutter.use_sqlite %}
from sqlalchemy import text
{%- endif %}

{%- if cookiecutter.use_database or cookiecutter.enable_redis %}
from app.api.deps import {% if cookiecutter.use_database %}DBSession{% endif %}{% if cookiecutter.use_database and cookiecutter.enable_redis %}, {% endif %}{% if cookiecutter.enable_redis %}Redis{% endif %}

{%- endif %}
from app.core.config import settings
from app.services.health import build_health_response

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, Any]:
    """Simple liveness probe - check if application is running.

    This is a lightweight check that should always succeed if the
    application is running. Use this for basic connectivity tests.

    Returns:
        {"status": "healthy"}
    """
    return {
        "status": "healthy",
        "max_upload_size_mb": settings.MAX_UPLOAD_SIZE_MB,
    }


@router.get("/health/live")
async def liveness_probe() -> dict[str, Any]:
    """Detailed liveness probe for Kubernetes.

    This endpoint is designed for Kubernetes liveness probes.
    It checks if the application process is alive and responding.
    Failure indicates the container should be restarted.

    Returns:
        Structured response with timestamp and service info.
    """
    return build_health_response(
        status="alive",
        details={
            "version": getattr(settings, "VERSION", "1.0.0"),
            "environment": settings.ENVIRONMENT,
        },
    )


@router.get("/health/ready", response_model=None)
async def readiness_probe(
{%- if cookiecutter.use_database %}
    db: DBSession,
{%- endif %}
{%- if cookiecutter.enable_redis %}
    redis: Redis,
{%- endif %}
) -> dict[str, Any] | JSONResponse:
    """Readiness probe for Kubernetes.

    This endpoint checks if all dependencies are ready to handle traffic.
    It verifies database connections, Redis, and other critical services.
    Failure indicates traffic should be temporarily diverted.

    Checks performed:
    {%- if cookiecutter.use_database %}
    - Database connectivity
    {%- endif %}
    {%- if cookiecutter.enable_redis %}
    - Redis connectivity
    {%- endif %}

    Returns:
        Structured response with individual check results.
        Returns 503 if any critical check fails.
    """
    checks: dict[str, dict[str, Any]] = {}

{%- if cookiecutter.use_postgresql %}
    # Database check
    try:
        start = datetime.now(UTC)
        await db.execute(text("SELECT 1"))
        latency_ms = (datetime.now(UTC) - start).total_seconds() * 1000
        checks["database"] = {
            "status": "healthy",
            "latency_ms": round(latency_ms, 2),
            "type": "postgresql",
        }
    except Exception as e:
        checks["database"] = {
            "status": "unhealthy",
            "error": str(e),
            "type": "postgresql",
        }
{%- endif %}

{%- if cookiecutter.use_mongodb %}
    # Database check
    try:
        start = datetime.now(UTC)
        await db.command("ping")
        latency_ms = (datetime.now(UTC) - start).total_seconds() * 1000
        checks["database"] = {
            "status": "healthy",
            "latency_ms": round(latency_ms, 2),
            "type": "mongodb",
        }
    except Exception as e:
        checks["database"] = {
            "status": "unhealthy",
            "error": str(e),
            "type": "mongodb",
        }
{%- endif %}

{%- if cookiecutter.use_sqlite %}
    # Database check
    try:
        start = datetime.now(UTC)
        db.execute(text("SELECT 1"))
        latency_ms = (datetime.now(UTC) - start).total_seconds() * 1000
        checks["database"] = {
            "status": "healthy",
            "latency_ms": round(latency_ms, 2),
            "type": "sqlite",
        }
    except Exception as e:
        checks["database"] = {
            "status": "unhealthy",
            "error": str(e),
            "type": "sqlite",
        }
{%- endif %}

{%- if cookiecutter.enable_redis %}
    # Redis check
    try:
        start = datetime.now(UTC)
        is_healthy = await redis.ping()
        latency_ms = (datetime.now(UTC) - start).total_seconds() * 1000
        if is_healthy:
            checks["redis"] = {
                "status": "healthy",
                "latency_ms": round(latency_ms, 2),
            }
        else:
            checks["redis"] = {
                "status": "unhealthy",
                "error": "Ping failed",
            }
    except Exception as e:
        checks["redis"] = {
            "status": "unhealthy",
            "error": str(e),
        }
{%- endif %}

    # Determine overall health
    all_healthy = all(
        check.get("status") == "healthy" for check in checks.values()
    ) if checks else True

    response_data = build_health_response(
        status="ready" if all_healthy else "not_ready",
        checks=checks,
    )

    if not all_healthy:
        return JSONResponse(status_code=503, content=response_data)

    return response_data


# Backward compatibility - keep /ready endpoint
@router.get("/ready", response_model=None)
async def readiness_check(
{%- if cookiecutter.use_database %}
    db: DBSession,
{%- endif %}
{%- if cookiecutter.enable_redis %}
    redis: Redis,
{%- endif %}
) -> dict[str, Any] | JSONResponse:
    """Readiness check (alias for /health/ready).

    Deprecated: Use /health/ready instead.
    """
    return await readiness_probe(
{%- if cookiecutter.use_database %}
        db=db,
{%- endif %}
{%- if cookiecutter.enable_redis %}
        redis=redis,
{%- endif %}
    )
