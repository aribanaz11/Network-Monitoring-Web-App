# 🌐 NetWatch — Network Monitoring & Management Web App

> A full-stack web application for monitoring network devices, running real-time latency diagnostics, polling SNMP telemetry, and executing secure SSH automation from a unified dashboard.

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Visit%20Website-22c55e?style=for-the-badge&logo=railway)](https://web-production-fb047f.up.railway.app/)
[![Python](https://img.shields.io/badge/Python-3.12-38bdf8?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.1-10b981?style=for-the-badge&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![License](https://img.shields.io/badge/License-MIT-amber?style=for-the-badge)](LICENSE)

---

## 🔗 Live Application & Demo Access

You can test the deployed application directly in your browser:

👉 **[https://web-production-fb047f.up.railway.app/](https://web-production-fb047f.up.railway.app/)**

### 👤 Test Accounts (Pre-configured)

I've set up three test accounts with different permission levels so you can explore the app right away:

| Role | Username | Password | What you can do |
|---|---|---|---|
| **Admin** | `admin` | `Admin@123456` | Full access: Add/edit devices, run SSH commands, access Django admin |
| **Operator** | `operator` | `Operator@123456` | Operations: Run ping/TCP diagnostics, view telemetry, execute safe commands |
| **Viewer** | `viewer` | `Viewer@123456` | Read-only: View dashboard, device inventory, and audit logs |

- **Django Admin**: [https://web-production-fb047f.up.railway.app/admin/](https://web-production-fb047f.up.railway.app/admin/)
- **Health Check Endpoint**: [https://web-production-fb047f.up.railway.app/api/health/](https://web-production-fb047f.up.railway.app/api/health/)

---

## 💡 Why I Built This

Managing and monitoring network infrastructure often requires switching between separate tools for ping sweeps, SNMP stats, and SSH sessions. 

I built **NetWatch** to bring these core networking operations into a single, responsive web platform with:
- **Instant visibility**: See what's online, offline, or experiencing latency spikes.
- **Interactive diagnostics**: Test ICMP reachability and TCP port connectivity directly from the browser.
- **Safe remote management**: Run whitelisted diagnostic commands over SSH without sharing raw device passwords.
- **Smart alert management**: Group related device failures to prevent alert fatigue.

---

## 🎯 What's Inside

### 1. Real-Time Telemetry Dashboard
- Live ICMP response time charts powered by Chart.js.
- Device availability stats across routers, switches, firewalls, and servers.
- Summary of active network incidents with severity badges.

### 2. Device Inventory & State Machine
- Manage network nodes with hostnames, IP addresses, vendor types, and locations.
- Deterministic 5-state lifecycle (`Online`, `Offline`, `Degraded`, `Discovered`, `Maintenance`).
- Failure and recovery thresholds to avoid false alarms from temporary packet drops.

### 3. Web-Based SSH Terminal
- Built on Paramiko to connect securely to network equipment.
- Device credentials encrypted at rest using AES-CBC (Fernet).
- Command whitelisting for safe operations (`show ip int brief`, `uname -a`, `uptime`, `df -h`).
- Harmful commands (`rm -rf`, `reboot`, `erase`) are blocked automatically.

### 4. SNMP Telemetry Explorer
- Queries standard MIB OIDs (`sysDescr`, CPU load, memory pool).
- Monitors interface traffic counters (`ifInOctets` / `ifOutOctets`).

### 5. Low-Level Diagnostic Suite
- Sub-second raw ICMP socket pinging with packet count and timeout options.
- TCP 3-way handshake verification for services (HTTP, SSH, SNMP ports).

### 6. Security & Audit Logging
- Role-Based Access Control (RBAC) enforced with JWT authentication.
- Every login, device change, and SSH command is logged to an immutable audit table.

---

## 🏗️ How It Works (Tech Stack)

- **Frontend**: Clean Single Page Application (SPA) built with Vanilla JavaScript, semantic HTML5, and responsive CSS (no bulky framework dependencies).
- **Backend**: Django 5.1 and Django REST Framework for clean, documented API endpoints.
- **Database**: PostgreSQL (production) with automatic SQLite3 fallback (for local development).
- **Security**: Symmetric AES encryption (Fernet) for stored credentials, JWT tokens with blacklist rotation, and CORS protection.
- **Task Handling**: Celery-ready architecture for background polling.

---

## 💻 Running It Locally

If you want to run the project on your machine:

### Prerequisites
- Python 3.10+ installed
- Git

### Quick Setup

```bash
# 1. Clone the repository
git clone https://github.com/aribanaz11/Network-Monitoring-Web-App.git
cd Network-Monitoring-Web-App

# 2. Create and activate a virtual environment
python -m venv .venv

# On Linux/macOS:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up database & seed demo devices
python backend/manage.py migrate
python backend/manage.py seed_network_demo

# 5. Start the server
python backend/manage.py runserver 127.0.0.1:8000
```

Open **[http://localhost:8000](http://localhost:8000)** in your browser and log in with `admin` / `Admin@123456`.

---

## 🧪 Testing

The repository includes a comprehensive 40-test test suite covering all core functions:

```bash
pytest backend/tests -v
```

All tests run locally in memory without needing live network hardware.

---

## 📜 License

This project is open source and available under the [MIT License](LICENSE).
