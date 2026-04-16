"""Session domain model."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Session(BaseModel):
    id: str
    name: str
    description: str = ""
    budget_usd: float = 5.0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        from_attributes = True


class SessionCreate(BaseModel):
    name: str
    description: str = ""
    budget_usd: float = 5.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SessionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    budget_usd: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None
