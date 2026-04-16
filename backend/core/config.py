"""Application configuration via pydantic-settings."""
from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ─────────────────────────────────────────────────────────────
    app_name: str = "AgentHub"
    app_version: str = "0.1.0"
    debug: bool = False
    log_level: str = "INFO"

    # ── Server ──────────────────────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8000
    allowed_origins: List[str] = Field(
        default=["http://localhost:5173", "http://localhost:3000"]
    )

    # ── Redis ────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    redis_max_connections: int = 20
    redis_socket_timeout: float = 5.0

    # ── Supabase ─────────────────────────────────────────────────────────
    supabase_url: str = ""
    supabase_service_key: str = ""

    # ── LLM API keys (optional — adapter checks at call time) ────────────
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    google_api_key: str = ""
    falai_api_key: str = ""

    # ── Cost / budget defaults (USD) ─────────────────────────────────────
    default_session_budget_usd: float = 5.0
    default_agent_hourly_cap_usd: float = 1.0
    budget_warning_threshold: float = 0.80   # 80 % triggers warning

    # ── Memory ───────────────────────────────────────────────────────────
    memory_cache_ttl_seconds: int = 300      # 5 min Redis TTL
    max_shared_memory_entries: int = 100
    max_private_memory_entries: int = 50

    # ── WebSocket ────────────────────────────────────────────────────────
    ws_ping_interval: float = 20.0
    ws_ping_timeout: float = 10.0
    ws_max_message_size: int = 1_048_576     # 1 MB

    # ── Routing ──────────────────────────────────────────────────────────
    routing_volunteer_timeout_ms: int = 2_000
    routing_max_recipients: int = 5


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
