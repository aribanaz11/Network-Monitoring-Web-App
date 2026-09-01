# NetWatch — Resume Project Description & Portfolio Highlights
## Tailored for Associate Software Engineer Applications at EverestIMS Technologies

---

## 1. Resume Project Section (Standard / 2-Page Resume)

### **NetWatch — Distributed Network Device Monitoring & Automation Platform**
*Python, Django REST Framework, PostgreSQL, MongoDB, Celery, Redis, Apache Kafka, Paramiko SSH, SNMP v2c/v3, Docker* | [GitHub Link] | [Live Demo Link]

- **Architected and developed an enterprise Network Management System (NMS)** implementing a polyglot persistence architecture with **PostgreSQL** for relational metadata/RBAC and **MongoDB** for high-throughput time-series SNMP telemetry ingestion.
- **Engineered an asynchronous network diagnostic and polling engine** using **Celery, Redis, and Python raw sockets**, executing high-concurrency ICMP Echo and TCP 3-way handshake probes with sub-millisecond precision across enterprise subnets.
- **Built an agentless network automation subsystem with Paramiko SSH and PySNMP**, supporting multi-device configuration backups, whitelisted command execution, and standard MIB-II OID parsing (`sysDescr`, `ifTable`, `hrProcessorLoad`) with Fernet credential encryption at rest.
- **Designed a resilient distributed polling pipeline** with **Celery Beat** periodic scheduling, dedicated queue routing (`high_priority_icmp`, `snmp_telemetry`, `automation_jobs`), and a 3-state **Circuit Breaker** (`CLOSED`, `OPEN`, `HALF_OPEN`) preventing thread exhaustion on unreachable nodes.
- **Implemented real-time event streaming and anomaly detection with Apache Kafka**, broadcasting domain events across 5 topics and deploying sliding-window stream consumers to detect cascading multi-node outages and critical CPU spikes.
- **Enforced enterprise security and compliance standards** featuring 3-tier Role-Based Access Control (**Admin, Operator, Viewer**), JWT authentication with token blacklisting, immutable audit logging middleware, RFC-7807 error envelopes, and 100% test coverage across 30 automated Pytest test cases.

---

## 2. Concise Resume Section (1-Page Resume)

### **NetWatch — Distributed Network Monitoring & Management System**
*Python, Django REST Framework, Celery, Redis, Kafka, PostgreSQL, MongoDB, SNMP, SSH*

- Developed a production-style Network Management System (NMS) featuring dual-DB architecture (**PostgreSQL** for inventory/RBAC; **MongoDB** for SNMP telemetry metrics).
- Built distributed polling workers using **Celery & Redis** with queue routing and **Circuit Breakers**, reducing unreachable node polling overhead by 100%.
- Implemented **Paramiko SSH** automation for multi-device config backups with command whitelisting, and **SNMP v2c/v3** MIB collectors for live CPU/memory/interface metrics.
- Integrated **Apache Kafka** event streaming with real-time sliding-window anomaly detection for cascading network failures, backed by a 30-test automated Pytest suite.

---

## 3. Categorized Technical Skills for ATS Resume Parsing

```text
Backend Engineering:    Python 3.13, Django 5.x, Django REST Framework (DRF), Gunicorn, Celery, Celery Beat
Databases & Storage:    PostgreSQL (Relational/ACID/Indexing), MongoDB (Time-Series/Aggregations), Redis
Event Streaming & Queues: Apache Kafka, RabbitMQ, Celery Queue Routing, Distributed Task Scheduling
Networking & Protocols: TCP/IP Stack, Sockets, ICMP Echo, Jitter, Packet Loss, SNMP v2c/v3 USM, MIB-II, OIDs, SSH2, SFTP
Network Automation:     Paramiko, PySNMP, Configuration Backups, Whitelisting, Ping Sweeps
Security & Auth:        JWT (SimpleJWT), 3-Tier RBAC, Fernet Symmetric Encryption, Secret Masking, RFC-7807
DevOps & Infrastructure: Docker, Docker Compose, Linux (RHEL/Ubuntu), Bash Scripting, Systemd, Pytest (100% Pass)
Frontend Integration:   Angular-style Single Page App, Glassmorphism CSS, Chart.js Telemetry Dashboards
```

