"""Message domain model."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class Message(BaseModel):
    id: str
    session_id: str
    sender_id: str
    sender_name: str
    role: str           # "user" | "assistant" | "system"
    content: str
    created_at: Optional[datetime] = None
    metadata: Dict[str, Any] = {}

    class Config:
        from_attributes = True
