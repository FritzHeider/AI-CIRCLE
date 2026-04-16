"""GeminiAdapter — Google Gemini via the google-generativeai SDK."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from adapters.base import AgentAdapter, AdapterResponse
from adapters.registry import register_adapter

logger = logging.getLogger(__name__)

GEMINI_PRICING: Dict[str, Dict[str, float]] = {
    "gemini-1.5-pro":   {"in": 3.50,  "out": 10.50},
    "gemini-1.5-flash": {"in": 0.075, "out": 0.30},
    "gemini-pro":       {"in": 0.50,  "out": 1.50},
    "default":          {"in": 0.50,  "out": 1.50},
}

DEFAULT_MODEL = "gemini-1.5-flash"


def _calc_cost(model: str, tokens_in: int, tokens_out: int) -> float:
    pricing = GEMINI_PRICING.get(model, GEMINI_PRICING["default"])
    return (tokens_in * pricing["in"] + tokens_out * pricing["out"]) / 1_000_000


def _to_gemini_history(messages: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """
    Convert OpenAI-style role/content messages to Gemini's
    {role: 'user'|'model', parts: [{text: ...}]} format.
    """
    gemini_msgs = []
    for msg in messages:
        role = "model" if msg["role"] == "assistant" else "user"
        gemini_msgs.append({"role": role, "parts": [{"text": msg["content"]}]})
    return gemini_msgs


@register_adapter("gemini")
class GeminiAdapter(AgentAdapter):
    """Adapter for Google Gemini models."""

    adapter_type = "gemini"
    capabilities = ["multimodal", "long_context", "summarization", "translation", "general"]

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

        api_key = settings.google_api_key
        if not api_key:
            logger.warning("GOOGLE_API_KEY not configured — GeminiAdapter skipping")
            return None

        try:
            import google.generativeai as genai
        except ImportError:
            logger.error("google-generativeai package not installed")
            return None

        genai.configure(api_key=api_key)
        model_name = agent_config.get("model_override") or DEFAULT_MODEL

        # Load memory context
        try:
            from services.memory_service import MemoryService
            mem = MemoryService(redis=redis, supabase=supabase)
            shared_ctx, private_ctx = await mem.build_agent_context(
                agent_config["id"], session_id
            )
        except Exception:
            shared_ctx, private_ctx = {}, {}

        system_instruction = self._build_system_message(agent_config, shared_ctx, private_ctx)

        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system_instruction,
        )

        formatted = self._format_conversation_history(history)
        gemini_history = _to_gemini_history(formatted)

        # Start a chat session with the existing history
        chat = model.start_chat(history=gemini_history)

        try:
            response = await chat.send_message_async(user_message)
        except Exception as exc:
            logger.exception("Gemini API error: %s", exc)
            return AdapterResponse(content=f"[Gemini error: {exc}]", model=model_name)

        text = response.text or ""

        # Gemini token counting (approximate via count_tokens)
        try:
            count_resp = await model.count_tokens_async(
                [{"role": "user", "parts": [{"text": user_message}]}]
            )
            tokens_in = count_resp.total_tokens
            out_count = await model.count_tokens_async(
                [{"role": "model", "parts": [{"text": text}]}]
            )
            tokens_out = out_count.total_tokens
        except Exception:
            tokens_in = len(user_message) // 4
            tokens_out = len(text) // 4

        cost = _calc_cost(model_name, tokens_in, tokens_out)
        artifacts = self._extract_code_artifacts(text)
        mentions = self._extract_mentions(text)

        return AdapterResponse(
            content=text,
            model=model_name,
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
        volunteer_keywords = {
            "summarize", "translate", "long", "document",
            "multimodal", "image", "video", "describe",
        }
        lower = message_content.lower()
        return any(kw in lower for kw in volunteer_keywords)
