"""HumanAdapter — represents a human participant in the group chat."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from adapters.base import AgentAdapter, AdapterResponse
from adapters.registry import register_adapter


@register_adapter("human")
class HumanAdapter(AgentAdapter):
    """
    Adapter for human participants.

    Humans send messages via the WebSocket client; this adapter
    does NOT auto-generate responses. It exists so the routing
    engine can treat humans consistently with AI agents and to
    handle @human mentions gracefully.
    """

    adapter_type = "human"
    capabilities = ["general", "review", "approval"]

    async def respond(
        self,
        session_id: str,
        agent_config: Dict[str, Any],
        user_message: str,
        history: List[Dict[str, Any]],
        redis: Any,
        supabase: Any,
    ) -> Optional[AdapterResponse]:
        # Humans respond via the WebSocket endpoint, not here.
        return None

    async def should_volunteer(
        self,
        session_id: str,
        message_content: str,
        agent_config: Dict[str, Any],
    ) -> bool:
        # Humans are never auto-volunteered — they choose to respond themselves.
        return False
