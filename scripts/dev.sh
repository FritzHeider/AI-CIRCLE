#!/usr/bin/env bash
# dev.sh — start backend + frontend in development mode
set -euo pipefail

# Start Redis if not running
docker compose up -d redis 2>/dev/null || true

# Backend
(
  cd backend
  source .venv/bin/activate 2>/dev/null || true
  uvicorn main:app --reload --port 8000 --log-level debug
) &
BACKEND_PID=$!

# Frontend
(
  cd frontend
  npm run dev
) &
FRONTEND_PID=$!

echo "Backend PID: $BACKEND_PID  |  Frontend PID: $FRONTEND_PID"
echo "Press Ctrl+C to stop all."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" SIGINT SIGTERM
wait
