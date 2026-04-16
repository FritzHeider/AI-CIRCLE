"""Agent configuration model."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AgentCapability(str):
    """Free-form capability tag, e.g. 'code', 'image', 'sql', 'reasoning'."""


class AgentConfig(BaseModel):
    id: str
    name: str
    adapter_type: str                       # maps to @register_adapter key
    description: str = ""
    capabilities: List[str] = Field(default_factory=list)
    avatar_color: str = "#6366f1"
    priority: int = 50                      # 0 = highest priority
    enabled: bool = True
    system_prompt_override: Optional[str] = None
    model_override: Optional[str] = None
    extra_config: Dict[str, Any] = Field(default_factory=dict)

    # Budget — can override session defaults
    hourly_cap_usd: Optional[float] = None

    class Config:
        from_attributes = True
