"""Costs REST API — budget queries and cost summaries."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from core.dependencies import get_cost_tracker
from services.cost_tracker import CostTracker

router = APIRouter()


@router.get("/{session_id}/summary")
async def get_cost_summary(
    session_id: str,
    tracker: CostTracker = Depends(get_cost_tracker),
):
    """Return per-agent cost totals and budget status for a session."""
    return await tracker.get_session_summary(session_id)


@router.get("/{session_id}/budget")
async def get_budget(
    session_id: str,
    tracker: CostTracker = Depends(get_cost_tracker),
):
    budget = await tracker.get_session_budget(session_id)
    return {"session_id": session_id, "budget_usd": budget}


@router.put("/{session_id}/budget")
async def set_budget(
    session_id: str,
    budget_usd: float,
    tracker: CostTracker = Depends(get_cost_tracker),
):
    await tracker.set_session_budget(session_id, budget_usd)
    return {"session_id": session_id, "budget_usd": budget_usd}
