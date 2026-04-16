"""Memory REST API — shared and private memory CRUD."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from core.dependencies import get_memory_service
from services.memory_service import MemoryService

router = APIRouter()


class MemorySetRequest(BaseModel):
    key: str
    value: Any
    agent_id: str | None = None


class PrivateMemorySetRequest(BaseModel):
    key: str
    value: Any


# ── Shared memory ──────────────────────────────────────────────────────────

@router.get("/shared/{session_id}")
async def get_shared_memory(
    session_id: str,
    mem: MemoryService = Depends(get_memory_service),
):
    return await mem.get_shared_memory(session_id)


@router.put("/shared/{session_id}")
async def set_shared_memory(
    session_id: str,
    body: MemorySetRequest,
    mem: MemoryService = Depends(get_memory_service),
):
    await mem.set_shared_memory(
        session_id=session_id,
        key=body.key,
        value=body.value,
        agent_id=body.agent_id,
    )
    return {"ok": True}


@router.delete("/shared/{session_id}/{key}")
async def delete_shared_memory(
    session_id: str,
    key: str,
    mem: MemoryService = Depends(get_memory_service),
):
    await mem.delete_shared_memory(session_id=session_id, key=key)
    return {"ok": True}


# ── Private memory ─────────────────────────────────────────────────────────

@router.get("/private/{agent_id}/{session_id}")
async def get_private_memory(
    agent_id: str,
    session_id: str,
    mem: MemoryService = Depends(get_memory_service),
):
    return await mem.get_private_memory(agent_id, session_id)


@router.put("/private/{agent_id}/{session_id}")
async def set_private_memory(
    agent_id: str,
    session_id: str,
    body: PrivateMemorySetRequest,
    mem: MemoryService = Depends(get_memory_service),
):
    await mem.set_private_memory(
        agent_id=agent_id,
        session_id=session_id,
        key=body.key,
        value=body.value,
    )
    return {"ok": True}
