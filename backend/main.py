"""AgentHub FastAPI application entry-point."""
from __future__ import annotations

import logging
import uuid
from typing import Optional

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from core.config import get_settings
from core.events import lifespan
from core.startup_checks import run_startup_checks
from services.session_manager import SessionManager
from services.cost_tracker import CostTracker
from websocket.hub import ConnectionHub
from websocket.handlers import MessageHandler
from websocket.protocol import WSMessage, MessageRole

# ── Logging ────────────────────────────────────────────────────────────────
settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ── Startup checks ─────────────────────────────────────────────────────────
run_startup_checks()

# ── App ────────────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Multi-agent group chat orchestrator",
    lifespan=lifespan,
)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Singletons attached after startup ──────────────────────────────────────
# These are initialised in lifespan and used below; declared here for clarity.
_session_manager: Optional[SessionManager] = None
_hub: Optional[ConnectionHub] = None
_message_handler: Optional[MessageHandler] = None


@app.on_event("startup")
async def _init_singletons() -> None:
    global _session_manager, _hub, _message_handler
    redis = app.state.redis
    supabase = app.state.supabase
    cost_tracker = CostTracker(redis=redis, supabase=supabase)

    _session_manager = SessionManager(redis=redis)
    _hub = ConnectionHub(redis=redis, session_manager=_session_manager)
    _message_handler = MessageHandler(
        redis=redis,
        supabase=supabase,
        hub=_hub,
        cost_tracker=cost_tracker,
    )
    app.state.session_manager = _session_manager
    app.state.hub = _hub
    app.state.cost_tracker = cost_tracker


# ── REST routers ──────────────────────────────────────────────────────────
from api import sessions, agents, messages, memory, costs, workflows  # noqa: E402

app.include_router(sessions.router, prefix="/api/sessions", tags=["sessions"])
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
app.include_router(messages.router, prefix="/api/messages", tags=["messages"])
app.include_router(memory.router, prefix="/api/memory", tags=["memory"])
app.include_router(costs.router, prefix="/api/costs", tags=["costs"])
app.include_router(workflows.router, prefix="/api/workflows", tags=["workflows"])


# ── Health check ──────────────────────────────────────────────────────────
@app.get("/health", tags=["health"])
async def health() -> dict:
    return {"status": "ok", "version": settings.app_version}


# ── WebSocket endpoint ────────────────────────────────────────────────────
@app.websocket("/ws/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    agent_id: Optional[str] = Query(default=None),
    agent_name: Optional[str] = Query(default="Unknown"),
) -> None:
    # Allow anonymous connections with a generated ID
    if not agent_id:
        agent_id = f"anon-{uuid.uuid4().hex[:8]}"

    conn = await _session_manager.connect(
        websocket=websocket,
        session_id=session_id,
        agent_id=agent_id,
        agent_name=agent_name,
    )

    # Ensure the hub is listening for this session
    await _hub.ensure_listener(session_id)

    # Announce join
    await _hub.publish(
        WSMessage.presence(session_id, agent_id, agent_name, "online")
    )

    # Send recent history on connect
    try:
        supabase = app.state.supabase
        history = await supabase.get_messages(session_id, limit=50)
        if history:
            from websocket.protocol import MessageType
            history_msg = WSMessage(
                type=MessageType.HISTORY,
                session_id=session_id,
                sender_id="system",
                sender_name="System",
                content="",
                metadata={"messages": history},
            )
            await websocket.send_text(history_msg.to_json())
    except Exception as exc:
        logger.warning("Failed to send history to %s: %s", agent_id, exc)

    try:
        while True:
            raw = await websocket.receive_text()
            await _message_handler.handle(conn, raw)
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected: session=%s agent=%s", session_id, agent_id)
    except Exception as exc:
        logger.exception("WebSocket error: session=%s agent=%s: %s", session_id, agent_id, exc)
    finally:
        await _session_manager.disconnect(conn)
        await _hub.publish(
            WSMessage.presence(session_id, agent_id, agent_name, "offline")
        )
        # Stop the hub listener if no more connections in the session
        if _session_manager.connection_count(session_id) == 0:
            await _hub.stop_listener(session_id)


# ── Dev entry point ────────────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
