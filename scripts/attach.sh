#!/bin/bash
# scripts/attach.sh
# Attaches to the careerautomated tmux session.

SESSION_NAME="careerautomated"

tmux has-session -t "$SESSION_NAME" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Tmux session '$SESSION_NAME' is not running. Start it with './scripts/dev.sh'."
    exit 1
fi

tmux attach-session -t "$SESSION_NAME"
