"""Supabase service — all database CRUD operations."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from supabase import create_client, Client

logger = logging.getLogger(__name__)


class SupabaseService:
    """Thin async-friendly wrapper around the Supabase Python client."""

    def __init__(self, url: str, key: str) -> None:
        if not url or not key:
            logger.warning(
                "SupabaseService created without URL/key — DB operations will fail"
            )
            self._client: Optional[Client] = None
        else:
            self._client = create_client(url, key)

    @property
    def client(self) -> Client:
        if self._client is None:
            raise RuntimeError("Supabase client not initialised — set SUPABASE_URL and SUPABASE_SERVICE_KEY")
        return self._client

    # ── Sessions ──────────────────────────────────────────────────────────

    async def create_session(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        result = self.client.table("sessions").insert(session_data).execute()
        return result.data[0]

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        result = (
            self.client.table("sessions")
            .select("*")
            .eq("id", session_id)
            .maybe_single()
            .execute()
        )
        return result.data

    async def list_sessions(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        result = (
            self.client.table("sessions")
            .select("*")
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        return result.data or []

    async def update_session(self, session_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        result = (
            self.client.table("sessions")
            .update(updates)
            .eq("id", session_id)
            .execute()
        )
        return result.data[0]

    async def delete_session(self, session_id: str) -> None:
        self.client.table("sessions").delete().eq("id", session_id).execute()

    # ── Messages ──────────────────────────────────────────────────────────

    async def save_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        result = self.client.table("messages").insert(message_data).execute()
        return result.data[0]

    async def get_messages(
        self,
        session_id: str,
        limit: int = 100,
        before_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        query = (
            self.client.table("messages")
            .select("*")
            .eq("session_id", session_id)
            .order("created_at", desc=True)
            .limit(limit)
        )
        if before_id:
            # Fetch the timestamp of the reference message first
            ref = (
                self.client.table("messages")
                .select("created_at")
                .eq("id", before_id)
                .maybe_single()
                .execute()
            )
            if ref.data:
                query = query.lt("created_at", ref.data["created_at"])
        result = query.execute()
        messages = result.data or []
        messages.reverse()  # Return chronological order
        return messages

    # ── Agent configs ─────────────────────────────────────────────────────

    async def list_agents(self) -> List[Dict[str, Any]]:
        result = (
            self.client.table("agent_configs")
            .select("*")
            .eq("enabled", True)
            .order("priority")
            .execute()
        )
        return result.data or []

    async def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        result = (
            self.client.table("agent_configs")
            .select("*")
            .eq("id", agent_id)
            .maybe_single()
            .execute()
        )
        return result.data

    async def create_agent(self, agent_data: Dict[str, Any]) -> Dict[str, Any]:
        result = self.client.table("agent_configs").insert(agent_data).execute()
        return result.data[0]

    async def update_agent(self, agent_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        result = (
            self.client.table("agent_configs")
            .update(updates)
            .eq("id", agent_id)
            .execute()
        )
        return result.data[0]

    async def delete_agent(self, agent_id: str) -> None:
        self.client.table("agent_configs").delete().eq("id", agent_id).execute()

    # ── Shared memory ─────────────────────────────────────────────────────

    async def get_shared_memory(self, session_id: str) -> List[Dict[str, Any]]:
        result = (
            self.client.table("shared_memory")
            .select("*")
            .eq("session_id", session_id)
            .order("created_at")
            .execute()
        )
        return result.data or []

    async def upsert_shared_memory(
        self, session_id: str, key: str, value: Any, agent_id: Optional[str] = None
    ) -> Dict[str, Any]:
        data = {
            "session_id": session_id,
            "key": key,
            "value": value,
            "updated_by": agent_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        result = (
            self.client.table("shared_memory")
            .upsert(data, on_conflict="session_id,key")
            .execute()
        )
        return result.data[0]

    async def delete_shared_memory(self, session_id: str, key: str) -> None:
        (
            self.client.table("shared_memory")
            .delete()
            .eq("session_id", session_id)
            .eq("key", key)
            .execute()
        )

    # ── Agent private memory ──────────────────────────────────────────────

    async def get_agent_memory(self, agent_id: str, session_id: str) -> List[Dict[str, Any]]:
        result = (
            self.client.table("agent_memory")
            .select("*")
            .eq("agent_id", agent_id)
            .eq("session_id", session_id)
            .order("created_at")
            .execute()
        )
        return result.data or []

    async def upsert_agent_memory(
        self, agent_id: str, session_id: str, key: str, value: Any
    ) -> Dict[str, Any]:
        data = {
            "agent_id": agent_id,
            "session_id": session_id,
            "key": key,
            "value": value,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        result = (
            self.client.table("agent_memory")
            .upsert(data, on_conflict="agent_id,session_id,key")
            .execute()
        )
        return result.data[0]

    # ── Cost events ───────────────────────────────────────────────────────

    async def record_cost_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        result = self.client.table("cost_events").insert(event_data).execute()
        return result.data[0]

    async def get_session_cost_summary(
        self, session_id: str
    ) -> List[Dict[str, Any]]:
        """Return per-agent cost totals for a session."""
        result = (
            self.client.table("cost_events")
            .select("agent_id, tokens_in, tokens_out, cost_usd")
            .eq("session_id", session_id)
            .execute()
        )
        events = result.data or []

        # Aggregate in Python (Supabase free tier lacks groupby RPC)
        totals: Dict[str, Dict[str, float]] = {}
        for ev in events:
            aid = ev["agent_id"]
            if aid not in totals:
                totals[aid] = {"tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0}
            totals[aid]["tokens_in"] += ev.get("tokens_in", 0)
            totals[aid]["tokens_out"] += ev.get("tokens_out", 0)
            totals[aid]["cost_usd"] += ev.get("cost_usd", 0.0)

        return [{"agent_id": k, **v} for k, v in totals.items()]

    # ── Workflows ─────────────────────────────────────────────────────────

    async def list_workflows(self) -> List[Dict[str, Any]]:
        result = (
            self.client.table("workflows")
            .select("*")
            .order("created_at", desc=True)
            .execute()
        )
        return result.data or []

    async def get_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        result = (
            self.client.table("workflows")
            .select("*")
            .eq("id", workflow_id)
            .maybe_single()
            .execute()
        )
        return result.data

    async def create_workflow(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        result = self.client.table("workflows").insert(workflow_data).execute()
        return result.data[0]

    async def update_workflow(
        self, workflow_id: str, updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        result = (
            self.client.table("workflows")
            .update(updates)
            .eq("id", workflow_id)
            .execute()
        )
        return result.data[0]

    async def delete_workflow(self, workflow_id: str) -> None:
        self.client.table("workflows").delete().eq("id", workflow_id).execute()
