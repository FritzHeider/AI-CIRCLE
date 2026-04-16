"""Tests for CostTracker."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from services.cost_tracker import CostTracker, BudgetCheck, AgentCostState


def make_tracker(session_cost=0.0, hourly_cost=0.0, budget=5.0):
    redis = MagicMock()
    redis.get_session_cost = AsyncMock(return_value=session_cost)
    redis.get_agent_hourly_cost = AsyncMock(return_value=hourly_cost)
    redis.add_session_cost = AsyncMock(return_value=session_cost + 0.01)
    redis.add_agent_hourly_cost = AsyncMock(return_value=hourly_cost + 0.01)
    redis.publish = AsyncMock()

    supabase = MagicMock()
    supabase.get_session = AsyncMock(return_value={"budget_usd": budget})
    supabase.record_cost_event = AsyncMock(return_value={"id": "evt-1"})

    tracker = CostTracker(redis=redis, supabase=supabase)
    return tracker


class TestBudgetCheck:
    @pytest.mark.asyncio
    async def test_allowed_under_budget(self):
        tracker = make_tracker(session_cost=1.0, budget=5.0)
        result = await tracker.check_budget("s1", "a1")
        assert result.allowed is True
        assert result.warning is False

    @pytest.mark.asyncio
    async def test_warning_at_80_percent(self):
        tracker = make_tracker(session_cost=4.1, budget=5.0)
        result = await tracker.check_budget("s1", "a1")
        assert result.allowed is True
        assert result.warning is True

    @pytest.mark.asyncio
    async def test_blocked_at_budget_limit(self):
        tracker = make_tracker(session_cost=5.0, budget=5.0)
        result = await tracker.check_budget("s1", "a1", estimated_cost_usd=0.01)
        assert result.allowed is False
        assert "budget" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_hourly_cap_enforcement(self):
        tracker = make_tracker(hourly_cost=1.0)
        # Default hourly cap is 1.0 USD — already at the limit
        result = await tracker.check_budget("s1", "a1", estimated_cost_usd=0.01)
        assert result.allowed is False
        assert "hourly" in result.reason.lower()


class TestRecordCost:
    @pytest.mark.asyncio
    async def test_record_updates_redis(self):
        tracker = make_tracker()
        state = await tracker.record_cost(
            session_id="s1",
            agent_id="a1",
            tokens_in=100,
            tokens_out=200,
            cost_usd=0.001,
            model="claude-sonnet-4-6",
        )
        assert isinstance(state, AgentCostState)
        assert state.tokens_in == 100
        assert state.tokens_out == 200
        assert state.cost_usd == 0.001

    @pytest.mark.asyncio
    async def test_record_persists_to_supabase(self):
        tracker = make_tracker()
        await tracker.record_cost(
            session_id="s1",
            agent_id="a1",
            tokens_in=50,
            tokens_out=100,
            cost_usd=0.0005,
        )
        tracker._supabase.record_cost_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_record_publishes_to_redis(self):
        tracker = make_tracker()
        await tracker.record_cost("s1", "a1", 10, 20, 0.001)
        tracker._redis.publish.assert_called_once()
