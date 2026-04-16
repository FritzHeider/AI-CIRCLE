"""CapabilityMatcher — scores agents by relevance to a message's intent."""
from __future__ import annotations

from typing import Dict, List, Tuple

# Keyword → capability tag mapping
KEYWORD_TO_CAPABILITY: Dict[str, str] = {
    # Code
    "code": "code", "function": "code", "class": "code", "script": "code",
    "implement": "code", "program": "code", "refactor": "code",
    # Debug
    "bug": "debug", "fix": "debug", "error": "debug", "issue": "debug",
    "trace": "debug", "crash": "debug",
    # SQL / data
    "sql": "sql", "query": "sql", "database": "sql", "table": "sql",
    "select": "sql", "insert": "sql", "schema": "sql",
    # Reasoning
    "plan": "reasoning", "design": "reasoning", "architect": "reasoning",
    "analyse": "reasoning", "analyze": "reasoning", "strategy": "reasoning",
    "reason": "reasoning", "think": "reasoning",
    # Writing
    "write": "writing", "draft": "writing", "summarize": "writing",
    "summary": "writing", "document": "writing", "blog": "writing",
    "email": "writing", "report": "writing",
    # Images
    "image": "image_generation", "picture": "image_generation",
    "photo": "image_generation", "draw": "image_generation",
    "generate": "image_generation", "artwork": "image_generation",
    "illustration": "image_generation", "flux": "image_generation",
    # Video
    "video": "video_generation", "clip": "video_generation",
    # Multimodal / long context
    "translate": "translation", "long": "long_context",
    "multimodal": "multimodal",
}

# Capability → priority boost (higher = more preferred)
CAPABILITY_PRIORITY: Dict[str, float] = {
    "image_generation": 2.0,
    "video_generation": 2.0,
    "sql":              1.8,
    "code":             1.5,
    "debug":            1.5,
    "reasoning":        1.3,
    "analysis":         1.2,
    "writing":          1.1,
    "translation":      1.1,
    "general":          1.0,
}


class CapabilityMatcher:
    """
    Scores each agent by how well its capabilities match the message keywords.

    Scoring formula (per agent):
        score = Σ (capability_priority × agent_priority_weight)
            for each keyword in message that maps to a capability
            the agent declares

    where agent_priority_weight = 1 / (1 + agent.priority)
        (lower priority number = higher weight)
    """

    def score(
        self,
        message: str,
        agents: List[Dict],
    ) -> List[Tuple[Dict, float]]:
        """
        Return *agents* sorted by descending relevance score.

        Only agents with score > 0 are returned.
        """
        lower = message.lower()
        words = set(lower.split())

        # Collect relevant capabilities mentioned in the message
        relevant_caps: Dict[str, float] = {}
        for word in words:
            cap = KEYWORD_TO_CAPABILITY.get(word)
            if cap:
                boost = CAPABILITY_PRIORITY.get(cap, 1.0)
                relevant_caps[cap] = max(relevant_caps.get(cap, 0.0), boost)

        if not relevant_caps:
            return []

        scored: List[Tuple[Dict, float]] = []
        for agent in agents:
            if not agent.get("enabled", True):
                continue
            if agent.get("adapter_type") == "human":
                continue  # humans are never auto-routed by capability

            agent_caps: List[str] = agent.get("capabilities", [])
            agent_priority: int = agent.get("priority", 50)
            weight = 1.0 / (1.0 + agent_priority)

            score = sum(
                relevant_caps[cap] * weight
                for cap in agent_caps
                if cap in relevant_caps
            )
            if score > 0:
                scored.append((agent, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def top_agents(
        self,
        message: str,
        agents: List[Dict],
        max_results: int = 3,
    ) -> List[Dict]:
        """Return top *max_results* agents by capability score."""
        return [a for a, _ in self.score(message, agents)[:max_results]]
