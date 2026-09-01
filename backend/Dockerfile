FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies (build essentials, postgres client libs)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    iputils-ping \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

# Copy source code
COPY . /app/backend/
COPY ../frontend /app/frontend/

WORKDIR /app/backend

EXPOSE 8000

CMD ["gunicorn", "netwatch_core.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2"]
