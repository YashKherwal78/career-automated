#!/bin/bash
# Auto-Mail Development Server Startup Script
# Usage: bash start.sh

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="/tmp/automail-venv"
BACKEND_PORT=8001
FRONTEND_DIR="$PROJECT_DIR/frontend"
BACKEND_DIR="$PROJECT_DIR/backend"

echo "🚀 Auto-Mail Server Startup"
echo "================================"

# ── 1. Ensure venv exists ──────────────────────────────────────────────
if [ ! -f "$VENV_DIR/bin/python" ]; then
  echo "📦 Creating virtual environment at $VENV_DIR..."
  /usr/bin/python3 -m venv "$VENV_DIR"
  "$VENV_DIR/bin/pip" install --upgrade pip
  "$VENV_DIR/bin/pip" install -r "$BACKEND_DIR/requirements.txt"
  echo "✅ Packages installed."
else
  echo "✅ Virtual environment found at $VENV_DIR"
fi

# ── 2. Kill stale processes ────────────────────────────────────────────
echo "🧹 Cleaning up stale processes..."
lsof -ti :$BACKEND_PORT | xargs kill -9 2>/dev/null || true
lsof -ti :5173 | xargs kill -9 2>/dev/null || true
sleep 1

# ── 3. Start Backend ──────────────────────────────────────────────────
echo "🖥️  Starting FastAPI backend on port $BACKEND_PORT..."
cd "$BACKEND_DIR"
"$VENV_DIR/bin/python" -m uvicorn main:app --port $BACKEND_PORT --reload &
BACKEND_PID=$!
sleep 3

# ── 4. Health check ───────────────────────────────────────────────────
if curl -sf http://localhost:$BACKEND_PORT/health > /dev/null; then
  echo "✅ Backend is healthy: http://localhost:$BACKEND_PORT"
  echo "   Docs: http://localhost:$BACKEND_PORT/docs"
else
  echo "❌ Backend health check failed!"
  kill $BACKEND_PID 2>/dev/null
  exit 1
fi

# ── 5. Start Frontend ────────────────────────────────────────────────
echo "🌐 Starting React frontend..."
cd "$FRONTEND_DIR"
npm run dev &
FRONTEND_PID=$!
sleep 3

echo ""
echo "================================"
echo "✅ Both servers are running!"
echo "   Frontend: http://localhost:5173"
echo "   Backend:  http://localhost:$BACKEND_PORT"
echo "   API Docs: http://localhost:$BACKEND_PORT/docs"
echo ""
echo "Press Ctrl+C to stop both servers."
echo "================================"

# Wait for either process to exit
wait $BACKEND_PID $FRONTEND_PID
