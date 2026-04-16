"""ConnectionHub — bridges Redis pub/sub to WebSocket broadcast."""
from __future__ import annotations

import asyncio
import logging
from typing import Dict

from services.redis_service import RedisService
from services.session_manager import SessionManager
from websocket.protocol import WSMessage

logger = logging.getLogger(__name__)


class ConnectionHub:
    """
    Manages the Redis→WebSocket bridge for each active session.

    When a session becomes active, a background task subscribes to the
    Redis session channel and fans out every published message to all
    WebSocket connections in that session.
    """

    def __init__(self, redis: RedisService, session_manager: SessionManager) -> None:
        self._redis = redis
        self._session_manager = session_manager
        # session_id → (asyncio.Event for stopping, asyncio.Task)
        self._listeners: Dict[str, tuple[asyncio.Event, asyncio.Task]] = {}

    # ── Lifecycle ─────────────────────────────────────────────────────────

    async def ensure_listener(self, session_id: str) -> None:
        """Start a Redis subscriber for *session_id* if one is not running."""
        if session_id in self._listeners:
            return

        stop_event = asyncio.Event()
        task = asyncio.create_task(
            self._listen(session_id, stop_event),
            name=f"hub-listener:{session_id}",
        )
        self._listeners[session_id] = (stop_event, task)
        logger.info("Started hub listener: session=%s", session_id)

    async def stop_listener(self, session_id: str) -> None:
        """Stop the Redis subscriber for *session_id*."""
        entry = self._listeners.pop(session_id, None)
        if entry:
            stop_event, task = entry
            stop_event.set()
            try:
                await asyncio.wait_for(task, timeout=3.0)
            except asyncio.TimeoutError:
                task.cancel()
            logger.info("Stopped hub listener: session=%s", session_id)

    async def stop_all(self) -> None:
        for session_id in list(self._listeners):
            await self.stop_listener(session_id)

    # ── Pub/sub → WebSocket bridge ────────────────────────────────────────

    async def _listen(self, session_id: str, stop_event: asyncio.Event) -> None:
        channel = RedisService.session_channel(session_id)
        async with self._redis.client.pubsub() as ps:
            await ps.subscribe(channel)
            try:
                while not stop_event.is_set():
                    msg = await ps.get_message(
                        ignore_subscribe_messages=True, timeout=1.0
                    )
                    if msg and msg["type"] == "message":
                        await self._session_manager.broadcast(
                            session_id, msg["data"]
                        )
            except asyncio.CancelledError:
                pass
            finally:
                await ps.unsubscribe(channel)

    # ── Publish helpers ───────────────────────────────────────────────────

    async def publish(self, message: WSMessage) -> None:
        """Publish a WSMessage to the session channel (Redis → all listeners)."""
        channel = RedisService.session_channel(message.session_id)
        await self._redis.publish(channel, message.to_json())

    async def publish_raw(self, session_id: str, payload: str) -> None:
        channel = RedisService.session_channel(session_id)
        await self._redis.publish(channel, payload)
