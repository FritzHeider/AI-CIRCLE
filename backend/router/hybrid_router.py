"""HybridRouter — three-stage routing: @mentions → capability match → volunteer opt-in."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from core.config import get_settings
from router.mention_parser import MentionParser
from router.capability_matcher import CapabilityMatcher
from router.volunteer_detector import VolunteerDetector

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class RouteDecision:
    """Result of a routing decision."""
    recipients: List[Dict[str, Any]] = field(default_factory=list)
    strategy: str = "none"          # "mention" | "capability" | "volunteer" | "none"
    mention_ids: Set[str] = field(default_factory=set)
    capability_agents: List[Dict] = field(default_factory=list)
    volunteer_agents: List[Dict] = field(default_factory=list)
    broadcast: bool = False


class HybridRouter:
    """
    Determines which agents should respond to each message.

    Stage 1 — Explicit @mentions
        If the message contains @mentions, route ONLY to those agents.
        @all / @everyone broadcasts to all enabled non-human agents.

    Stage 2 — Capability matching
        If no mentions, score agents by keyword→capability relevance.
        Select top N agents (N = settings.routing_max_recipients).

    Stage 3 — Volunteer opt-in
        Query each agent's should_volunteer(). Any that volunteer are
        merged with capability results (de-duplicated).

    If neither capability nor volunteer yields results, fall back to the
    highest-priority enabled non-human agent.
    """

    def __init__(self) -> None:
        self._mention_parser = MentionParser()
        self._capability_matcher = CapabilityMatcher()
        self._volunteer_detector = VolunteerDetector()

    async def route(
        self,
        session_id: str,
        message_content: str,
        sender_id: str,
        available_agents: List[Dict[str, Any]],
        redis: Any,
    ) -> RouteDecision:
        # Exclude sender from routing targets
        eligible = [
            a for a in available_agents
            if a["id"] != sender_id and a.get("enabled", True)
        ]
        if not eligible:
            return RouteDecision(strategy="none")

        # ── Stage 1: @mentions ──────────────────────────────────────────
        mention_ids = self._mention_parser.resolve(message_content, eligible)
        if mention_ids:
            broadcast = self._mention_parser.has_broadcast(message_content)
            recipients = [a for a in eligible if a["id"] in mention_ids]
            logger.debug(
                "Route via mention: %s (broadcast=%s)", mention_ids, broadcast
            )
            return RouteDecision(
                recipients=recipients,
                strategy="mention",
                mention_ids=mention_ids,
                broadcast=broadcast,
            )

        # ── Stage 2: Capability matching ────────────────────────────────
        non_human = [a for a in eligible if a.get("adapter_type") != "human"]
        cap_agents = self._capability_matcher.top_agents(
            message_content, non_human, max_results=settings.routing_max_recipients
        )

        # ── Stage 3: Volunteer opt-in ───────────────────────────────────
        vol_agents = await self._volunteer_detector.detect(
            session_id, message_content, non_human
        )

        # Merge capability + volunteer (de-duplicate by id)
        seen: Set[str] = set()
        merged: List[Dict] = []
        for agent in cap_agents + vol_agents:
            if agent["id"] not in seen:
                seen.add(agent["id"])
                merged.append(agent)

        if merged:
            # Respect max recipients
            recipients = merged[: settings.routing_max_recipients]
            strategy = "capability" if cap_agents else "volunteer"
            if cap_agents and vol_agents:
                strategy = "capability+volunteer"
            logger.debug("Route via %s: %s", strategy, [a["id"] for a in recipients])
            return RouteDecision(
                recipients=recipients,
                strategy=strategy,
                capability_agents=cap_agents,
                volunteer_agents=vol_agents,
            )

        # ── Fallback: highest-priority agent ───────────────────────────
        if non_human:
            fallback = sorted(non_human, key=lambda a: a.get("priority", 50))[:1]
            logger.debug("Route via fallback: %s", fallback[0]["id"])
            return RouteDecision(recipients=fallback, strategy="fallback")

        return RouteDecision(strategy="none")
