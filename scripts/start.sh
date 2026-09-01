#!/bin/bash
# ==============================================================================
# NetWatch - Service Startup Script
# ==============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$ROOT_DIR/backend"

cd "$BACKEND_DIR"
source .venv/bin/activate || source .venv/Scripts/activate

echo "Starting NetWatch API Server on http://127.0.0.1:8000..."
python manage.py runserver 0.0.0.0:8000
