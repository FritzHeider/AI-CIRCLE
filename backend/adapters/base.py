"""AgentAdapter abstract base class."""
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from websocket.protocol import ArtifactInfo


@dataclass
class AdapterResponse:
    """Unified response returned by every adapter."""
    content: str
    model: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    artifacts: List[ArtifactInfo] = field(default_factory=list)
    mentions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class AgentAdapter(ABC):
    """
    Abstract base class for all LLM / tool adapters.

    Subclasses must implement:
      - `adapter_type` class attribute
      - `respond()` method

    Optional overrides:
      - `should_volunteer()` — return True if agent wants to respond unprompted
      - `capabilities` class attribute — list of capability tags
    """

    adapter_type: str = ""
    capabilities: List[str] = []

    # ── Required interface ────────────────────────────────────────────────

    @abstractmethod
    async def respond(
        self,
        session_id: str,
        agent_config: Dict[str, Any],
        user_message: str,
        history: List[Dict[str, Any]],
        redis: Any,
        supabase: Any,
    ) -> Optional[AdapterResponse]:
        """
        Generate a response.

        Parameters
        ----------
        session_id    : Active session id
        agent_config  : Row from agent_configs table (includes name, model_override, etc.)
        user_message  : The latest human message text
        history       : Recent messages [{"role": ..., "content": ...}, ...]
        redis         : RedisService instance
        supabase      : SupabaseService instance

        Returns
        -------
        AdapterResponse or None (if the adapter declines to respond)
        """
        ...

    # ── Optional volunteer hook ───────────────────────────────────────────

    async def should_volunteer(
        self,
        session_id: str,
        message_content: str,
        agent_config: Dict[str, Any],
    ) -> bool:
        """Return True if this adapter *wants* to respond to the given message."""
        return False

    # ── Helpers available to all subclasses ──────────────────────────────

    def _build_system_message(
        self,
        agent_config: Dict[str, Any],
        shared_context: Dict[str, Any],
        private_context: Dict[str, Any],
    ) -> str:
        """
        Compose the system prompt string for an agent.

        Merges:
          1. Base system prompt (from agent_config or default)
          2. Shared project context from memory
          3. Private per-agent notes from memory
        """
        base = (
            agent_config.get("system_prompt_override")
            or self._default_system_prompt(agent_config)
        )

        parts = [base]

        if shared_context:
            ctx_lines = "\n".join(
                f"  {k}: {v}" for k, v in shared_context.items()
            )
            parts.append(f"\n\n## Shared Project Context\n{ctx_lines}")

        if private_context:
            priv_lines = "\n".join(
                f"  {k}: {v}" for k, v in private_context.items()
            )
            parts.append(f"\n\n## Your Private Notes\n{priv_lines}")

        return "\n".join(parts)

    def _default_system_prompt(self, agent_config: Dict[str, Any]) -> str:
        name = agent_config.get("name", "Agent")
        desc = agent_config.get("description", "")
        caps = ", ".join(agent_config.get("capabilities", []))
        return (
            f"You are {name}, an AI agent in a multi-agent group chat.\n"
            f"{desc}\n"
            f"Your capabilities: {caps or 'general assistant'}.\n"
            "Respond concisely and collaboratively. "
            "When referencing another agent use @AgentName."
        )

    def _format_conversation_history(
        self,
        history: List[Dict[str, Any]],
        include_system: bool = False,
    ) -> List[Dict[str, str]]:
        """
        Convert raw DB message rows to a simple role/content list.

        Filters out system messages unless include_system=True.
        """
        result = []
        for msg in history:
            role = msg.get("role", "user")
            if role == "system" and not include_system:
                continue
            result.append({"role": role, "content": msg.get("content", "")})
        return result

    def _extract_mentions(self, text: str) -> List[str]:
        """Return list of @mention strings found in *text*."""
        return re.findall(r"@[\w.-]+", text)

    def _extract_code_artifacts(self, text: str) -> List[ArtifactInfo]:
        """Extract ```lang ... ``` code blocks from a response."""
        pattern = r"```(\w+)?\n(.*?)```"
        artifacts = []
        for match in re.finditer(pattern, text, re.DOTALL):
            lang = match.group(1) or "text"
            code = match.group(2).strip()
            if code:
                artifacts.append(
                    ArtifactInfo(type="code", language=lang, content=code)
                )
        return artifacts
