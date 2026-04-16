"""ClaudeAdapter — Anthropic Claude via the official Python SDK."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from adapters.base import AgentAdapter, AdapterResponse
from adapters.registry import register_adapter
from websocket.protocol import ArtifactInfo

logger = logging.getLogger(__name__)

# Per-model pricing (USD per 1M tokens)
CLAUDE_PRICING: Dict[str, Dict[str, float]] = {
    "claude-opus-4-6":    {"in": 15.0,  "out": 75.0},
    "claude-sonnet-4-6":  {"in": 3.0,   "out": 15.0},
    "claude-haiku-4-5-20251001": {"in": 0.25, "out": 1.25},
    # fallback
    "default":            {"in": 3.0,   "out": 15.0},
}

DEFAULT_MODEL = "claude-sonnet-4-6"


def _calc_cost(model: str, tokens_in: int, tokens_out: int) -> float:
    pricing = CLAUDE_PRICING.get(model, CLAUDE_PRICING["default"])
    return (tokens_in * pricing["in"] + tokens_out * pricing["out"]) / 1_000_000


@register_adapter("claude")
class ClaudeAdapter(AgentAdapter):
    """Adapter for Anthropic Claude models."""

    adapter_type = "claude"
    capabilities = ["reasoning", "planning", "code", "writing", "analysis"]

    async def respond(
        self,
        session_id: str,
        agent_config: Dict[str, Any],
        user_message: str,
        history: List[Dict[str, Any]],
        redis: Any,
        supabase: Any,
    ) -> Optional[AdapterResponse]:
        from core.config import get_settings
        settings = get_settings()

        api_key = settings.anthropic_api_key
        if not api_key:
            logger.warning("ANTHROPIC_API_KEY not configured — ClaudeAdapter skipping")
            return None

        try:
            import anthropic
        except ImportError:
            logger.error("anthropic package not installed")
            return None

        model = agent_config.get("model_override") or DEFAULT_MODEL

        # Build conversation
        formatted = self._format_conversation_history(history)
        # Append the latest user message
        formatted.append({"role": "user", "content": user_message})

        # Load memory context
        try:
            from services.memory_service import MemoryService
            mem = MemoryService(redis=redis, supabase=supabase)
            shared_ctx, private_ctx = await mem.build_agent_context(
                agent_config["id"], session_id
            )
        except Exception:
            shared_ctx, private_ctx = {}, {}

        system_prompt = self._build_system_message(agent_config, shared_ctx, private_ctx)

        client = anthropic.AsyncAnthropic(api_key=api_key)

        try:
            response = await client.messages.create(
                model=model,
                max_tokens=agent_config.get("extra_config", {}).get("max_tokens", 2048),
                system=system_prompt,
                messages=formatted,
            )
        except Exception as exc:
            logger.exception("Claude API error: %s", exc)
            return AdapterResponse(
                content=f"[Claude error: {exc}]",
                model=model,
            )

        content_block = response.content[0]
        text = content_block.text if hasattr(content_block, "text") else str(content_block)

        tokens_in = response.usage.input_tokens
        tokens_out = response.usage.output_tokens
        cost = _calc_cost(model, tokens_in, tokens_out)

        artifacts = self._extract_code_artifacts(text)
        mentions = self._extract_mentions(text)

        return AdapterResponse(
            content=text,
            model=model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=cost,
            artifacts=artifacts,
            mentions=mentions,
        )

    async def should_volunteer(
        self,
        session_id: str,
        message_content: str,
        agent_config: Dict[str, Any],
    ) -> bool:
        """Volunteer for reasoning, planning, and complex analysis tasks."""
        volunteer_keywords = {
            "plan", "design", "architect", "analyse", "analyze",
            "reason", "strategy", "review", "compare", "explain",
        }
        lower = message_content.lower()
        return any(kw in lower for kw in volunteer_keywords)
