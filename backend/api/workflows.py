"""Workflows REST API — CRUD + topological execution order."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core.dependencies import get_supabase
from services.supabase_service import SupabaseService

router = APIRouter()


class WorkflowNode(BaseModel):
    id: str
    type: str                       # "agent" | "trigger" | "condition" | "output"
    agent_id: Optional[str] = None
    label: str = ""
    config: Dict[str, Any] = {}
    position: Dict[str, float] = {}


class WorkflowEdge(BaseModel):
    id: str
    source: str
    target: str
    label: str = ""


class WorkflowCreate(BaseModel):
    name: str
    description: str = ""
    nodes: List[WorkflowNode] = []
    edges: List[WorkflowEdge] = []
    trigger: str = "manual"         # "manual" | "scheduled" | "event"
    trigger_config: Dict[str, Any] = {}


class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    nodes: Optional[List[WorkflowNode]] = None
    edges: Optional[List[WorkflowEdge]] = None
    trigger: Optional[str] = None
    trigger_config: Optional[Dict[str, Any]] = None


def _topological_sort(
    nodes: List[Dict], edges: List[Dict]
) -> List[str]:
    """
    Return node IDs in topological (dependency) order using Kahn's algorithm.
    Returns original order if the graph has cycles.
    """
    in_degree: Dict[str, int] = {n["id"]: 0 for n in nodes}
    adjacency: Dict[str, List[str]] = {n["id"]: [] for n in nodes}

    for edge in edges:
        src, tgt = edge["source"], edge["target"]
        if src in adjacency:
            adjacency[src].append(tgt)
        if tgt in in_degree:
            in_degree[tgt] += 1

    queue = [nid for nid, deg in in_degree.items() if deg == 0]
    order: List[str] = []

    while queue:
        nid = queue.pop(0)
        order.append(nid)
        for neighbor in adjacency.get(nid, []):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    # Fall back to original order if cycle detected
    if len(order) != len(nodes):
        return [n["id"] for n in nodes]

    return order


@router.get("")
async def list_workflows(db: SupabaseService = Depends(get_supabase)):
    return await db.list_workflows()


@router.post("", status_code=201)
async def create_workflow(
    body: WorkflowCreate,
    db: SupabaseService = Depends(get_supabase),
):
    data = body.model_dump()
    data["id"] = str(uuid.uuid4())
    data["created_at"] = datetime.now(timezone.utc).isoformat()
    return await db.create_workflow(data)


@router.get("/{workflow_id}")
async def get_workflow(
    workflow_id: str,
    db: SupabaseService = Depends(get_supabase),
):
    row = await db.get_workflow(workflow_id)
    if not row:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return row


@router.patch("/{workflow_id}")
async def update_workflow(
    workflow_id: str,
    body: WorkflowUpdate,
    db: SupabaseService = Depends(get_supabase),
):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    return await db.update_workflow(workflow_id, updates)


@router.delete("/{workflow_id}", status_code=204)
async def delete_workflow(
    workflow_id: str,
    db: SupabaseService = Depends(get_supabase),
):
    await db.delete_workflow(workflow_id)


@router.get("/{workflow_id}/execution-order")
async def get_execution_order(
    workflow_id: str,
    db: SupabaseService = Depends(get_supabase),
):
    """Return node IDs sorted in topological execution order."""
    row = await db.get_workflow(workflow_id)
    if not row:
        raise HTTPException(status_code=404, detail="Workflow not found")
    order = _topological_sort(row.get("nodes", []), row.get("edges", []))
    return {"workflow_id": workflow_id, "execution_order": order}
