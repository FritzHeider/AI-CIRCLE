# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

AgentHub is a multi-agent group chat orchestrator. A FastAPI backend manages WebSocket sessions where multiple AI agents (Claude, OpenAI, Gemini, fal.ai) and human participants share a real-time chat room. Messages are routed via a three-stage `HybridRouter`: @mention → capability matching → volunteer opt-in.

## Development Commands

### First-time setup
```bash
./scripts/setup_local.sh   # creates venv, installs deps, starts Redis via Docker
```

### Start dev servers
```bash
./scripts/dev.sh           # starts Redis (Docker), backend (port 8000), frontend (port 5173)
```

Or individually:
```bash
# Backend
cd backend && source .venv/bin/activate && uvicorn main:app --reload --port 8000 --log-level debug

# Frontend
cd frontend && npm run dev
```

### Backend tests
```bash
cd backend && source .venv/bin/activate
pytest                          # all tests
pytest tests/test_router.py     # single file
pytest -k "test_mention"        # single test by name
```

### Linting
```bash
# Backend (ruff, line-length 100, Python 3.11)
cd backend && ruff check . && ruff format .

# Frontend (ESLint, zero warnings allowed)
cd frontend && npm run lint

# Frontend type-check + build
cd frontend && npm run build
```

## Architecture

```
Browser ──WebSocket──▶ FastAPI/main.py ──▶ HybridRouter ──▶ AgentAdapters
                            │                                Claude/OpenAI/Gemini/fal.ai
                            ▼
                       Redis Pub/Sub ◀──▶ ConnectionHub (websocket/hub.py)
                            │
                       Supabase (PostgreSQL) — persistent messages, agent configs, sessions
```

### Backend (`backend/`)

| Directory | Purpose |
|---|---|
| `core/` | `config.py` (pydantic-settings, `get_settings()`), lifespan events, startup checks |
| `adapters/` | One file per LLM provider, all extend `AgentAdapter` base class. Register with `@register_adapter("type")` |
| `router/` | `HybridRouter` orchestrates three stages; sub-components are `MentionParser`, `CapabilityMatcher`, `VolunteerDetector` |
| `websocket/` | `protocol.py` (WSMessage dataclass), `hub.py` (Redis pub/sub fan-out), `handlers.py` (incoming message dispatch) |
| `services/` | `RedisService`, `SupabaseService`, `SessionManager`, `CostTracker`, `MemoryService` |
| `api/` | FastAPI routers: sessions, agents, messages, memory, costs, workflows |
| `models/` | Pydantic request/response models |
| `tests/` | pytest with `asyncio_mode = "auto"`; fixtures in `conftest.py` |

### Adapter interface
Every adapter implements:
- `adapter_type: str` (class attribute, matches DB `adapter_type` column)
- `capabilities: List[str]` (used by `CapabilityMatcher`)
- `async respond(session_id, agent_config, user_message, history, redis, supabase) -> AdapterResponse | None`
- `async should_volunteer(session_id, message_content, agent_config) -> bool` (optional)

`AdapterResponse` carries: `content`, `model`, `tokens_in`, `tokens_out`, `cost_usd`, `artifacts`, `mentions`.

### Routing logic (`router/hybrid_router.py`)
1. **@mention** — explicit `@Name` routes only to named agents; `@all`/`@everyone` broadcasts
2. **Capability matching** — keyword scoring against agent `capabilities` lists; selects top N (config: `routing_max_recipients`, default 5)
3. **Volunteer opt-in** — calls `should_volunteer()` on each non-human agent; merges with capability results
4. **Fallback** — highest-priority enabled non-human agent

### Frontend (`frontend/src/`)

| Directory | Purpose |
|---|---|
| `lib/api.ts` | Typed REST client (`api.sessions.*`, `api.agents.*`, etc.); base URL from `VITE_API_URL` |
| `lib/websocket.ts` | `AgentHubWebSocket` class with exponential backoff reconnect; base URL from `VITE_WS_URL` |
| `hooks/` | `useWebSocket`, `useChat`, `useAgents`, `useCosts` — state management via Zustand |
| `components/chat/` | Chat room UI |
| `components/workflow/` | ReactFlow-based workflow editor |
| `components/dashboard/` | Recharts cost/usage dashboards |
| `components/config/` | Agent configuration panels |

### WebSocket protocol
Connect to `ws://localhost:8000/ws/{session_id}?agent_id=…&agent_name=…`. On connect the server pushes the last 50 messages as a `HISTORY` type message. All messages are `WSMessage` JSON objects with `type`, `session_id`, `sender_id`, `sender_name`, `content`, `metadata`.

## Key Configuration

All settings live in `backend/core/config.py` (pydantic-settings, reads from `.env`):
- `SUPABASE_URL` / `SUPABASE_SERVICE_KEY` — required
- `REDIS_URL` — default `redis://localhost:6379/0`
- `DEFAULT_SESSION_BUDGET_USD` — per-session spending cap (default `5.0`)
- `ROUTING_MAX_RECIPIENTS` — max agents per message (default `5`)
- `ROUTING_VOLUNTEER_TIMEOUT_MS` — volunteer detection deadline (default `2000`)

Frontend env vars (prefix `VITE_`):
- `VITE_API_URL` — REST base URL (default `http://localhost:8000`)
- `VITE_WS_URL` — WebSocket base URL (default `ws://localhost:8000`)

## Adding a New Agent Adapter

1. Create `backend/adapters/your_adapter.py`
2. Subclass `AgentAdapter`, set `adapter_type` and `capabilities`
3. Implement `async respond(...)` returning `AdapterResponse | None`
4. Decorate with `@register_adapter("your_type")` (from `adapters/registry.py`)
5. Add the agent via the Agents panel in the UI or `POST /api/agents`

## Infrastructure

- **Redis** runs via `docker-compose.yml` (service: `redis`); used for pub/sub fan-out and session caching
- **Supabase schema** is initialized by running `scripts/setup_supabase.sql` in the Supabase SQL Editor
- **Deployment**: Railway (`railway.toml`); CI/CD via `.github/workflows/ci.yml` deploys `main` branch automatically
