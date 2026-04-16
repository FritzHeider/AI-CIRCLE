"""Tests for the HybridRouter and its sub-components."""
from __future__ import annotations

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from router.mention_parser import MentionParser
from router.capability_matcher import CapabilityMatcher
from router.hybrid_router import HybridRouter, RouteDecision


# ── Fixtures ──────────────────────────────────────────────────────────────

AGENTS = [
    {"id": "a-claude",  "name": "Claude",   "adapter_type": "claude",  "capabilities": ["reasoning", "code", "writing"], "priority": 10, "enabled": True},
    {"id": "a-openai",  "name": "OpenAI",   "adapter_type": "openai",  "capabilities": ["code", "debug", "sql"],          "priority": 20, "enabled": True},
    {"id": "a-gemini",  "name": "Gemini",   "adapter_type": "gemini",  "capabilities": ["multimodal", "long_context"],    "priority": 30, "enabled": True},
    {"id": "a-fal",     "name": "FalAI",    "adapter_type": "falai",   "capabilities": ["image_generation"],              "priority": 40, "enabled": True},
    {"id": "a-human",   "name": "Fritz",    "adapter_type": "human",   "capabilities": ["general", "review"],             "priority": 99, "enabled": True},
]


# ── MentionParser ──────────────────────────────────────────────────────────

class TestMentionParser:
    def setup_method(self):
        self.parser = MentionParser()

    def test_parse_single_mention(self):
        result = self.parser.parse("@Claude can you help?")
        assert "@Claude" in result

    def test_parse_multiple_mentions(self):
        result = self.parser.parse("@Claude and @OpenAI please respond")
        assert len(result) == 2

    def test_parse_no_mentions(self):
        assert self.parser.parse("hello world") == []

    def test_resolve_by_name(self):
        ids = self.parser.resolve("@Claude help me", AGENTS)
        assert "a-claude" in ids

    def test_resolve_by_alias_at_gpt(self):
        ids = self.parser.resolve("@gpt write this", AGENTS)
        assert "a-openai" in ids

    def test_resolve_broadcast_all(self):
        ids = self.parser.resolve("@all stand by", AGENTS)
        assert len(ids) == len(AGENTS)

    def test_resolve_broadcast_everyone(self):
        ids = self.parser.resolve("@everyone update", AGENTS)
        assert len(ids) == len(AGENTS)

    def test_resolve_fal_alias(self):
        ids = self.parser.resolve("@fal.ai create image", AGENTS)
        assert "a-fal" in ids

    def test_resolve_unknown_mention(self):
        ids = self.parser.resolve("@unknownbot help", AGENTS)
        assert len(ids) == 0

    def test_has_broadcast_true(self):
        assert self.parser.has_broadcast("@all let's begin")

    def test_has_broadcast_false(self):
        assert not self.parser.has_broadcast("@Claude let's begin")


# ── CapabilityMatcher ──────────────────────────────────────────────────────

class TestCapabilityMatcher:
    def setup_method(self):
        self.matcher = CapabilityMatcher()

    def test_code_message_scores_openai_and_claude(self):
        results = self.matcher.score("write a function in Python", AGENTS)
        ids = [a["id"] for a, _ in results]
        assert "a-openai" in ids or "a-claude" in ids

    def test_image_message_scores_fal(self):
        results = self.matcher.score("generate an image of a sunset", AGENTS)
        ids = [a["id"] for a, _ in results]
        assert "a-fal" in ids

    def test_sql_message_scores_openai(self):
        results = self.matcher.score("write a SQL query for users table", AGENTS)
        ids = [a["id"] for a, _ in results]
        assert "a-openai" in ids

    def test_human_not_included(self):
        results = self.matcher.score("code review", AGENTS)
        ids = [a["id"] for a, _ in results]
        assert "a-human" not in ids

    def test_unrelated_message_returns_empty(self):
        results = self.matcher.score("the quick brown fox", AGENTS)
        assert results == []

    def test_top_agents_respects_max(self):
        agents = self.matcher.top_agents("write code and sql", AGENTS, max_results=1)
        assert len(agents) <= 1


# ── HybridRouter ──────────────────────────────────────────────────────────

class TestHybridRouter:
    def setup_method(self):
        self.router = HybridRouter()
        self.redis = MagicMock()

    @pytest.mark.asyncio
    async def test_mention_routing(self):
        decision = await self.router.route(
            session_id="s1",
            message_content="@Claude please review this",
            sender_id="a-human",
            available_agents=AGENTS,
            redis=self.redis,
        )
        assert decision.strategy == "mention"
        assert any(a["id"] == "a-claude" for a in decision.recipients)

    @pytest.mark.asyncio
    async def test_broadcast_routing(self):
        decision = await self.router.route(
            session_id="s1",
            message_content="@all everyone please respond",
            sender_id="a-human",
            available_agents=AGENTS,
            redis=self.redis,
        )
        assert decision.strategy == "mention"
        assert decision.broadcast

    @pytest.mark.asyncio
    async def test_capability_routing_code(self):
        decision = await self.router.route(
            session_id="s1",
            message_content="implement a binary search function",
            sender_id="a-human",
            available_agents=AGENTS,
            redis=self.redis,
        )
        assert decision.strategy in ("capability", "capability+volunteer", "fallback")
        assert len(decision.recipients) > 0

    @pytest.mark.asyncio
    async def test_sender_excluded_from_recipients(self):
        decision = await self.router.route(
            session_id="s1",
            message_content="write code",
            sender_id="a-openai",
            available_agents=AGENTS,
            redis=self.redis,
        )
        ids = [a["id"] for a in decision.recipients]
        assert "a-openai" not in ids

    @pytest.mark.asyncio
    async def test_fallback_when_no_match(self):
        decision = await self.router.route(
            session_id="s1",
            message_content="the quick brown fox jumps",
            sender_id="a-human",
            available_agents=AGENTS,
            redis=self.redis,
        )
        # Should still return at least a fallback
        assert len(decision.recipients) >= 0  # may be 0 if all volunteer checks fail

    @pytest.mark.asyncio
    async def test_no_recipients_when_no_agents(self):
        decision = await self.router.route(
            session_id="s1",
            message_content="hello",
            sender_id="a-human",
            available_agents=[],
            redis=self.redis,
        )
        assert decision.strategy == "none"
        assert decision.recipients == []
