"""WebSocket message handlers — parse inbound frames and route to agents."""
from __future__ import annotations

import json
import logging
from typing import Any, Dict

from websocket.protocol import (
    MessageType,
    MessageRole,
    WSMessage,
)
from services.redis_service import RedisService
from services.supabase_service import SupabaseService
from services.session_manager import ConnectionInfo
from services.cost_tracker import CostTracker
from websocket.hub import ConnectionHub

logger = logging.getLogger(__name__)


class MessageHandler:
    """
    Handles inbound WebSocket frames from a single connection.

    Responsibilities:
      - Parse and validate inbound JSON
      - Route CHAT messages through the HybridRouter
      - Dispatch to appropriate agent adapters
      - Persist messages to Supabase
      - Fan-out replies via ConnectionHub
    """

    def __init__(
        self,
        redis: RedisService,
        supabase: SupabaseService,
        hub: ConnectionHub,
        cost_tracker: CostTracker,
    ) -> None:
        self._redis = redis
        self._supabase = supabase
        self._hub = hub
        self._cost_tracker = cost_tracker

        # Lazily imported to avoid circular dependencies at module load time
        self._router = None
        self._registry = None

    def _get_router(self):
        if self._router is None:
            from router.hybrid_router import HybridRouter
            self._router = HybridRouter()
        return self._router

    def _get_registry(self):
        if self._registry is None:
            from adapters.registry import AdapterRegistry
            self._registry = AdapterRegistry.instance()
        return self._registry

    # ── Entry point ───────────────────────────────────────────────────────

    async def handle(self, conn: ConnectionInfo, raw: str) -> None:
        try:
            data: Dict[str, Any] = json.loads(raw)
        except json.JSONDecodeError:
            await self._send_error(conn, "Invalid JSON")
            return

        msg_type = data.get("type", "")

        if msg_type == MessageType.PING:
            await self._hub.publish(WSMessage.pong(conn.session_id))
        elif msg_type == MessageType.CHAT:
            await self._handle_chat(conn, data)
        elif msg_type == MessageType.TYPING_START:
            await self._handle_typing(conn, is_typing=True)
        elif msg_type == MessageType.TYPING_STOP:
            await self._handle_typing(conn, is_typing=False)
        elif msg_type == MessageType.LEAVE:
            # Handled by the endpoint itself; ignore here
            pass
        else:
            logger.debug("Unknown message type: %s", msg_type)

    # ── Chat ─────────────────────────────────────────────────────────────

    async def _handle_chat(self, conn: ConnectionInfo, data: Dict[str, Any]) -> None:
        content: str = data.get("content", "").strip()
        if not content:
            return

        session_id = conn.session_id
        sender_id = conn.agent_id
        sender_name = conn.agent_name

        # Build and broadcast the original user message
        user_msg = WSMessage.chat(
            session_id=session_id,
            sender_id=sender_id,
            sender_name=sender_name,
            content=content,
            role=MessageRole.USER,
            reply_to=data.get("reply_to"),
        )
        await self._hub.publish(user_msg)

        # Persist
        await self._supabase.save_message({
            "id": user_msg.id,
            "session_id": session_id,
            "sender_id": sender_id,
            "sender_name": sender_name,
            "role": "user",
            "content": content,
        })

        # Determine which agents should respond
        router = self._get_router()
        registry = self._get_registry()

        # Load available agents
        agent_rows = await self._supabase.list_agents()

        decision = await router.route(
            session_id=session_id,
            message_content=content,
            sender_id=sender_id,
            available_agents=agent_rows,
            redis=self._redis,
        )

        if not decision.recipients:
            logger.debug("No recipients for message in session %s", session_id)
            return

        # Dispatch to each recipient agent
        import asyncio
        tasks = []
        for agent_cfg in decision.recipients:
            tasks.append(
                self._dispatch_to_agent(
                    session_id=session_id,
                    agent_cfg=agent_cfg,
                    user_message=content,
                    user_id=sender_id,
                )
            )
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _dispatch_to_agent(
        self,
        session_id: str,
        agent_cfg: Dict[str, Any],
        user_message: str,
        user_id: str,
    ) -> None:
        agent_id = agent_cfg["id"]
        agent_name = agent_cfg["name"]
        adapter_type = agent_cfg.get("adapter_type", "human")

        # Pre-flight budget check
        check = await self._cost_tracker.check_budget(session_id, agent_id)
        if not check.allowed:
            await self._hub.publish(
                WSMessage.system(
                    session_id=session_id,
                    content=f"⚠️ {agent_name} is paused: {check.reason}",
                    metadata={"agent_id": agent_id, "type": "budget_exceeded"},
                )
            )
            return

        if check.warning:
            await self._hub.publish(
                WSMessage.system(
                    session_id=session_id,
                    content=(
                        f"⚠️ Budget warning: {check.budget_pct*100:.0f}% of session "
                        f"budget consumed (${check.session_total_usd:.4f} / ${check.session_budget_usd:.2f})"
                    ),
                    metadata={"type": "budget_warning"},
                )
            )

        # Emit typing indicator
        await self._hub.publish(
            WSMessage.typing(session_id, agent_id, agent_name, is_typing=True)
        )

        try:
            registry = self._get_registry()
            adapter = registry.get(adapter_type)
            if adapter is None:
                logger.warning("No adapter for type: %s", adapter_type)
                return

            # Load recent history
            history = await self._supabase.get_messages(session_id, limit=20)

            result = await adapter.respond(
                session_id=session_id,
                agent_config=agent_cfg,
                user_message=user_message,
                history=history,
                redis=self._redis,
                supabase=self._supabase,
            )

            if result is None:
                return

            # Broadcast agent reply
            reply = WSMessage.chat(
                session_id=session_id,
                sender_id=agent_id,
                sender_name=agent_name,
                content=result.content,
                role=MessageRole.ASSISTANT,
                artifacts=result.artifacts,
                mentions=result.mentions,
            )
            await self._hub.publish(reply)

            # Persist reply
            await self._supabase.save_message({
                "id": reply.id,
                "session_id": session_id,
                "sender_id": agent_id,
                "sender_name": agent_name,
                "role": "assistant",
                "content": result.content,
            })

            # Record cost
            if result.tokens_in or result.tokens_out:
                await self._cost_tracker.record_cost(
                    session_id=session_id,
                    agent_id=agent_id,
                    tokens_in=result.tokens_in,
                    tokens_out=result.tokens_out,
                    cost_usd=result.cost_usd,
                    model=result.model,
                    message_id=reply.id,
                )

        except Exception as exc:
            logger.exception("Error dispatching to agent %s: %s", agent_id, exc)
            await self._hub.publish(
                WSMessage.error(
                    session_id=session_id,
                    message=f"{agent_name} encountered an error: {exc}",
                    code="agent_error",
                )
            )
        finally:
            await self._hub.publish(
                WSMessage.typing(session_id, agent_id, agent_name, is_typing=False)
            )

    # ── Typing ────────────────────────────────────────────────────────────

    async def _handle_typing(self, conn: ConnectionInfo, is_typing: bool) -> None:
        await self._hub.publish(
            WSMessage.typing(
                conn.session_id,
                conn.agent_id,
                conn.agent_name,
                is_typing=is_typing,
            )
        )

    # ── Error ─────────────────────────────────────────────────────────────

    async def _send_error(self, conn: ConnectionInfo, message: str) -> None:
        await self._hub.publish(
            WSMessage.error(session_id=conn.session_id, message=message)
        )
