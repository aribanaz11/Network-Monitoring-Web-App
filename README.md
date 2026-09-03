# 🌐 NetWatch — Network Monitoring & Management Web App

> A full-stack web application for monitoring network devices, running real-time latency diagnostics, polling SNMP telemetry, and executing secure SSH automation from a unified dashboard.

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Visit%20Website-22c55e?style=for-the-badge&logo=railway)](https://web-production-fb047f.up.railway.app/)
[![Python](https://img.shields.io/badge/Python-3.12-38bdf8?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.1-10b981?style=for-the-badge&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![License](https://img.shields.io/badge/License-MIT-amber?style=for-the-badge)](LICENSE)

---

## 🔗 Live Application

Explore the deployed application in production:

👉 **[https://web-production-fb047f.up.railway.app/](https://web-production-fb047f.up.railway.app/)**

- **Django Admin Portal**: [https://web-production-fb047f.up.railway.app/admin/](https://web-production-fb047f.up.railway.app/admin/)
- **Health Check Endpoint**: [https://web-production-fb047f.up.railway.app/api/health/](https://web-production-fb047f.up.railway.app/api/health/)

### 👤 Role-Based Access Control (RBAC)

NetWatch supports 3-tier Role-Based Access Control enforced through signed JWT authentication:

| Role | Access Level | Capabilities |
|---|---|---|
| **Administrator** | Full Control | Add, edit, and delete network devices; run SSH automation; access Django Admin |
| **NOC Operator** | Operations | Execute ICMP/TCP diagnostics; poll SNMP telemetry; run whitelisted terminal commands |
| **Audit Viewer** | Read-Only | Inspect telemetry charts, view device inventory, and review immutable audit logs |

---

## 💡 Why I Built This

Managing and monitoring network infrastructure often requires switching between separate tools for ping sweeps, SNMP stats, and SSH sessions. 

I built **NetWatch** to bring these core networking operations into a single, responsive web platform with:
- **Instant visibility**: See what's online, offline, or experiencing latency spikes.
- **Interactive diagnostics**: Test ICMP reachability and TCP port connectivity directly from the browser.
- **Safe remote management**: Run whitelisted diagnostic commands over SSH with credentials encrypted at rest.
- **Smart alert management**: Group related device failures into single actionable incidents to eliminate alert storms.

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
- TCP 3-way handshake verification for critical service ports.

### 6. Security & Audit Logging
- Role-Based Access Control (RBAC) enforced with JWT authentication.
- Every login, device change, and SSH command is logged to an immutable audit table with automatic credential redaction.

---
## 💻 Running Locally

### Prerequisites
- Python 3.10+
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

# 4. Configure your environment
cp .env.example .env

# 5. Run migrations & seed demo devices
python backend/manage.py migrate
python backend/manage.py seed_network_demo

# 6. Create your administrator account
python backend/manage.py createsuperuser

# 7. Start the development server
python backend/manage.py runserver 127.0.0.1:8000
```

Open **[http://localhost:8000](http://localhost:8000)** in your browser and log in with your newly created credentials.

---

## 🧪 Testing

The repository includes a comprehensive 40-test test suite covering all core functions:

```bash
pytest
```

All 40 tests execute in isolated memory environments in seconds without external network dependencies.

---

## 📜 License

This project is open source and available under the [MIT License](LICENSE).
