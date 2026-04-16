#!/usr/bin/env bash
# setup_local.sh — one-command local development setup
set -euo pipefail

echo "=== AgentHub Local Setup ==="

# Check dependencies
command -v docker  >/dev/null 2>&1 || { echo "Docker is required"; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "Python 3.11+ is required"; exit 1; }
command -v node    >/dev/null 2>&1 || { echo "Node.js 18+ is required"; exit 1; }

# Copy env file
if [ ! -f .env ]; then
  cp .env.example .env
  echo "✓ Created .env from .env.example — fill in your API keys!"
else
  echo "✓ .env already exists"
fi

# Start Redis via Docker Compose (detached)
echo "Starting Redis…"
docker compose up -d redis
echo "✓ Redis started"

# Backend venv
echo "Setting up Python virtual environment…"
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo "✓ Backend dependencies installed"
cd ..

# Frontend deps
echo "Installing frontend dependencies…"
cd frontend
npm install --silent
echo "✓ Frontend dependencies installed"
cd ..

echo ""
echo "=== Setup complete! ==="
echo ""
echo "To start the backend:"
echo "  cd backend && source .venv/bin/activate && uvicorn main:app --reload"
echo ""
echo "To start the frontend:"
echo "  cd frontend && npm run dev"
echo ""
echo "Open http://localhost:5173 in your browser."
