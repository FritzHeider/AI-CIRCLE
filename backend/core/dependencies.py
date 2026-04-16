"""FastAPI dependency-injection helpers."""
from __future__ import annotations

from fastapi import Depends, Request

from services.redis_service import RedisService
from services.supabase_service import SupabaseService
from services.memory_service import MemoryService
from services.cost_tracker import CostTracker


# ── Low-level service dependencies ─────────────────────────────────────────

def get_redis(request: Request) -> RedisService:
    """Return the shared RedisService from app.state."""
    return request.app.state.redis


def get_supabase(request: Request) -> SupabaseService:
    """Return the shared SupabaseService from app.state."""
    return request.app.state.supabase


# ── Higher-level service dependencies ──────────────────────────────────────

def get_memory_service(
    redis: RedisService = Depends(get_redis),
    supabase: SupabaseService = Depends(get_supabase),
) -> MemoryService:
    return MemoryService(redis=redis, supabase=supabase)


def get_cost_tracker(
    redis: RedisService = Depends(get_redis),
    supabase: SupabaseService = Depends(get_supabase),
) -> CostTracker:
    return CostTracker(redis=redis, supabase=supabase)
