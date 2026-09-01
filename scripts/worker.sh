#!/bin/bash
# ==============================================================================
# NetWatch - Celery Background Worker Startup Script
# ==============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$ROOT_DIR/backend"

cd "$BACKEND_DIR"
source .venv/bin/activate || source .venv/Scripts/activate

echo "Starting NetWatch Celery Worker and Beat Scheduler..."
celery -A netwatch_core worker --beat --loglevel=info --concurrency=4
