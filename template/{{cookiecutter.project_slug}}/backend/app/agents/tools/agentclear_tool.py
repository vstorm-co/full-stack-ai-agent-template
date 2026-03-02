"""
AgentClear integration — dynamic API discovery and execution for AI agents.

Enables agents to find and call 60+ API services (PDF extraction, image
generation, web scraping, data enrichment, etc.) by describing what they need
in natural language.

Install: pip install agentclear
Docs: https://agentclear.dev/docs
"""
import os
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

try:
    from agentclear import AgentClear
    _AGENTCLEAR_AVAILABLE = True
except ImportError:
    _AGENTCLEAR_AVAILABLE = False
    logger.debug("agentclear not installed — dynamic API discovery disabled")


def is_agentclear_configured() -> bool:
    """Check if AgentClear is available and configured."""
    return _AGENTCLEAR_AVAILABLE and bool(os.getenv("AGENTCLEAR_API_KEY"))


def get_client() -> Optional["AgentClear"]:
    """Get an AgentClear client instance."""
    if not is_agentclear_configured():
        return None
    return AgentClear(api_key=os.environ["AGENTCLEAR_API_KEY"])


async def discover_services(
    query: str,
    max_results: int = 5,
    min_trust_tier: str = "basic",
) -> list[dict[str, Any]]:
    """
    Search for API services matching a natural language query.

    Args:
        query: What you need (e.g., "extract tables from PDF",
               "generate image from text prompt")
        max_results: Maximum number of results to return
        min_trust_tier: Minimum trust level ("basic", "verified", "premium")

    Returns:
        List of matching services with id, name, description, trust_tier, price
    """
    client = get_client()
    if client is None:
        return [{"error": "AgentClear not configured"}]

    results = client.discover(
        query=query,
        max_results=max_results,
        min_trust_tier=min_trust_tier,
    )
    return [
        {
            "id": svc.id,
            "name": svc.name,
            "description": svc.description,
            "trust_tier": svc.trust_tier,
            "price_per_call": svc.price_per_call,
        }
        for svc in results
    ]


async def call_service(
    service_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """
    Call a discovered API service through AgentClear's secure proxy.

    Args:
        service_id: The service ID from discover_services results
        payload: Data to send to the service

    Returns:
        Service response with data, cost, and metadata
    """
    client = get_client()
    if client is None:
        return {"error": "AgentClear not configured"}

    response = client.proxy(service_id=service_id, body=payload)
    return {
        "data": response.data,
        "cost": response.cost,
        "service_id": service_id,
    }
