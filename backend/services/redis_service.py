"""Redis service wrapper — pub/sub, presence, cost counters, caching."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, AsyncIterator, Callable, Dict, List, Optional

import redis.asyncio as aioredis
from redis.asyncio.client import PubSub

logger = logging.getLogger(__name__)


class RedisService:
    """Async Redis client used throughout AgentHub."""

    def __init__(self, url: str, max_connections: int = 20) -> None:
        self._url = url
        self._max_connections = max_connections
        self._pool: aioredis.ConnectionPool | None = None
        self._client: aioredis.Redis | None = None

    # ── Lifecycle ─────────────────────────────────────────────────────────

    async def connect(self) -> None:
        self._pool = aioredis.ConnectionPool.from_url(
            self._url,
            max_connections=self._max_connections,
            decode_responses=True,
        )
        self._client = aioredis.Redis(connection_pool=self._pool)
        await self._client.ping()
        logger.debug("Redis pool connected: %s", self._url)

    async def disconnect(self) -> None:
        if self._client:
            await self._client.aclose()
        if self._pool:
            await self._pool.aclose()
        logger.debug("Redis pool closed")

    @property
    def client(self) -> aioredis.Redis:
        if self._client is None:
            raise RuntimeError("RedisService not connected — call connect() first")
        return self._client

    # ── Generic key/value ─────────────────────────────────────────────────

    async def set(self, key: str, value: str, ttl_seconds: Optional[int] = None) -> None:
        if ttl_seconds:
            await self.client.setex(key, ttl_seconds, value)
        else:
            await self.client.set(key, value)

    async def get(self, key: str) -> Optional[str]:
        return await self.client.get(key)

    async def delete(self, key: str) -> None:
        await self.client.delete(key)

    async def exists(self, key: str) -> bool:
        return bool(await self.client.exists(key))

    async def expire(self, key: str, ttl_seconds: int) -> None:
        await self.client.expire(key, ttl_seconds)

    # ── JSON helpers ──────────────────────────────────────────────────────

    async def set_json(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        await self.set(key, json.dumps(value), ttl_seconds)

    async def get_json(self, key: str) -> Any:
        raw = await self.get(key)
        return json.loads(raw) if raw else None

    # ── Hash operations ──────────────────────────────────────────────────

    async def hset(self, name: str, mapping: Dict[str, str]) -> None:
        await self.client.hset(name, mapping=mapping)

    async def hget(self, name: str, key: str) -> Optional[str]:
        return await self.client.hget(name, key)

    async def hgetall(self, name: str) -> Dict[str, str]:
        return await self.client.hgetall(name) or {}

    async def hdel(self, name: str, key: str) -> None:
        await self.client.hdel(name, key)

    # ── Counter helpers ───────────────────────────────────────────────────

    async def incr_float(self, key: str, amount: float) -> float:
        return float(await self.client.incrbyfloat(key, amount))

    async def incr(self, key: str, amount: int = 1) -> int:
        return int(await self.client.incrby(key, amount))

    # ── Pub/Sub ──────────────────────────────────────────────────────────

    async def publish(self, channel: str, message: str) -> int:
        """Publish a message; returns subscriber count."""
        return await self.client.publish(channel, message)

    def pubsub(self) -> PubSub:
        return self.client.pubsub()

    async def subscribe_and_listen(
        self,
        channel: str,
        callback: Callable[[str], Any],
        stop_event: asyncio.Event,
    ) -> None:
        """Subscribe to *channel* and call *callback* for each message until *stop_event* is set."""
        async with self.client.pubsub() as ps:
            await ps.subscribe(channel)
            try:
                while not stop_event.is_set():
                    message = await ps.get_message(
                        ignore_subscribe_messages=True, timeout=1.0
                    )
                    if message and message["type"] == "message":
                        await callback(message["data"])
            finally:
                await ps.unsubscribe(channel)

    # ── Presence ─────────────────────────────────────────────────────────

    async def set_presence(
        self, session_id: str, agent_id: str, status: str, ttl: int = 60
    ) -> None:
        key = f"presence:{session_id}"
        await self.hset(key, {agent_id: status})
        await self.expire(key, ttl)

    async def get_presence(self, session_id: str) -> Dict[str, str]:
        return await self.hgetall(f"presence:{session_id}")

    async def remove_presence(self, session_id: str, agent_id: str) -> None:
        await self.hdel(f"presence:{session_id}", agent_id)

    # ── Session cost counters ─────────────────────────────────────────────

    async def add_session_cost(self, session_id: str, amount_usd: float) -> float:
        key = f"cost:session:{session_id}"
        total = await self.incr_float(key, amount_usd)
        await self.expire(key, 86_400)  # 24 h
        return total

    async def get_session_cost(self, session_id: str) -> float:
        raw = await self.get(f"cost:session:{session_id}")
        return float(raw) if raw else 0.0

    async def add_agent_hourly_cost(
        self, session_id: str, agent_id: str, amount_usd: float
    ) -> float:
        key = f"cost:hour:{session_id}:{agent_id}"
        total = await self.incr_float(key, amount_usd)
        await self.expire(key, 3_600)  # 1 h
        return total

    async def get_agent_hourly_cost(self, session_id: str, agent_id: str) -> float:
        raw = await self.get(f"cost:hour:{session_id}:{agent_id}")
        return float(raw) if raw else 0.0

    # ── Channel names (centralised) ───────────────────────────────────────

    @staticmethod
    def session_channel(session_id: str) -> str:
        return f"session:{session_id}:messages"

    @staticmethod
    def presence_channel(session_id: str) -> str:
        return f"session:{session_id}:presence"

    @staticmethod
    def cost_channel(session_id: str) -> str:
        return f"session:{session_id}:costs"
