#!/bin/bash
# scripts/restart.sh
# Restarts the development session cleanly.

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"$DIR/stop.sh"
sleep 2
"$DIR/dev.sh"
