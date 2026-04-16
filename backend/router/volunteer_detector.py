"""VolunteerDetector — asks each adapter if it wants to volunteer for a message."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List

from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class VolunteerDetector:
    """
    Concurrently queries each enabled agent's adapter.should_volunteer().

    Agents that raise an exception or exceed the timeout are silently skipped.
    """

    async def detect(
        self,
        session_id: str,
        message_content: str,
        agents: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Return a list of agents that volunteered to respond.

        Parameters
        ----------
        session_id      : Current session ID
        message_content : The message text to evaluate
        agents          : List of agent config dicts from Supabase

        Returns
        -------
        List of agent dicts whose adapters returned True from should_volunteer()
        """
        from adapters.registry import AdapterRegistry
        registry = AdapterRegistry.instance()

        timeout = settings.routing_volunteer_timeout_ms / 1000.0

        async def _check(agent: Dict[str, Any]) -> bool:
            if not agent.get("enabled", True):
                return False
            if agent.get("adapter_type") == "human":
                return False
            adapter = registry.get(agent.get("adapter_type", ""))
            if adapter is None:
                return False
            try:
                return await asyncio.wait_for(
                    adapter.should_volunteer(session_id, message_content, agent),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                logger.debug(
                    "Volunteer timeout: agent=%s", agent.get("id")
                )
                return False
            except Exception as exc:
                logger.debug(
                    "Volunteer error: agent=%s err=%s", agent.get("id"), exc
                )
                return False

        results = await asyncio.gather(*[_check(a) for a in agents])
        return [a for a, volunteered in zip(agents, results) if volunteered]
