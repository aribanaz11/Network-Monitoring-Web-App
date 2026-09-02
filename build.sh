#!/usr/bin/env bash
# Exit on error
set -o errexit

echo "==> [NetWatch] Installing Python production dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "==> [NetWatch] Collecting static assets with WhiteNoise..."
python backend/manage.py collectstatic --no-input

echo "==> [NetWatch] Applying database migrations..."
python backend/manage.py migrate

echo "==> [NetWatch] Seeding initial network inventory demo devices..."
python backend/manage.py seed_network_demo

echo "==> [NetWatch] Build completed successfully!"
