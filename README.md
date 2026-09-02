# NetWatch — Enterprise Network Device Monitoring & Management System

[![NetWatch CI](https://github.com/aribanaz11/Network-Monitoring-Web-App/actions/workflows/ci.yml/badge.svg)](https://github.com/aribanaz11/Network-Monitoring-Web-App/actions)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Django 5.1](https://img.shields.io/badge/Django-5.1-green.svg)](https://www.djangoproject.com/)
[![Render](https://img.shields.io/badge/Deploy%20to-Render-46E3B7.svg)](https://render.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An enterprise-grade, full-stack Network Management & Observability Platform engineered for ITOM/AIOps operations. NetWatch provides sub-second multi-subsystem reachability diagnostics, a 5-state deterministic device lifecycle state machine, alert storm suppression with automated incident deduplication, non-blocking TCP multi-port diagnostics, secure SSH command automation with Fernet credential encryption at rest, and RFC 7807 problem details error handling.

---

## 🏗️ Architecture & Technology Stack

- **Backend Web Core**: Django 5.1 & Django REST Framework
- **Production WSGI Server**: Gunicorn (Linux/Render) / Waitress (Multi-Threaded Windows)
- **Static Asset Pipeline**: WhiteNoise (Compressed & Cached)
- **Database & Persistence**: PostgreSQL 16 (Relational System of Record via `dj-database-url`) / SQLite3 (Zero-config fallback)
- **Distributed Worker Engine**: Celery 5.4 with RabbitMQ 3.13 Task Broker & Redis 7 Result Store
- **Event Streaming & Anomaly Detection**: Apache Kafka Domain Event Bus with 5 dedicated topics
- **Frontend User Interface**: Ultra-Clean Modern Light SPA (Apple/Linear aesthetic with Chart.js telemetry)
- **Security & Cryptography**: AES-CBC Fernet symmetric encryption at rest, JWT Authentication with Token Blacklisting, and 3-Tier RBAC (`Admin`, `Operator`, `Viewer`).

---

## 🚀 Live Production Deployment on Render

NetWatch is pre-configured for zero-friction cloud deployment on [Render](https://render.com).

### Option 1: 1-Click Infrastructure Blueprint (Recommended)
1. Navigate to [**Render Blueprint Deploy**](https://dashboard.render.com/blueprints/new).
2. Connect your GitHub repository: `https://github.com/aribanaz11/Network-Monitoring-Web-App`.
3. Click **Apply**. Render will automatically provision the web service, execute migrations, collect static assets, seed demo inventory, and launch your live URL.

### Option 2: Manual Web Service Setup
If creating a manual Web Service on Render:
- **Repository**: `https://github.com/aribanaz11/Network-Monitoring-Web-App`
- **Environment / Runtime**: `Python 3`
- **Build Command**:
  ```bash
  pip install -r requirements.txt && python backend/manage.py collectstatic --no-input && python backend/manage.py migrate && python backend/manage.py seed_network_demo
  ```
- **Start Command**:
  ```bash
  gunicorn --chdir backend netwatch_core.wsgi:application --bind 0.0.0.0:$PORT --workers 2
  ```
- **Health Check Path**: `/health`
- **Plan / Instance Type**: `Free`

---

## 🔐 Environment Variables

Copy `.env.example` to `.env` to configure your environment:

| Variable | Description | Default / Example |
|---|---|---|
| `DJANGO_SECRET_KEY` | Unique Django secret cryptographic key | `generateValue: true` on Render |
| `DEBUG` | Toggle debug mode (Must be `False` in production) | `False` |
| `ALLOWED_HOSTS` | Comma-separated list of valid host headers | `*,.onrender.com` |
| `DATABASE_URL` | PostgreSQL connection URL string | Provided automatically by Render DB |
| `USE_SQLITE` | Standalone file-based database fallback | `True` (if no PostgreSQL attached) |
| `FERNET_KEY` | 32-byte base64 key for credential encryption | `W3sO-LqP7b_dG5vUv-0L2Y1t9kLpM_xZ7sQ2dF4jK8M=` |
| `SIMULATOR_MODE` | Simulates packet loss/jitter on synthetic lab nodes | `True` |
| `CELERY_TASK_ALWAYS_EAGER` | Synchronous task execution for monolithic dynos | `True` |

---

## 💻 Local Development Setup

### 1. Clone & Setup Virtual Environment
```bash
git clone https://github.com/aribanaz11/Network-Monitoring-Web-App.git
cd Network-Monitoring-Web-App

# Create and activate virtual environment
python -m venv backend/.venv
# Windows:
backend\.venv\Scripts\activate
# Linux/macOS:
source backend/.venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Database Migrations & Initial Data Seeding
```bash
python backend/manage.py migrate
python backend/manage.py seed_network_demo
```

### 3. Run Development Server
```bash
# Start Django Server (Port 8000)
python backend/manage.py runserver 127.0.0.1:8000
```
Open **[http://localhost:8000](http://localhost:8000)** in your browser.

---

## 🧪 Automated Testing

NetWatch includes a comprehensive 40-test automated test suite covering all critical network monitoring edge cases:

```bash
pytest backend/tests -v
```

```text
============================= 40 passed in 48.39s =============================
```

- `test_state_machine.py`: 5-State lifecycle transitions, failure & recovery hysteresis.
- `test_deduplication.py`: Alert storm suppression and incident auto-resolution.
- `test_tcp_observability.py`: TCP multi-port scan, Liveness/Readiness health probes, RFC 7807 error format.
- `test_icmp.py`: Real ICMP socket pings and simulated latency/loss calculation.
- `test_snmp.py`: SNMP v2c/v3 telemetry polling and OID walking.
- `test_ssh.py`: Whitelisted command execution and Fernet credential decryption.
- `test_tasks.py`: Asynchronous Celery workers and 3-state Circuit Breakers.
- `test_events.py`: Kafka topic routing and sliding-window outage anomaly detection.
- `test_auth.py`: JWT authentication, token blacklist, and 3-Tier RBAC.
