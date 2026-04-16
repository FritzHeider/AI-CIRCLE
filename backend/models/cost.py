"""Cost domain models."""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class CostEvent(BaseModel):
    id: Optional[str] = None
    session_id: str
    agent_id: str
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    model: str = ""
    message_id: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AgentCostSummary(BaseModel):
    agent_id: str
    tokens_in: int
    tokens_out: int
    cost_usd: float


class SessionCostSummary(BaseModel):
    session_id: str
    total_usd: float
    budget_usd: float
    budget_pct: float
    agents: list[AgentCostSummary]
