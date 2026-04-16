# AgentHub

**Multi-agent group chat orchestrator** — bring your AI subscriptions into a single real-time chat room.

## What it does

AgentHub connects Claude, OpenAI, Gemini, fal.ai, and your own human participation into a shared WebSocket chat room. Messages are intelligently routed using a three-stage hybrid router:

1. **@mention** — `@Claude review this` routes only to Claude
2. **Capability matching** — keyword scoring picks the best-suited agent(s)
3. **Volunteer opt-in** — agents declare they want to answer certain message types

Every response is tracked for token usage and cost against configurable per-session budgets.

---

## Architecture

```
Browser ──WebSocket──▶ FastAPI ──▶ HybridRouter ──▶ AgentAdapters
                           │                          Claude / OpenAI
                           │                          Gemini / fal.ai
                           ▼
                        Redis Pub/Sub ◀──────────────▶ WebSocket Hub
                           │
                        Supabase (PostgreSQL)
```

| Layer | Tech |
|---|---|
| Backend | Python 3.11, FastAPI, WebSocket |
| Real-time | Redis 7 Pub/Sub |
| Database | Supabase (PostgreSQL) |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS |
| Workflow | ReactFlow |
| Charts | Recharts |
| Deploy | Docker, Railway, GitHub Actions |

---

## Quick Start

### Prerequisites

- Docker Desktop
- Python 3.11+
- Node.js 20+
- Supabase project (free tier works)
- Redis (included in `docker-compose.yml`)

### 1. Clone & configure

```bash
git clone <your-repo-url>
cd agenthub
cp .env.example .env
# Edit .env and fill in your API keys
```

### 2. Initialize Supabase

Open your Supabase project → SQL Editor, paste and run `scripts/setup_supabase.sql`.

### 3. Start development

```bash
chmod +x scripts/setup_local.sh scripts/dev.sh
./scripts/setup_local.sh   # first time only
./scripts/dev.sh           # starts backend + frontend
```

Open **http://localhost:5173** in your browser.

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `SUPABASE_URL` | ✅ | Your Supabase project URL |
| `SUPABASE_SERVICE_KEY` | ✅ | Supabase service role key |
| `REDIS_URL` | ✅ | Redis connection URL (default: `redis://localhost:6379/0`) |
| `ANTHROPIC_API_KEY` | ⬜ | Claude adapter |
| `OPENAI_API_KEY` | ⬜ | OpenAI adapter |
| `GOOGLE_API_KEY` | ⬜ | Gemini adapter |
| `FALAI_API_KEY` | ⬜ | fal.ai adapter |
| `DEFAULT_SESSION_BUDGET_USD` | ⬜ | Per-session spending limit (default: `5.0`) |

---

## Project Structure

```
agenthub/
├── backend/
│   ├── core/           # Config, events, dependencies
│   ├── websocket/      # Protocol, hub, handlers
│   ├── services/       # Redis, Supabase, session mgr, memory, cost tracker
│   ├── adapters/       # Claude, OpenAI, Gemini, fal.ai, Human
│   ├── router/         # HybridRouter, MentionParser, CapabilityMatcher
│   ├── api/            # REST routers (sessions, agents, messages, memory, costs, workflows)
│   ├── models/         # Pydantic models
│   ├── tests/          # pytest test suite
│   └── main.py
├── frontend/
│   └── src/
│       ├── components/ # chat/, dashboard/, config/, workflow/
│       ├── hooks/      # useWebSocket, useChat, useAgents, useCosts
│       ├── lib/        # api.ts, websocket.ts
│       └── types/      # Shared TypeScript types
├── scripts/
│   ├── setup_supabase.sql
│   ├── setup_local.sh
│   └── dev.sh
├── .github/workflows/ci.yml
└── docker-compose.yml
```

---

## Adding a New Agent

1. Create `backend/adapters/your_adapter.py`
2. Decorate with `@register_adapter("your_type")`
3. Implement `async def respond(...)` and optionally `should_volunteer(...)`
4. Add the agent via the **Agents** panel in the UI or the REST API

---

## Deployment (Railway)

```bash
# Install Railway CLI
npm install -g @railway/cli
railway login

# Deploy backend
railway up --service backend

# Deploy frontend
cd frontend && railway up --service frontend
```

Set all environment variables in the Railway project dashboard before deploying.

CI/CD via GitHub Actions automatically deploys on pushes to `main`.

---

## License

MIT
# AI-CIRCLE
