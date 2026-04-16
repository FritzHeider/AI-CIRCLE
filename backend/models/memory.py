"""Memory domain models."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel


class SharedMemoryEntry(BaseModel):
    session_id: str
    key: str
    value: Any
    updated_by: Optional[str] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AgentMemoryEntry(BaseModel):
    agent_id: str
    session_id: str
    key: str
    value: Any
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
