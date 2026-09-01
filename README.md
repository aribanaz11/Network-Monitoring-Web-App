# NetWatch — Distributed Network Device Monitoring & Management System

[![Python 3.13](https://img.shields.io/badge/Python-3.13-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Django 5.1](https://img.shields.io/badge/Django-5.1-green.svg?logo=django&logoColor=white)](https://www.djangoproject.com/)
[![DRF](https://img.shields.io/badge/DRF-3.15-red.svg)](https://www.django-rest-framework.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue.svg?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![MongoDB](https://img.shields.io/badge/MongoDB-7.0-green.svg?logo=mongodb&logoColor=white)](https://www.mongodb.com/)
[![Celery](https://img.shields.io/badge/Celery-5.4-brightgreen.svg?logo=celery&logoColor=white)](https://docs.celeryq.dev/)
[![Redis](https://img.shields.io/badge/Redis-7.2-red.svg?logo=redis&logoColor=white)](https://redis.io/)
[![Apache Kafka](https://img.shields.io/badge/Apache_Kafka-3.7-black.svg?logo=apachekafka&logoColor=white)](https://kafka.apache.org/)
[![Pytest](https://img.shields.io/badge/Tests-30%2F30%20Passed%20(100%25)-success.svg)](https://docs.pytest.org/)
[![Security](https://img.shields.io/badge/Fernet-Encrypted_Credentials-blueviolet.svg)](https://cryptography.io/)

> **NetWatch** is a production-style, distributed Network Device Monitoring & Management System (NMS) engineered specifically as an interview-ready portfolio system for an **Associate Software Engineer position at EverestIMS Technologies** (aligned with enterprise platforms like **Infraon IMS**, **ITOM**, and **AIOps**).

---

## 1. System Architecture Blueprint

```
                                  +-------------------------------------------------------------+
                                  |                 NetWatch Glassmorphism SPA                  |
                                  | (Dashboard, Live Telemetry, SSH Console, SNMP, Stream Feed) |
                                  +------------------------------+------------------------------+
                                                                 |
                                                                 | REST / JSON (JWT Auth & RBAC)
                                                                 v
                                  +-------------------------------------------------------------+
                                  |              Django 5 + Django REST Framework               |
                                  | ├── 3-Tier RBAC (Admin, Operator, Viewer)                   |
                                  | ├── RFC-7807 Standardized Exception Handling                |
                                  | ├── Fernet Symmetric Credential Encryption                  |
                                  | └── Immutable Compliance Audit Logging Middleware           |
                                  +--------+---------------------+---------------------+--------+
                                           |                     |                     |
                  +------------------------+                     |                     +------------------------+
                  v                                              v                                              v
+-----------------------------------+  +-----------------------------------+  +-----------------------------------+
|        PostgreSQL Database        |  |     MongoDB Telemetry Store       |  |          Redis Message Broker     |
| (Relational Inventory, RBAC Users,|  | (Polymorphic Time-Series Metrics, |  | (Celery Worker Task Queues &      |
|  Check Logs, Incidents, Audit)    |  |  SNMP MIB Snapshots, Interfaces)  |  |  Distributed Circuit Breaker Locks|
+-----------------------------------+  +-----------------------------------+  +-----------------+-----------------+
                                                         ^                                      |
                                                         |                                      | Task Routing
                                                         +----------------------+               v
                                                                                |  +----------------------------+
                                                                                |  |      Celery Beat (30s)     |
                                                                                |  | (Fleet Polling Coordinator)|
                                                                                |  +-------------+--------------+
                                                                                |                |
                                        +---------------------------------------+----------------+---------------------------------------+
                                        |                                                        |                                       |
                                        v                                                        v                                       v
                     +--------------------------------------+                 +--------------------------------------+                 +--------------------------------------+
                     |  Worker: high_priority_icmp          |                 |  Worker: snmp_telemetry              |                 |  Worker: automation_jobs             |
                     |  ├── Native ICMP Echo / Jitter Engine|                 |  ├── SNMP v2c / v3 USM Collector     |                 |  ├── Paramiko SSH Automation Engine  |
                     |  ├── Circuit Breaker (CLOSED/OPEN)   |                 |  ├── MIB-II OID Ingestion            |                 |  ├── Whitelisted Command Runner      |
                     |  └── Auto-Incident Trigger/Resolution|                 |  └── Threshold Alert Evaluation      |                 |  └── Multi-Device Config Backup      |
                     +------------------+-------------------+                 +------------------+-------------------+                 +------------------+-------------------+
                                        |                                                        |                                                        |
                                        +--------------------------------------------------------+--------------------------------------------------------+
                                                                                                 |
                                                                                                 | Broadcasts Domain Events
                                                                                                 v
                                                                              +------------------------------------+
                                                                              |       Apache Kafka Event Bus       |
                                                                              | ├── netwatch.device.status         |
                                                                              | ├── netwatch.alert.lifecycle       |
                                                                              | ├── netwatch.telemetry.snmp        |
                                                                              | ├── netwatch.automation.jobs       |
                                                                              | └── netwatch.security.audit        |
                                                                              +------------------+-----------------+
                                                                                                 |
                                                                                                 v
                                                                              +------------------------------------+
                                                                              |      Event Stream Processor        |
                                                                              | ├── Sliding Window Aggregation     |
                                                                              | ├── Cascading Outage Detection     |
                                                                              | └── Real-Time Dashboard Stream     |
                                                                              +------------------------------------+
```

---

## 2. Core Architectural Highlights & EverestIMS Alignment

| Component | Technical Implementation | EverestIMS Alignment (Infraon IMS/ITOM/AIOps) |
|---|---|---|
| **Polyglot Persistence** | **PostgreSQL** for relational metadata/RBAC + **MongoDB** for high-volume time-series SNMP metrics. | Matches Infraon's dual storage strategy for device inventory vs high-frequency telemetry metrics. |
| **Network Diagnostics** | Raw ICMP Echo engine, Round Trip Time, Jitter ($\Delta \text{latency}$), and TCP 3-Way Handshake port prober. | Core availability monitoring engine for routers, switches, servers, and firewalls. |
| **Agentless Automation** | **Paramiko SSH** engine with strict command whitelisting and destructive regex blocking (`rm -rf`, `reboot`, `erase`). | Matches Infraon ITOM configuration backup, compliance verification, and bulk execution. |
| **SNMP Telemetry Engine** | SNMP v2c and SNMP v3 USM (`AuthPriv`/`AuthNoPriv`) collecting standard MIB-II OIDs (`sysUpTime`, `ifTable`, `hrProcessorLoad`). | Core metric collector for network bandwidth, CPU load, and interface status. |
| **Distributed Task Processing** | **Celery & Redis** with queue routing (`high_priority_icmp`, `snmp_telemetry`, `automation_jobs`, `default`) and Celery Beat scheduler. | Enterprise horizontal scaling to poll tens of thousands of nodes every 30-60 seconds. |
| **Resilience & Fault Tolerance** | 3-State **Circuit Breaker** (`CLOSED`, `OPEN`, `HALF_OPEN`) with cooldown timers to prevent thread starvation on unreachable nodes. | Prevents cascading polling thread pool exhaustion during major network outages. |
| **Event Streaming & Anomaly Detection** | **Apache Kafka** event bus broadcasting across 5 topics with a sliding-window stream processor detecting cascading network outages. | Parallels Infraon AIOps event correlation, noise reduction, and root-cause analysis. |
| **Security & RBAC** | Custom 3-tier RBAC (`Admin`, `Operator`, `Viewer`), JWT auth, Fernet credential encryption at rest, and immutable audit logs. | Enterprise compliance, role separation, and zero-leak credential management. |

---

## 3. Technology Stack Justification

- **Python 3.13 & Django REST Framework**: Standard enterprise backend framework providing robust ORM, clean serialization, extensible middleware hooks, and RFC-7807 error envelopes.
- **PostgreSQL**: ACID-compliant relational store ensuring data integrity for device configurations, users, and audit logs with B-Tree indexes on `ip_address` and `status`.
- **MongoDB**: High-throughput document store with time-series collections and TTL auto-purging, ideal for dynamic, polymorphic vendor MIB tables.
- **Celery & Redis**: Asynchronous task queue decoupling HTTP requests from slow network I/O, supporting queue routing, rate limits, and retries with exponential backoff.
- **Apache Kafka**: Distributed event streaming platform decoupling telemetry producers from multiple downstream consumers (live UI, alerting engine, ML anomaly detector).
- **Paramiko & PySNMP**: Industry-standard, battle-tested Python libraries for agentless SSH automation and ASN.1/BER SNMP packet handling.

---

## 4. Quick Start & Local Installation

### Option A: Running with Docker Compose (Recommended)

```bash
# 1. Clone repository
git clone https://github.com/your-username/netwatch.git
cd netwatch

# 2. Launch complete multi-container stack
docker-compose up -d --build

# 3. Access Web Dashboard
open http://localhost:4200
```

### Option B: Native Local Setup (Development Environment)

```bash
# 1. Create and activate Python virtual environment
cd netwatch/backend
python -m venv .venv
# On Linux/macOS:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Apply database migrations & seed initial demo data
python manage.py migrate
python manage.py seed_network_demo

# 4. Start Django REST Backend Server
python manage.py runserver 127.0.0.1:8000

# 5. Start Celery Worker (in a separate terminal)
celery -A netwatch_core worker -l info -Q high_priority_icmp,snmp_telemetry,automation_jobs,default

# 6. Start Celery Beat Periodic Scheduler (in a separate terminal)
celery -A netwatch_core beat -l info

# 7. Start Kafka Stream Consumer Daemon (in a separate terminal)
python manage.py run_kafka_consumer --group netwatch-telemetry-consumer-group

# 8. Serve Frontend Glassmorphism SPA
cd ../frontend
python -m http.server 4200
```

---

## 5. Seeded Accounts & RBAC Roles

| Role | Email | Password | Permissions & Capabilities |
|---|---|---|---|
| **Admin** | `admin@netwatch.io` | `Admin@123456` | Full platform control: Add/Delete devices, manage user roles, full audit access. |
| **Operator** | `operator@netwatch.io` | `Operator@123456` | Operational control: Run SSH commands, SNMP polling, trigger diagnostics, manage alerts. |
| **Viewer** | `viewer@netwatch.io` | `Viewer@123456` | Read-only access: View dashboard, inspect device inventory, monitor event stream. |

---

## 6. REST API Reference

### Authentication & RBAC
- `POST /api/auth/login/`: Obtain JWT Access and Refresh tokens (includes user role claims).
- `POST /api/auth/token/refresh/`: Refresh an expired access token.
- `POST /api/auth/logout/`: Blacklist refresh token upon session termination.
- `GET  /api/auth/users/`: List users (`Admin` only).

### Device Inventory & Management
- `GET    /api/devices/`: List all devices with status and credential masking (All roles).
- `POST   /api/devices/`: Register a new device with Fernet credential encryption (`Admin` only).
- `GET    /api/devices/{id}/`: Retrieve detailed device configuration and metrics.
- `DELETE /api/devices/{id}/`: Delete device and associated logs (`Admin` only).
- `POST   /api/devices/{id}/ping/`: Trigger instant ICMP reachability check (`Operator`/`Admin`).
- `POST   /api/devices/{id}/ssh/`: Execute whitelisted SSH command (`Operator`/`Admin`).
- `GET    /api/devices/{id}/snmp/`: Poll live SNMP v2c/v3 MIB telemetry (`Operator`/`Admin`).
- `POST   /api/devices/{id}/snmp/walk/`: Execute SNMP subtree walk (`Operator`/`Admin`).

### Monitoring & Distributed Tasks
- `POST /api/monitoring/devices/{id}/tcp-check/`: Test TCP 3-way handshake on a specific port.
- `POST /api/monitoring/custom-ping/`: Ad-hoc ping sweep with custom packet count and timeout.
- `POST /api/monitoring/fleet/poll-now/`: Force immediate Celery fleet-wide polling sweep.
- `GET  /api/monitoring/tasks/status/`: Health diagnostics of Celery workers and queues.

### Kafka Event Streaming & Anomaly Detection
- `GET  /api/events/live/`: Query live stream events with topic and key filters.
- `GET  /api/events/stats/`: Broker health, throughput EPS, and consumer group anomaly stats.
- `POST /api/events/replay/`: Emit synthetic stream events for pipeline verification (`Operator`/`Admin`).

### Automation Jobs & Incidents
- `GET  /api/automation/jobs/`: List scheduled and completed multi-device automation jobs.
- `POST /api/automation/jobs/`: Create a new automation job (Config Backup / Command Runner).
- `POST /api/automation/jobs/{id}/run/`: Trigger asynchronous execution across target devices.
- `GET  /api/alerts/`: List network incident alerts with severity filters.
- `POST /api/alerts/{id}/acknowledge/`: Transition incident to `ACKNOWLEDGED`.
- `POST /api/alerts/{id}/resolve/`: Resolve and close incident.

---

## 7. Automated Test Suite Execution

NetWatch includes a comprehensive automated test suite verifying all 5 architectural phases:

```bash
cd netwatch/backend
pytest tests -v
```

### Test Suite Summary (30/30 Tests Passed — 100% Success Rate)

- `test_auth.py` (3 tests): JWT login, claims validation, 3-tier RBAC permission guards.
- `test_devices.py` (2 tests): Fernet credential encryption at rest, API secret masking.
- `test_icmp.py` (3 tests): Native ICMP engine, packet loss calculation, latency/jitter timers.
- `test_api_integration.py` (1 test): Complete end-to-end device creation and diagnostic flow.
- `test_ssh.py` (3 tests): Paramiko SSH execution, command whitelisting, destructive regex blocking.
- `test_snmp.py` (3 tests): SNMP v2c/v3 telemetry collector, MIB-II tree walk, MongoDB insertion.
- `test_automation.py` (1 test): Multi-device configuration backup job orchestration.
- `test_tasks.py` (7 tests): Celery async tasks, queue routing, Beat scheduler, Circuit Breaker state transitions (`CLOSED` $\rightarrow$ `OPEN` $\rightarrow$ `HALF_OPEN`).
- `test_events.py` (7 tests): Dual-mode Kafka event bus, topic routing, streaming anomaly detection (cascading outage correlation), and REST replay RBAC.

---

## 8. Interview Preparation & Candidate Resources

For detailed interview preparation and resume bullet points tailored specifically for EverestIMS Technologies, refer to the included companion guides:
- **`INTERVIEW_PREPARATION.md`**: 100+ deep technical questions and detailed answers across 22 core domains (Python, Django, PostgreSQL, MongoDB, Networking, SNMP, SSH, Celery, Kafka, Linux, System Design).
- **`RESUME_PROJECT_DESCRIPTION.md`**: ATS-friendly, metrics-driven STAR/XYZ bullet points and 30-second/2-minute interview elevator pitches.
- **`EVERESTIMS_JD_MAPPING.md`**: Detailed mapping connecting every job requirement from the EverestIMS Associate Software Engineer job description to concrete code in NetWatch.

---

## 9. Project Directory Structure

```text
netwatch/
├── backend/
│   ├── apps/
│   │   ├── accounts/          # 3-Tier RBAC, JWT Auth, Custom User Model
│   │   ├── alerts/            # Automated Incident Management & Auto-Resolution
│   │   ├── audit/             # Immutable Compliance Audit Logging Middleware
│   │   ├── automation/        # Multi-Device Config Backup & Job Execution
│   │   ├── devices/           # Device Inventory & Fernet Credential Encryption
│   │   ├── events/            # Kafka Event Bus, Topics & Stream Anomaly Processor
│   │   ├── monitoring/        # Celery Workers, Beat Scheduler, Fleet Poller
│   │   └── network_engine/    # Raw ICMP, TCP Handshake, Paramiko SSH, PySNMP & Circuit Breaker
│   ├── netwatch_core/         # Django Settings, Dual-DB (PG/Mongo), URL Routing, Celery App
│   ├── tests/                 # 30 Comprehensive Pytest Automated Test Cases
│   ├── manage.py
│   ├── pytest.ini
│   └── requirements.txt
├── frontend/
│   ├── index.html             # Responsive Dark Glassmorphism Web Client
│   └── src/
│       ├── app.js             # Reactive Frontend State & REST/Event Controllers
│       └── styles.css         # Custom Enterprise CSS Design System
├── scripts/
│   ├── setup_linux.sh         # Linux Automated Installation & Environment Provisioner
│   └── system_diagnostics.sh  # Linux System Health & Network Diagnostic Script
├── docker-compose.yml         # Multi-Container Orchestration Topology
├── INTERVIEW_PREPARATION.md   # 100+ Technical Interview Questions & Answers
├── RESUME_PROJECT_DESCRIPTION.md # ATS Resume Bullet Points & Elevator Pitches
├── EVERESTIMS_JD_MAPPING.md   # EverestIMS Technologies JD Skill Alignment Matrix
└── README.md                  # Master System Documentation
```

---

## 10. License & Author

- **Project**: NetWatch Enterprise Network Device Monitoring & Management System
- **Author**: Associate Software Engineer Candidate (Prepared for EverestIMS Technologies)
- **License**: MIT License
