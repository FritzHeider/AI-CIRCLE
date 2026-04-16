"""FastAPI lifespan events — startup and shutdown hooks."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from core.config import get_settings
from services.redis_service import RedisService
from services.supabase_service import SupabaseService

logger = logging.getLogger(__name__)
settings = get_settings()

# Module-level singletons initialised during startup
redis_service: RedisService | None = None
supabase_service: SupabaseService | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifespan: connect services on startup, close on shutdown."""
    global redis_service, supabase_service

    logger.info("AgentHub starting up …")

    # ── Initialise services ────────────────────────────────────────────
    redis_service = RedisService(url=settings.redis_url)
    await redis_service.connect()
    logger.info("Redis connected: %s", settings.redis_url)

    supabase_service = SupabaseService(
        url=settings.supabase_url,
        key=settings.supabase_service_key,
    )
    logger.info("Supabase client ready")

    # Store on app.state so dependencies can reach them
    app.state.redis = redis_service
    app.state.supabase = supabase_service

    logger.info("AgentHub ready ✓")
    yield

    # ── Shutdown ───────────────────────────────────────────────────────
    logger.info("AgentHub shutting down …")
    await redis_service.disconnect()
    logger.info("Redis disconnected")
    logger.info("Shutdown complete")
