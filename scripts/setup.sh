#!/bin/bash
# ==============================================================================
# NetWatch - Automated Setup Script (Linux / macOS / WSL)
# ==============================================================================
set -e

echo "=========================================================="
echo " Starting NetWatch Enterprise Platform Setup"
echo " Target: EverestIMS Technologies Associate Software Engineer"
echo "=========================================================="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$ROOT_DIR/backend"

cd "$BACKEND_DIR"

echo "[1/4] Setting up Python Virtual Environment..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi

source .venv/bin/activate || source .venv/Scripts/activate

echo "[2/4] Installing Python Requirements..."
pip install --upgrade pip
pip install -r requirements.txt

echo "[3/4] Running Database Migrations..."
python manage.py makemigrations accounts devices monitoring alerts automation audit events metrics
python manage.py migrate

echo "[4/4] Seeding Database with Enterprise Demo Topology..."
python "$SCRIPT_DIR/seed_database.py"

echo "=========================================================="
echo " NetWatch Backend Setup Completed Successfully!"
echo " Run ./scripts/start.sh to launch all services."
echo "=========================================================="