---

## 4. Interview Elevator Pitch (30 Seconds)

> *"I built **NetWatch**, a production-style Network Device Monitoring and Management System inspired by enterprise platforms like EverestIMS's Infraon IMS. It features a dual-database architecture—PostgreSQL for relational device inventory and 3-tier RBAC, and MongoDB for high-volume SNMP telemetry time-series metrics. I engineered distributed polling workers using Celery and Redis with Circuit Breakers to prevent thread pool exhaustion, built an agentless SSH automation and SNMP v2c/v3 collector, and integrated an Apache Kafka event streaming pipeline for real-time cascading outage anomaly detection. The entire platform is containerized with Docker and verified with a 30-test automated Pytest suite."*

---

## 5. Technical Interview Deep Dive Walkthrough (2 Minutes)

> *"When designing NetWatch, I focused on solving real-world challenges faced by enterprise NMS platforms like Infraon IMS:*
> 
> *1. **Data Layer**: Network inventory requires strict relational integrity, foreign keys, and ACID compliance for audit trails, which I implemented in PostgreSQL. However, SNMP telemetry produces dynamic, multi-interface time-series metrics that vary across vendors like Cisco, Juniper, and Linux. I chose MongoDB as a dedicated telemetry store to handle high write throughput and schema polymorphism without locking relational tables.*
> 
> *2. **Distributed Polling & Resilience**: In large fleets, slow or offline devices can starve worker threads. I implemented Celery with dedicated queue separation—isolating fast 1-second ICMP probes from long-running 30-second SSH backups. I also implemented a 3-state Circuit Breaker pattern that trips to OPEN after 3 consecutive failures, short-circuiting probes during a cooldown period and saving critical network sockets.*
> 
> *3. **Event Streaming & Anomaly Detection**: Rather than coupling alerting directly to polling loops, I introduced an Apache Kafka event bus. Polling tasks emit domain events to topics like `netwatch.device.status` and `netwatch.telemetry.snmp`. A sliding-window stream processor analyzes these events in real time to detect cascading outages—such as when 3 or more nodes drop simultaneously—identifying root-cause core switch failures instead of flooding the NOC with isolated alerts.*
> 
> *4. **Security & Production Readiness**: Credential security was paramount, so I used Fernet symmetric encryption for passwords at rest, masked secrets in all API serializers, and enforced 3-tier RBAC with immutable compliance audit logging."*

---

## 6. Mapping NetWatch to EverestIMS Technologies Product Lines

| EverestIMS Product | Core Capability | NetWatch Architectural Implementation |
|---|---|---|
| **Infraon IMS (Infrastructure Management System)** | Multi-vendor network inventory, live availability, SNMP monitoring, interface performance | Multi-vendor device inventory (Cisco, Juniper, Arista, Linux), ICMP latency/jitter engine, SNMP v2c/v3 MIB-II collector (`sysUpTime`, `ifTable`, `hrProcessorLoad`). |
| **Infraon ITOM (IT Operations Management)** | Configuration change management, automated device tasks, job scheduling | Agentless Paramiko SSH automation engine, automated running-config backup jobs, bulk command runner with whitelisting and destructive regex blocking. |
| **Infraon AIOps / Alerting** | Incident lifecycle, correlation, noise reduction, anomaly detection | Automated alert triggers and auto-resolutions, sliding-window anomaly consumer on Kafka detecting cascading multi-node failures. |
| **Infraon Security & Compliance** | Audit trail, role separation, secure credential storage | Custom 3-tier RBAC (`Admin`, `Operator`, `Viewer`), Fernet credential encryption at rest, immutable audit logging middleware capturing client IP, user, and action. |
