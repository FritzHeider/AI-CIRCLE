"""WebSocket message protocol — all Pydantic models and the WSMessage factory."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── Enumerations ────────────────────────────────────────────────────────────

class MessageType(str, Enum):
    # Client → Server
    CHAT = "chat"
    TYPING_START = "typing_start"
    TYPING_STOP = "typing_stop"
    JOIN = "join"
    LEAVE = "leave"
    PING = "ping"

    # Server → Client
    MESSAGE = "message"
    SYSTEM = "system"
    TYPING = "typing"
    PRESENCE = "presence"
    COST_UPDATE = "cost_update"
    ERROR = "error"
    PONG = "pong"
    HISTORY = "history"


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


# ── Payload models ──────────────────────────────────────────────────────────

class AgentMeta(BaseModel):
    agent_id: str
    agent_name: str
    adapter_type: str
    avatar_color: Optional[str] = None


class CostInfo(BaseModel):
    agent_id: str
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    session_total_usd: float = 0.0
    session_budget_usd: float = 0.0
    budget_pct: float = 0.0


class PresenceInfo(BaseModel):
    agent_id: str
    agent_name: str
    status: str  # "online" | "offline" | "typing"


class ArtifactInfo(BaseModel):
    type: str          # "code" | "image" | "markdown"
    language: Optional[str] = None
    content: str = ""
    url: Optional[str] = None
    filename: Optional[str] = None


# ── Core wire message ────────────────────────────────────────────────────────

class WSMessage(BaseModel):
    """Single wire-format message sent over every WebSocket connection."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: MessageType
    session_id: str
    sender_id: str
    sender_name: str
    role: MessageRole = MessageRole.ASSISTANT
    content: str = ""
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    mentions: List[str] = Field(default_factory=list)
    artifacts: List[ArtifactInfo] = Field(default_factory=list)
    cost: Optional[CostInfo] = None
    presence: Optional[PresenceInfo] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    reply_to: Optional[str] = None   # message id being replied to

    # ── Factory helpers ──────────────────────────────────────────────────

    @classmethod
    def chat(
        cls,
        session_id: str,
        sender_id: str,
        sender_name: str,
        content: str,
        role: MessageRole = MessageRole.ASSISTANT,
        mentions: Optional[List[str]] = None,
        artifacts: Optional[List[ArtifactInfo]] = None,
        cost: Optional[CostInfo] = None,
        reply_to: Optional[str] = None,
    ) -> "WSMessage":
        return cls(
            type=MessageType.MESSAGE,
            session_id=session_id,
            sender_id=sender_id,
            sender_name=sender_name,
            role=role,
            content=content,
            mentions=mentions or [],
            artifacts=artifacts or [],
            cost=cost,
            reply_to=reply_to,
        )

    @classmethod
    def system(
        cls,
        session_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "WSMessage":
        return cls(
            type=MessageType.SYSTEM,
            session_id=session_id,
            sender_id="system",
            sender_name="System",
            role=MessageRole.SYSTEM,
            content=content,
            metadata=metadata or {},
        )

    @classmethod
    def typing(
        cls,
        session_id: str,
        agent_id: str,
        agent_name: str,
        is_typing: bool,
    ) -> "WSMessage":
        return cls(
            type=MessageType.TYPING,
            session_id=session_id,
            sender_id=agent_id,
            sender_name=agent_name,
            presence=PresenceInfo(
                agent_id=agent_id,
                agent_name=agent_name,
                status="typing" if is_typing else "online",
            ),
        )

    @classmethod
    def presence(
        cls,
        session_id: str,
        agent_id: str,
        agent_name: str,
        status: str,
    ) -> "WSMessage":
        return cls(
            type=MessageType.PRESENCE,
            session_id=session_id,
            sender_id=agent_id,
            sender_name=agent_name,
            presence=PresenceInfo(
                agent_id=agent_id,
                agent_name=agent_name,
                status=status,
            ),
        )

    @classmethod
    def cost_update(
        cls,
        session_id: str,
        cost_info: CostInfo,
    ) -> "WSMessage":
        return cls(
            type=MessageType.COST_UPDATE,
            session_id=session_id,
            sender_id="system",
            sender_name="System",
            cost=cost_info,
        )

    @classmethod
    def error(
        cls,
        session_id: str,
        message: str,
        code: Optional[str] = None,
    ) -> "WSMessage":
        return cls(
            type=MessageType.ERROR,
            session_id=session_id,
            sender_id="system",
            sender_name="System",
            role=MessageRole.SYSTEM,
            content=message,
            metadata={"code": code} if code else {},
        )

    @classmethod
    def pong(cls, session_id: str) -> "WSMessage":
        return cls(
            type=MessageType.PONG,
            session_id=session_id,
            sender_id="system",
            sender_name="System",
        )

    def to_json(self) -> str:
        return self.model_dump_json()
