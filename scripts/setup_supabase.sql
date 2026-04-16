-- AgentHub Supabase Schema
-- Run this in the Supabase SQL Editor to initialize the database.

-- ── Sessions ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sessions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL,
    description TEXT DEFAULT '',
    budget_usd  NUMERIC(10,6) DEFAULT 5.0,
    metadata    JSONB DEFAULT '{}',
    created_at  TIMESTAMPTZ DEFAULT now(),
    updated_at  TIMESTAMPTZ DEFAULT now()
);

-- ── Messages ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS messages (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id  UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    sender_id   TEXT NOT NULL,
    sender_name TEXT NOT NULL,
    role        TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content     TEXT NOT NULL DEFAULT '',
    metadata    JSONB DEFAULT '{}',
    created_at  TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS messages_session_id_created_at
    ON messages (session_id, created_at DESC);

-- ── Agent configs ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS agent_configs (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                   TEXT NOT NULL,
    adapter_type           TEXT NOT NULL,
    description            TEXT DEFAULT '',
    capabilities           TEXT[] DEFAULT '{}',
    avatar_color           TEXT DEFAULT '#6366f1',
    priority               INTEGER DEFAULT 50,
    enabled                BOOLEAN DEFAULT true,
    system_prompt_override TEXT,
    model_override         TEXT,
    hourly_cap_usd         NUMERIC(10,6),
    extra_config           JSONB DEFAULT '{}',
    created_at             TIMESTAMPTZ DEFAULT now()
);

-- ── Shared memory ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS shared_memory (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    key        TEXT NOT NULL,
    value      JSONB NOT NULL,
    updated_by TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (session_id, key)
);

-- ── Agent private memory ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS agent_memory (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id   UUID NOT NULL REFERENCES agent_configs(id) ON DELETE CASCADE,
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    key        TEXT NOT NULL,
    value      JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (agent_id, session_id, key)
);

-- ── Cost events ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS cost_events (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    agent_id   UUID NOT NULL REFERENCES agent_configs(id) ON DELETE CASCADE,
    tokens_in  INTEGER DEFAULT 0,
    tokens_out INTEGER DEFAULT 0,
    cost_usd   NUMERIC(10,8) DEFAULT 0,
    model      TEXT DEFAULT '',
    message_id UUID REFERENCES messages(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS cost_events_session_id
    ON cost_events (session_id);

-- ── Workflows ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS workflows (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name           TEXT NOT NULL,
    description    TEXT DEFAULT '',
    nodes          JSONB DEFAULT '[]',
    edges          JSONB DEFAULT '[]',
    trigger        TEXT DEFAULT 'manual' CHECK (trigger IN ('manual', 'scheduled', 'event')),
    trigger_config JSONB DEFAULT '{}',
    created_at     TIMESTAMPTZ DEFAULT now(),
    updated_at     TIMESTAMPTZ DEFAULT now()
);

-- ── Seed default agents ───────────────────────────────────────────────────
INSERT INTO agent_configs (name, adapter_type, description, capabilities, avatar_color, priority)
VALUES
    ('Claude',  'claude',  'Anthropic Claude — reasoning and planning', ARRAY['reasoning','planning','code','writing','analysis'], '#7c3aed', 10),
    ('OpenAI',  'openai',  'OpenAI GPT — code and function calling',    ARRAY['code','debug','sql','general'],                     '#10b981', 20),
    ('Gemini',  'gemini',  'Google Gemini — multimodal and long context',ARRAY['multimodal','long_context','summarization'],        '#2563eb', 30),
    ('FalAI',   'falai',   'fal.ai — image and video generation',       ARRAY['image_generation','video_generation'],              '#f59e0b', 40),
    ('Fritz',   'human',   'Human participant',                         ARRAY['general','review','approval'],                      '#6b7280', 99)
ON CONFLICT DO NOTHING;
