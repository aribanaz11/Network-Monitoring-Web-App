#!/bin/bash
# ==============================================================================
# NetWatch - Service Shutdown Script
# ==============================================================================
echo "Stopping NetWatch processes..."

# Stop Django
pkill -f "manage.py runserver" || echo "No running Django server."

# Stop Celery
pkill -f "celery -A netwatch_core" || echo "No running Celery workers."

echo "All NetWatch processes stopped."
