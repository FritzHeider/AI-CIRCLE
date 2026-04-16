"""Agents REST API."""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core.dependencies import get_supabase
from services.supabase_service import SupabaseService

router = APIRouter()


class AgentCreate(BaseModel):
    name: str
    adapter_type: str
    description: str = ""
    capabilities: List[str] = []
    avatar_color: str = "#6366f1"
    priority: int = 50
    enabled: bool = True
    system_prompt_override: Optional[str] = None
    model_override: Optional[str] = None
    hourly_cap_usd: Optional[float] = None
    extra_config: Dict[str, Any] = {}


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    capabilities: Optional[List[str]] = None
    avatar_color: Optional[str] = None
    priority: Optional[int] = None
    enabled: Optional[bool] = None
    system_prompt_override: Optional[str] = None
    model_override: Optional[str] = None
    hourly_cap_usd: Optional[float] = None
    extra_config: Optional[Dict[str, Any]] = None


@router.get("")
async def list_agents(db: SupabaseService = Depends(get_supabase)):
    return await db.list_agents()


@router.post("", status_code=201)
async def create_agent(
    body: AgentCreate,
    db: SupabaseService = Depends(get_supabase),
):
    data = body.model_dump()
    data["id"] = str(uuid.uuid4())
    return await db.create_agent(data)


@router.get("/{agent_id}")
async def get_agent(
    agent_id: str,
    db: SupabaseService = Depends(get_supabase),
):
    row = await db.get_agent(agent_id)
    if not row:
        raise HTTPException(status_code=404, detail="Agent not found")
    return row


@router.patch("/{agent_id}")
async def update_agent(
    agent_id: str,
    body: AgentUpdate,
    db: SupabaseService = Depends(get_supabase),
):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    return await db.update_agent(agent_id, updates)


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(
    agent_id: str,
    db: SupabaseService = Depends(get_supabase),
):
    await db.delete_agent(agent_id)
