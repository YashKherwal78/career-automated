#!/bin/bash
# scripts/stop.sh
# Gracefully stops the tmux session and kills all processes.

SESSION_NAME="careerautomated"

echo "Stopping CareerAutomated development runtime..."

# Kill uvicorn process manually if active
lsof -t -i :8000 | xargs kill -9 2>/dev/null

# Kill Vite process manually if active
lsof -t -i :8080 | xargs kill -9 2>/dev/null

# Terminate tmux session
tmux kill-session -t "$SESSION_NAME" 2>/dev/null

# Clean up any leftover worker python processes
pkill -f "backend/src/workers/" 2>/dev/null

echo "Stopped successfully."
