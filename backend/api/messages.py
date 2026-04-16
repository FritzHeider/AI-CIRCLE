"""Messages REST API — history retrieval."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query

from core.dependencies import get_supabase
from services.supabase_service import SupabaseService

router = APIRouter()


@router.get("/{session_id}")
async def get_messages(
    session_id: str,
    limit: int = Query(default=50, le=200),
    before_id: Optional[str] = Query(default=None),
    db: SupabaseService = Depends(get_supabase),
):
    """Return paginated message history for a session."""
    return await db.get_messages(
        session_id=session_id,
        limit=limit,
        before_id=before_id,
    )
