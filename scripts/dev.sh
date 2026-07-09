#!/bin/bash
# scripts/dev.sh
# Starts the tmux session for CareerAutomated development environment.

SESSION_NAME="careerautomated"

# Create logs directory
mkdir -p logs

# Check if session exists
tmux has-session -t "$SESSION_NAME" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "Tmux session '$SESSION_NAME' already exists. Attach to it using './scripts/attach.sh'."
    exit 0
fi

echo "Starting CareerAutomated Tmux Session..."

# Window 1: Pipeline (runs run_pipeline.py with NO_API=1 to let uvicorn run in its own window)
NO_API=1 tmux new-session -d -s "$SESSION_NAME" -n "pipeline" "python3 run_pipeline.py 2>&1 | tee logs/scheduler.log"

# Window 2: FastAPI (runs uvicorn)
tmux new-window -t "$SESSION_NAME" -n "fastapi" "python3 -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 2>&1 | tee logs/api.log"

# Window 3: Frontend (runs Vite server)
tmux new-window -t "$SESSION_NAME" -n "frontend" "cd frontend && npm run dev 2>&1 | tee ../logs/frontend.log"

# Window 4: Worker Logs (tails the redirect log files)
tmux new-window -t "$SESSION_NAME" -n "worker-logs"
tmux send-keys -t "$SESSION_NAME:worker-logs" "tail -f logs/discovery.log logs/verification.log logs/crawler.log logs/cleanup.log" Enter

# Window 5: Database (sqlite3 client)
tmux new-window -t "$SESSION_NAME" -n "database"
tmux send-keys -t "$SESSION_NAME:database" "sqlite3 data/crm.db" Enter
tmux send-keys -t "$SESSION_NAME:database" "# Quick Queries: " Enter
tmux send-keys -t "$SESSION_NAME:database" "# SELECT COUNT(*) FROM normalized_jobs\;" Enter
tmux send-keys -t "$SESSION_NAME:database" "# SELECT COUNT(*) FROM ats_registry\;" Enter
tmux send-keys -t "$SESSION_NAME:database" "# SELECT worker_name, status, failures FROM worker_states\;" Enter

# Window 6: Monitoring (auto-refresh script showing current stats)
tmux new-window -t "$SESSION_NAME" -n "monitoring"
tmux send-keys -t "$SESSION_NAME:monitoring" "while true\; do clear\; curl -s http://localhost:8000/api/v1/dashboard | json_pp 2>/dev/null || echo \"API Offline\"\; sleep 3\; done" Enter

# Select the first window
tmux select-window -t "$SESSION_NAME:pipeline"

echo "CareerAutomated development environment started in tmux session '$SESSION_NAME'."
echo "To attach, run: ./scripts/attach.sh"
