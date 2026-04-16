"""OpenAIAdapter — OpenAI GPT / Codex via the official Python SDK."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from adapters.base import AgentAdapter, AdapterResponse
from adapters.registry import register_adapter

logger = logging.getLogger(__name__)

# Per-model pricing (USD per 1M tokens)
OPENAI_PRICING: Dict[str, Dict[str, float]] = {
    "gpt-4o":         {"in": 5.0,   "out": 15.0},
    "gpt-4o-mini":    {"in": 0.15,  "out": 0.60},
    "gpt-4-turbo":    {"in": 10.0,  "out": 30.0},
    "gpt-3.5-turbo":  {"in": 0.50,  "out": 1.50},
    "o1-preview":     {"in": 15.0,  "out": 60.0},
    "o1-mini":        {"in": 3.0,   "out": 12.0},
    "default":        {"in": 5.0,   "out": 15.0},
}

DEFAULT_MODEL = "gpt-4o"


def _calc_cost(model: str, tokens_in: int, tokens_out: int) -> float:
    pricing = OPENAI_PRICING.get(model, OPENAI_PRICING["default"])
    return (tokens_in * pricing["in"] + tokens_out * pricing["out"]) / 1_000_000


def _count_tokens_approx(messages: List[Dict[str, str]], model: str) -> int:
    """Rough token count using tiktoken if available, else character estimate."""
    try:
        import tiktoken
        enc = tiktoken.encoding_for_model(model)
    except Exception:
        # Fallback: ~4 chars per token
        total_chars = sum(len(m.get("content", "")) for m in messages)
        return total_chars // 4

    total = 0
    for msg in messages:
        total += 4  # per-message overhead
        for key, val in msg.items():
            total += len(enc.encode(str(val)))
    total += 2  # reply priming
    return total


@register_adapter("openai")
class OpenAIAdapter(AgentAdapter):
    """Adapter for OpenAI GPT models."""

    adapter_type = "openai"
    capabilities = ["code", "debug", "sql", "general", "function_calling"]

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

        api_key = settings.openai_api_key
        if not api_key:
            logger.warning("OPENAI_API_KEY not configured — OpenAIAdapter skipping")
            return None

        try:
            from openai import AsyncOpenAI
        except ImportError:
            logger.error("openai package not installed")
            return None

        model = agent_config.get("model_override") or DEFAULT_MODEL

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

        messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]
        messages.extend(self._format_conversation_history(history))
        messages.append({"role": "user", "content": user_message})

        client = AsyncOpenAI(api_key=api_key)
        max_tokens = agent_config.get("extra_config", {}).get("max_tokens", 2048)

        try:
            completion = await client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=agent_config.get("extra_config", {}).get("temperature", 0.7),
            )
        except Exception as exc:
            logger.exception("OpenAI API error: %s", exc)
            return AdapterResponse(content=f"[OpenAI error: {exc}]", model=model)

        choice = completion.choices[0]
        text = choice.message.content or ""

        tokens_in = completion.usage.prompt_tokens
        tokens_out = completion.usage.completion_tokens
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
        """Volunteer for coding and debugging tasks."""
        volunteer_keywords = {
            "code", "function", "class", "bug", "fix", "debug",
            "implement", "write", "sql", "query", "script", "refactor",
        }
        lower = message_content.lower()
        return any(kw in lower for kw in volunteer_keywords)
