"""Pre-flight checks run at startup to surface mis-configuration early."""
from __future__ import annotations

import logging
import sys

from core.config import get_settings

logger = logging.getLogger(__name__)


def run_startup_checks() -> None:
    """Validate critical environment variables; exit process on hard failure."""
    settings = get_settings()
    errors: list[str] = []
    warnings: list[str] = []

    # Hard requirements
    if not settings.supabase_url:
        errors.append("SUPABASE_URL is not set")
    if not settings.supabase_service_key:
        errors.append("SUPABASE_SERVICE_KEY is not set")
    if not settings.redis_url:
        errors.append("REDIS_URL is not set")

    # Soft warnings (at least one LLM key should be present for non-human agents)
    llm_keys = {
        "ANTHROPIC_API_KEY": settings.anthropic_api_key,
        "OPENAI_API_KEY": settings.openai_api_key,
        "GOOGLE_API_KEY": settings.google_api_key,
        "FALAI_API_KEY": settings.falai_api_key,
    }
    configured = [k for k, v in llm_keys.items() if v]
    if not configured:
        warnings.append(
            "No LLM API keys configured — only the HumanAgent will be functional"
        )
    else:
        logger.info("LLM keys configured: %s", ", ".join(configured))

    # Report
    for w in warnings:
        logger.warning("Startup warning: %s", w)

    if errors:
        for e in errors:
            logger.critical("Startup error: %s", e)
        sys.exit(1)

    logger.info("Startup checks passed ✓")
