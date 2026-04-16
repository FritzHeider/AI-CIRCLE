"""Sessions REST API."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core.dependencies import get_supabase
from services.supabase_service import SupabaseService

router = APIRouter()


class SessionCreate(BaseModel):
    name: str
    description: str = ""
    budget_usd: float = 5.0


class SessionUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    budget_usd: float | None = None


@router.get("")
async def list_sessions(
    limit: int = 50,
    offset: int = 0,
    db: SupabaseService = Depends(get_supabase),
):
    return await db.list_sessions(limit=limit, offset=offset)


@router.post("", status_code=201)
async def create_session(
    body: SessionCreate,
    db: SupabaseService = Depends(get_supabase),
):
    data = {
        "id": str(uuid.uuid4()),
        "name": body.name,
        "description": body.description,
        "budget_usd": body.budget_usd,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    return await db.create_session(data)


@router.get("/{session_id}")
async def get_session(
    session_id: str,
    db: SupabaseService = Depends(get_supabase),
):
    row = await db.get_session(session_id)
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    return row


@router.patch("/{session_id}")
async def update_session(
    session_id: str,
    body: SessionUpdate,
    db: SupabaseService = Depends(get_supabase),
):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    return await db.update_session(session_id, updates)


@router.delete("/{session_id}", status_code=204)
async def delete_session(
    session_id: str,
    db: SupabaseService = Depends(get_supabase),
):
    await db.delete_session(session_id)
