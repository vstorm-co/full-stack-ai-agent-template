{%- if cookiecutter.enable_rag and cookiecutter.enable_redis %}
"""RAG status streaming — Redis pub/sub fan-out for SSE clients."""

import asyncio
import json
import logging
from collections.abc import AsyncIterator

import redis.asyncio as aioredis
import redis.exceptions
from fastapi.sse import ServerSentEvent

logger = logging.getLogger(__name__)


class RAGStatusService:
    """Streams RAG ingestion status events from Redis pub/sub.

    A shared ``aioredis.Redis`` client must be injected at construction time
    (created once during application lifespan and stored in ``app.state``).
    This avoids opening a new Redis connection for every SSE subscriber.
    """

    CHANNEL = "rag_status"

    def __init__(self, client: aioredis.Redis) -> None:
        self._client = client

    async def stream_events(self, *, collections: set[str] | None = None) -> AsyncIterator[ServerSentEvent]:
        """Yield ``ServerSentEvent`` items as they arrive on the ``rag_status`` channel.

        Cleanup is guaranteed via ``finally`` even if the consumer disconnects
        mid-stream.
        """
        event_id = 0

        try:
            async with self._client.pubsub() as pubsub:
                await pubsub.subscribe(self.CHANNEL)
                async for message in pubsub.listen():
                    if message["type"] != "message":
                        continue
                    payload = message["data"]
                    data = payload.decode() if isinstance(payload, bytes) else payload
                    if collections is not None:
                        try:
                            event = json.loads(data)
                        except (json.JSONDecodeError, TypeError):
                            continue
                        if not isinstance(event, dict):
                            continue
                        collection = event.get("collection_name")
                        if not isinstance(collection, str) or collection not in collections:
                            continue
                    event_id += 1
                    yield ServerSentEvent(raw_data=data, event="status", id=str(event_id))
        except asyncio.CancelledError:
            # Client disconnected — propagate cancellation cleanly
            raise
        except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError) as exc:
            logger.warning("RAG SSE stream lost Redis connection: %s", exc)
            yield ServerSentEvent(data="stream_error", event="error", id=str(event_id + 1))
        except Exception:
            logger.exception("RAG SSE stream encountered an unexpected error")
            yield ServerSentEvent(data="stream_error", event="error", id=str(event_id + 1))
            raise
{%- else %}
"""RAG status service — not enabled (requires enable_rag and enable_redis)."""
{%- endif %}
