#!/usr/bin/env bash
set -euo pipefail

echo "== 5e-ai-character-forge :: bootstrap =="

[[ -f .env ]] || cp .env.example .env
PORT_API=${PORT_API:-8000}
PORT_WEB=${PORT_WEB:-5173}

# --- Python venv + deps ---
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r api/requirements.txt

# --- Frontend scaffold (Vite) ---
if [[ ! -f web/package.json ]]; then
  echo "Scaffolding Vite (React+TS) in /web..."
  npm create vite@latest web -- --template react-ts
  (cd web && npm i && npm i axios)
else
  (cd web && npm i)
fi

# --- Kill any stale API on :$PORT_API (optional, best effort) ---
(lsof -ti ":$PORT_API" | xargs -r kill -9) 2>/dev/null || true

# --- Start API with uvicorn (module path) ---
# This fixes the "attempted relative import with no known parent package" error
uvicorn api.app.main:app --host 0.0.0.0 --port "$PORT_API" --reload &
API_PID=$!
echo "API started (PID ${API_PID}) at http://localhost:${PORT_API}"

# Ensure cleanup on exit
cleanup() { kill "$API_PID" 2>/dev/null || true; }
trap cleanup EXIT

# --- Start Vite (pass API port through env for the client) ---
cd web
VITE_API_PORT="$PORT_API" npm run dev
