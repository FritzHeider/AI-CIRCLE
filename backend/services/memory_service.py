"""MemoryService — two-tier memory: Redis cache + Supabase persistence."""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from core.config import get_settings
from services.redis_service import RedisService
from services.supabase_service import SupabaseService

logger = logging.getLogger(__name__)
settings = get_settings()


class MemoryService:
    """
    Manages shared project context and per-agent private memory.

    Architecture:
      - Redis: fast read cache with TTL (default 5 min)
      - Supabase: durable persistence
    """

    def __init__(self, redis: RedisService, supabase: SupabaseService) -> None:
        self._redis = redis
        self._supabase = supabase

    # ── Cache key helpers ─────────────────────────────────────────────────

    @staticmethod
    def _shared_cache_key(session_id: str) -> str:
        return f"memory:shared:{session_id}"

    @staticmethod
    def _private_cache_key(agent_id: str, session_id: str) -> str:
        return f"memory:private:{agent_id}:{session_id}"

    # ── Shared memory ─────────────────────────────────────────────────────

    async def get_shared_memory(self, session_id: str) -> Dict[str, Any]:
        """Return all shared memory for a session as a flat dict."""
        cache_key = self._shared_cache_key(session_id)
        cached = await self._redis.get_json(cache_key)
        if cached is not None:
            return cached

        rows = await self._supabase.get_shared_memory(session_id)
        data = {row["key"]: row["value"] for row in rows}
        await self._redis.set_json(cache_key, data, ttl_seconds=settings.memory_cache_ttl_seconds)
        return data

    async def set_shared_memory(
        self,
        session_id: str,
        key: str,
        value: Any,
        agent_id: Optional[str] = None,
    ) -> None:
        await self._supabase.upsert_shared_memory(session_id, key, value, agent_id)
        # Invalidate cache so next read hits DB
        await self._redis.delete(self._shared_cache_key(session_id))
        logger.debug("Shared memory set: session=%s key=%s by=%s", session_id, key, agent_id)

    async def delete_shared_memory(self, session_id: str, key: str) -> None:
        await self._supabase.delete_shared_memory(session_id, key)
        await self._redis.delete(self._shared_cache_key(session_id))

    # ── Private memory ────────────────────────────────────────────────────

    async def get_private_memory(
        self, agent_id: str, session_id: str
    ) -> Dict[str, Any]:
        cache_key = self._private_cache_key(agent_id, session_id)
        cached = await self._redis.get_json(cache_key)
        if cached is not None:
            return cached

        rows = await self._supabase.get_agent_memory(agent_id, session_id)
        data = {row["key"]: row["value"] for row in rows}
        await self._redis.set_json(cache_key, data, ttl_seconds=settings.memory_cache_ttl_seconds)
        return data

    async def set_private_memory(
        self, agent_id: str, session_id: str, key: str, value: Any
    ) -> None:
        await self._supabase.upsert_agent_memory(agent_id, session_id, key, value)
        await self._redis.delete(self._private_cache_key(agent_id, session_id))
        logger.debug("Private memory set: agent=%s session=%s key=%s", agent_id, session_id, key)

    # ── Context builder used by adapters ──────────────────────────────────

    async def build_agent_context(
        self, agent_id: str, session_id: str
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Return (shared_context, private_context) for an agent's system prompt.

        Both are flat dicts; the adapter formats them into its system message.
        """
        shared, private = await asyncio.gather(
            self.get_shared_memory(session_id),
            self.get_private_memory(agent_id, session_id),
        )
        return shared, private

    # ── Bulk operations ───────────────────────────────────────────────────

    async def clear_session_memory(self, session_id: str) -> None:
        """Remove all shared memory for a session (hard delete)."""
        rows = await self._supabase.get_shared_memory(session_id)
        for row in rows:
            await self._supabase.delete_shared_memory(session_id, row["key"])
        await self._redis.delete(self._shared_cache_key(session_id))


# Resolve circular import from asyncio usage inside method
import asyncio  # noqa: E402
