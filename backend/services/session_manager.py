"""SessionManager — tracks which WebSocket connections belong to which session."""
from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Dict, List, Optional, Set

from fastapi import WebSocket

from services.redis_service import RedisService

logger = logging.getLogger(__name__)


class ConnectionInfo:
    """Metadata about a single WebSocket connection."""

    __slots__ = ("websocket", "agent_id", "agent_name", "session_id")

    def __init__(
        self,
        websocket: WebSocket,
        agent_id: str,
        agent_name: str,
        session_id: str,
    ) -> None:
        self.websocket = websocket
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.session_id = session_id


class SessionManager:
    """
    Manages active WebSocket connections grouped by session_id.

    Connections are held in memory; Redis presence is the authoritative
    source for cross-instance presence (when running multiple replicas).
    """

    def __init__(self, redis: RedisService) -> None:
        self._redis = redis
        # session_id → set of ConnectionInfo
        self._sessions: Dict[str, Set[ConnectionInfo]] = defaultdict(set)
        self._lock = asyncio.Lock()

    # ── Connection management ─────────────────────────────────────────────

    async def connect(
        self,
        websocket: WebSocket,
        session_id: str,
        agent_id: str,
        agent_name: str,
    ) -> ConnectionInfo:
        await websocket.accept()
        conn = ConnectionInfo(
            websocket=websocket,
            agent_id=agent_id,
            agent_name=agent_name,
            session_id=session_id,
        )
        async with self._lock:
            self._sessions[session_id].add(conn)
        await self._redis.set_presence(session_id, agent_id, "online")
        logger.info(
            "Connected: session=%s agent=%s (%s)",
            session_id,
            agent_id,
            agent_name,
        )
        return conn

    async def disconnect(self, conn: ConnectionInfo) -> None:
        async with self._lock:
            self._sessions[conn.session_id].discard(conn)
            if not self._sessions[conn.session_id]:
                del self._sessions[conn.session_id]
        await self._redis.remove_presence(conn.session_id, conn.agent_id)
        logger.info(
            "Disconnected: session=%s agent=%s",
            conn.session_id,
            conn.agent_id,
        )

    # ── Broadcasting ──────────────────────────────────────────────────────

    async def broadcast(self, session_id: str, message: str) -> None:
        """Send *message* to every connection in *session_id*."""
        conns = list(self._sessions.get(session_id, set()))
        dead: list[ConnectionInfo] = []
        for conn in conns:
            try:
                await conn.websocket.send_text(message)
            except Exception:
                dead.append(conn)
        for conn in dead:
            await self.disconnect(conn)

    async def send_to_agent(
        self, session_id: str, agent_id: str, message: str
    ) -> bool:
        """Send *message* only to connections belonging to *agent_id*. Returns True if delivered."""
        delivered = False
        for conn in list(self._sessions.get(session_id, set())):
            if conn.agent_id == agent_id:
                try:
                    await conn.websocket.send_text(message)
                    delivered = True
                except Exception:
                    await self.disconnect(conn)
        return delivered

    # ── Queries ───────────────────────────────────────────────────────────

    def get_connections(self, session_id: str) -> List[ConnectionInfo]:
        return list(self._sessions.get(session_id, set()))

    def agent_ids_in_session(self, session_id: str) -> Set[str]:
        return {c.agent_id for c in self._sessions.get(session_id, set())}

    def session_count(self) -> int:
        return len(self._sessions)

    def connection_count(self, session_id: Optional[str] = None) -> int:
        if session_id:
            return len(self._sessions.get(session_id, set()))
        return sum(len(v) for v in self._sessions.values())
