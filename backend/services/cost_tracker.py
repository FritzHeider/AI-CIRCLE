"""CostTracker — per-session budgets, per-agent hourly caps, rate limiting."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional

from core.config import get_settings
from services.redis_service import RedisService
from services.supabase_service import SupabaseService

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class BudgetCheck:
    """Result of a pre-flight budget check."""
    allowed: bool
    reason: str = ""
    session_total_usd: float = 0.0
    session_budget_usd: float = 0.0
    budget_pct: float = 0.0
    warning: bool = False  # True when >80% consumed


@dataclass
class AgentCostState:
    """Snapshot of an agent's cost state after a call."""
    agent_id: str
    session_id: str
    tokens_in: int = 0
    tokens_out: int = 0
    call_cost_usd: float = 0.0
    session_total_usd: float = 0.0
    agent_hourly_usd: float = 0.0
    session_budget_usd: float = 0.0
    budget_pct: float = 0.0


class CostTracker:
    """
    Enforces spending limits and records cost events.

    Limits (checked in order):
      1. Per-agent hourly cap  → hard stop
      2. Session budget        → hard stop at 100%, warning at 80%
    """

    def __init__(self, redis: RedisService, supabase: SupabaseService) -> None:
        self._redis = redis
        self._supabase = supabase
        # In-memory session budget cache: session_id → budget_usd
        self._budgets: Dict[str, float] = {}

    # ── Budget helpers ────────────────────────────────────────────────────

    async def get_session_budget(self, session_id: str) -> float:
        if session_id in self._budgets:
            return self._budgets[session_id]
        row = await self._supabase.get_session(session_id)
        budget = (row or {}).get("budget_usd", settings.default_session_budget_usd)
        self._budgets[session_id] = float(budget)
        return self._budgets[session_id]

    async def set_session_budget(self, session_id: str, budget_usd: float) -> None:
        self._budgets[session_id] = budget_usd
        await self._supabase.update_session(session_id, {"budget_usd": budget_usd})

    # ── Pre-flight check ──────────────────────────────────────────────────

    async def check_budget(
        self,
        session_id: str,
        agent_id: str,
        estimated_cost_usd: float = 0.0,
    ) -> BudgetCheck:
        """
        Check whether an agent is allowed to make a call.
        Call this BEFORE invoking the LLM.
        """
        hourly = await self._redis.get_agent_hourly_cost(session_id, agent_id)
        hourly_cap = settings.default_agent_hourly_cap_usd
        if hourly + estimated_cost_usd > hourly_cap:
            return BudgetCheck(
                allowed=False,
                reason=(
                    f"Agent hourly cap reached (${hourly:.4f} / ${hourly_cap:.2f})"
                ),
                session_total_usd=await self._redis.get_session_cost(session_id),
                session_budget_usd=await self.get_session_budget(session_id),
            )

        session_total = await self._redis.get_session_cost(session_id)
        budget = await self.get_session_budget(session_id)

        if budget > 0 and session_total + estimated_cost_usd >= budget:
            return BudgetCheck(
                allowed=False,
                reason=f"Session budget exhausted (${session_total:.4f} / ${budget:.2f})",
                session_total_usd=session_total,
                session_budget_usd=budget,
                budget_pct=session_total / budget if budget else 0.0,
            )

        budget_pct = (session_total / budget) if budget > 0 else 0.0
        warning = budget_pct >= settings.budget_warning_threshold

        return BudgetCheck(
            allowed=True,
            reason="ok",
            session_total_usd=session_total,
            session_budget_usd=budget,
            budget_pct=budget_pct,
            warning=warning,
        )

    # ── Record cost ───────────────────────────────────────────────────────

    async def record_cost(
        self,
        session_id: str,
        agent_id: str,
        tokens_in: int,
        tokens_out: int,
        cost_usd: float,
        model: str = "",
        message_id: Optional[str] = None,
    ) -> AgentCostState:
        """Persist cost event and update counters. Returns updated state."""
        # Persist to Supabase
        event = {
            "session_id": session_id,
            "agent_id": agent_id,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "cost_usd": cost_usd,
            "model": model,
            "message_id": message_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await self._supabase.record_cost_event(event)

        # Update Redis counters
        session_total = await self._redis.add_session_cost(session_id, cost_usd)
        agent_hourly = await self._redis.add_agent_hourly_cost(session_id, agent_id, cost_usd)

        budget = await self.get_session_budget(session_id)
        budget_pct = (session_total / budget) if budget > 0 else 0.0

        state = AgentCostState(
            agent_id=agent_id,
            session_id=session_id,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            call_cost_usd=cost_usd,
            session_total_usd=session_total,
            agent_hourly_usd=agent_hourly,
            session_budget_usd=budget,
            budget_pct=budget_pct,
        )

        # Broadcast cost update via Redis
        await self._broadcast_cost_update(state)

        return state

    async def _broadcast_cost_update(self, state: AgentCostState) -> None:
        import json
        payload = {
            "agent_id": state.agent_id,
            "tokens_in": state.tokens_in,
            "tokens_out": state.tokens_out,
            "cost_usd": state.call_cost_usd,
            "session_total_usd": state.session_total_usd,
            "session_budget_usd": state.session_budget_usd,
            "budget_pct": state.budget_pct,
        }
        channel = RedisService.cost_channel(state.session_id)
        await self._redis.publish(channel, json.dumps(payload))

    # ── Summaries ─────────────────────────────────────────────────────────

    async def get_session_summary(self, session_id: str) -> Dict:
        totals = await self._supabase.get_session_cost_summary(session_id)
        session_total = await self._redis.get_session_cost(session_id)
        budget = await self.get_session_budget(session_id)
        return {
            "session_id": session_id,
            "total_usd": session_total,
            "budget_usd": budget,
            "budget_pct": (session_total / budget) if budget > 0 else 0.0,
            "agents": totals,
        }
