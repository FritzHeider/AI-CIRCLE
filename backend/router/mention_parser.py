"""MentionParser — extracts @mentions from messages and resolves them to agent IDs."""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Set

# Normalise common shorthand @mentions to canonical adapter types
MENTION_ALIASES: Dict[str, str] = {
    "@claude":    "claude",
    "@anthropic": "claude",
    "@openai":    "openai",
    "@gpt":       "openai",
    "@codex":     "openai",
    "@gemini":    "gemini",
    "@google":    "gemini",
    "@fal":       "falai",
    "@fal.ai":    "falai",
    "@falai":     "falai",
    "@human":     "human",
    "@me":        "human",
    "@all":       "__all__",
    "@everyone":  "__all__",
}

_MENTION_RE = re.compile(r"@[\w.\-]+")


class MentionParser:
    """Parses @mention tokens from a message string."""

    def parse(self, text: str) -> List[str]:
        """
        Return a list of raw @mention strings found in *text*.

        Example: "@Claude can you review this?" → ["@Claude"]
        """
        return _MENTION_RE.findall(text)

    def resolve(
        self,
        text: str,
        agents: List[Dict],
    ) -> Set[str]:
        """
        Resolve @mentions to a set of agent IDs from *agents*.

        Handles:
          - @all / @everyone  → returns ALL agent IDs
          - @<adapter_type>   → returns all agents of that type
          - @<agent_name>     → case-insensitive name match
          - unknown mentions  → silently ignored

        Returns an empty set if no mentions are found.
        """
        raw_mentions = self.parse(text)
        if not raw_mentions:
            return set()

        resolved: Set[str] = set()

        for mention in raw_mentions:
            lower = mention.lower()

            # Broadcast
            alias = MENTION_ALIASES.get(lower)
            if alias == "__all__":
                return {a["id"] for a in agents}

            # Alias to adapter type
            if alias:
                for a in agents:
                    if a.get("adapter_type") == alias and a.get("enabled", True):
                        resolved.add(a["id"])
                continue

            # Direct name match (case-insensitive, strip @)
            target_name = mention.lstrip("@").lower()
            for a in agents:
                if a.get("name", "").lower() == target_name and a.get("enabled", True):
                    resolved.add(a["id"])

        return resolved

    def has_broadcast(self, text: str) -> bool:
        """Return True if the message contains @all or @everyone."""
        raw = [m.lower() for m in self.parse(text)]
        return any(MENTION_ALIASES.get(m) == "__all__" for m in raw)

    def has_any_mention(self, text: str) -> bool:
        return bool(self.parse(text))
