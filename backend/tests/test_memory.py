"""Tests for MemoryService."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock


def make_memory_service():
    from services.memory_service import MemoryService

    redis = MagicMock()
    redis.get_json = AsyncMock(return_value=None)
    redis.set_json = AsyncMock()
    redis.delete = AsyncMock()

    supabase = MagicMock()
    supabase.get_shared_memory = AsyncMock(return_value=[
        {"key": "project_name", "value": "AgentHub"},
        {"key": "goal", "value": "multi-agent chat"},
    ])
    supabase.upsert_shared_memory = AsyncMock(return_value={"key": "k", "value": "v"})
    supabase.delete_shared_memory = AsyncMock()
    supabase.get_agent_memory = AsyncMock(return_value=[
        {"key": "persona", "value": "helpful assistant"},
    ])
    supabase.upsert_agent_memory = AsyncMock(return_value={"key": "k", "value": "v"})

    return MemoryService(redis=redis, supabase=supabase), redis, supabase


class TestSharedMemory:
    @pytest.mark.asyncio
    async def test_get_from_supabase_when_cache_miss(self):
        mem, redis, supabase = make_memory_service()
        result = await mem.get_shared_memory("s1")
        assert result == {"project_name": "AgentHub", "goal": "multi-agent chat"}
        supabase.get_shared_memory.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_from_cache_on_hit(self):
        mem, redis, supabase = make_memory_service()
        redis.get_json = AsyncMock(return_value={"cached": "value"})
        result = await mem.get_shared_memory("s1")
        assert result == {"cached": "value"}
        supabase.get_shared_memory.assert_not_called()

    @pytest.mark.asyncio
    async def test_set_invalidates_cache(self):
        mem, redis, supabase = make_memory_service()
        await mem.set_shared_memory("s1", "new_key", "new_value", agent_id="a1")
        supabase.upsert_shared_memory.assert_called_once()
        redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_invalidates_cache(self):
        mem, redis, supabase = make_memory_service()
        await mem.delete_shared_memory("s1", "goal")
        supabase.delete_shared_memory.assert_called_once()
        redis.delete.assert_called_once()


class TestPrivateMemory:
    @pytest.mark.asyncio
    async def test_get_private_memory(self):
        mem, redis, supabase = make_memory_service()
        result = await mem.get_private_memory("a1", "s1")
        assert result == {"persona": "helpful assistant"}

    @pytest.mark.asyncio
    async def test_set_private_memory(self):
        mem, redis, supabase = make_memory_service()
        await mem.set_private_memory("a1", "s1", "key", "value")
        supabase.upsert_agent_memory.assert_called_once()
        redis.delete.assert_called_once()
