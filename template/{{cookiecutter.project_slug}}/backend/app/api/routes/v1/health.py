"""Health check endpoints.

Provides Kubernetes-compatible health check endpoints:
- /health - Simple liveness check
- /health/live - Detailed liveness probe
- /health/ready - Readiness probe with dependency checks
"""
{%- if cookiecutter.use_database or cookiecutter.enable_redis %}
# ruff: noqa: I001 - Imports structured for Jinja2 template conditionals
{%- endif %}

import socket
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

{%- if cookiecutter.use_database or cookiecutter.enable_redis %}
from app.api.deps import {% if cookiecutter.use_database %}DBSession{% endif %}{% if cookiecutter.use_database and cookiecutter.enable_redis %}, {% endif %}{% if cookiecutter.enable_redis %}Redis{% endif %}

{%- endif %}
from app.core.config import settings
from app.schemas.base import HealthDetailResponse, HealthResponse
from app.services.health import build_health_response

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
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


@router.get("/health/live", response_model=HealthDetailResponse)
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

{%- if cookiecutter.enable_redis %}
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

{%- if cookiecutter.enable_rag and cookiecutter.vector_store == "milvus" %}
    try:
        start = datetime.now(UTC)
        with socket.create_connection(
            (settings.MILVUS_HOST, settings.MILVUS_PORT), timeout=2
        ):
            pass
        latency_ms = (datetime.now(UTC) - start).total_seconds() * 1000
        checks["vector_store"] = {
            "status": "healthy",
            "latency_ms": round(latency_ms, 2),
            "type": "milvus",
        }
    except Exception as e:
        checks["vector_store"] = {
            "status": "unhealthy",
            "error": str(e),
            "type": "milvus",
        }
{%- elif cookiecutter.enable_rag and cookiecutter.vector_store == "qdrant" %}
    try:
        start = datetime.now(UTC)
        with socket.create_connection(
            (settings.QDRANT_HOST, settings.QDRANT_PORT), timeout=2
        ):
            pass
        latency_ms = (datetime.now(UTC) - start).total_seconds() * 1000
        checks["vector_store"] = {
            "status": "healthy",
            "latency_ms": round(latency_ms, 2),
            "type": "qdrant",
        }
    except Exception as e:
        checks["vector_store"] = {
            "status": "unhealthy",
            "error": str(e),
            "type": "qdrant",
        }
{%- elif cookiecutter.enable_rag %}
    checks["vector_store"] = {
        "status": "unknown",
        "detail": "configured but no probe implemented",
        "type": "{{ cookiecutter.vector_store }}",
    }
{%- endif %}

    # LLM provider — config-only check (avoid spending money on a probe call).
    llm_provider = (getattr(settings, "LLM_PROVIDER", None) or "").lower()
    if llm_provider:
        key_field = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "google": "GOOGLE_API_KEY",
            "openrouter": "OPENROUTER_API_KEY",
        }.get(llm_provider)
        api_key = getattr(settings, key_field, None) if key_field else None
        checks["llm"] = {
            "status": "healthy" if api_key else "unhealthy",
            "provider": llm_provider,
            "detail": "API key configured" if api_key else "API key missing",
        }
    else:
        checks["llm"] = {"status": "unknown", "detail": "not configured"}

{%- if cookiecutter.enable_billing %}
    stripe_key = getattr(settings, "STRIPE_SECRET_KEY", None)
    checks["stripe"] = (
        {"status": "healthy", "detail": "key configured"}
        if stripe_key
        else {"status": "unknown", "detail": "not configured"}
    )
{%- endif %}

{%- if cookiecutter.use_celery %}
    # Background worker — config-only (a real probe needs an end-to-end ping).
    broker_url = getattr(settings, "CELERY_BROKER_URL", None)
    checks["worker"] = (
        {"status": "healthy", "detail": "broker configured"}
        if broker_url
        else {"status": "unknown", "detail": "not configured"}
    )
{%- endif %}

    # Determine overall health — only db + redis are critical for readiness.
    critical = {k: v for k, v in checks.items() if k in ("database", "redis")}
    all_healthy = (
        all(check.get("status") == "healthy" for check in critical.values())
        if critical
        else True
    )

    # The admin /system page reads each service from the top level, so flatten
    # the checks alongside the structured `checks` field for K8s probes.
    response_data = build_health_response(
        status="ready" if all_healthy else "not_ready",
        checks=checks,
    )
    response_data.update(checks)

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
