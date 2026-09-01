#!/usr/bin/env bash
# Exit on error
set -o errexit

echo "Installing Python dependencies..."
pip install -r backend/requirements.txt

echo "Collecting static assets..."
python backend/manage.py collectstatic --no-input

echo "Applying database migrations..."
python backend/manage.py migrate

echo "Seeding initial enterprise demo devices..."
python backend/manage.py seed_network_demo

echo "NetWatch Build Completed Successfully!"
