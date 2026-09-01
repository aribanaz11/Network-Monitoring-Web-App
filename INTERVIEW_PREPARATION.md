# NetWatch — Master Technical Interview Preparation Guide
## Prepared for EverestIMS Technologies — Associate Software Engineer Candidate

This comprehensive guide contains **100+ deep, rigorous technical questions and answers across 22 core domains** covered in the **NetWatch** platform. It connects computer science theory, systems programming, and network engineering directly to real-world code implementations in NetWatch and EverestIMS Technologies' enterprise product suite (Infraon IMS, ITOM, AIOps).

---

# Table of Contents
1. [Python Core & Internals](#1-python-core--internals)
2. [Python Advanced Language Features](#2-python-advanced-language-features)
3. [Python Concurrency & Parallelism Models](#3-python-concurrency--parallelism-models)
4. [Django Framework Internals](#4-django-framework-internals)
5. [Django REST Framework (DRF) & API Architecture](#5-django-rest-framework-drf--api-architecture)
6. [PostgreSQL & Relational Data Engineering](#6-postgresql--relational-data-engineering)
7. [MongoDB & Telemetry Time-Series Storage](#7-mongodb--telemetry-time-series-storage)
8. [Dual-Database Strategy & Polyglot Persistence](#8-dual-database-strategy--polyglot-persistence)
9. [Networking Fundamentals & TCP/IP Protocol Suite](#9-networking-fundamentals--tcpip-protocol-suite)
10. [Transport Layer & Low-Level Socket Programming](#10-transport-layer--low-level-socket-programming)
11. [ICMP Engine & Network Diagnostics](#11-icmp-engine--network-diagnostics)
12. [SNMP Architecture (v2c / v3 USM) & MIB Parsing](#12-snmp-architecture-v2c--v3-usm--mib-parsing)
13. [SSH Automation & Paramiko Engineering](#13-ssh-automation--paramiko-engineering)
14. [Distributed Task Queues (Celery & Redis/RabbitMQ)](#14-distributed-task-queues-celery--redisrabbitmq)
15. [Periodic Scheduling & High-Frequency Fleet Polling](#15-periodic-scheduling--high-frequency-fleet-polling)
16. [Resilience Engineering & Circuit Breaker Pattern](#16-resilience-engineering--circuit-breaker-pattern)
17. [Event Streaming & Apache Kafka Architecture](#17-event-streaming--apache-kafka-architecture)
18. [Real-Time Stream Processing & Anomaly Detection](#18-real-time-stream-processing--anomaly-detection)
19. [Enterprise Security, Cryptography & Audit Trails](#19-enterprise-security-cryptography--audit-trails)
20. [Linux Systems Programming & Network Utilities](#20-linux-systems-programming--network-utilities)
21. [DevOps, Docker Containerization & Testing](#21-devops-docker-containerization--testing)
22. [EverestIMS Product Alignment & System Design Scenarios](#22-everestims-product-alignment--system-design-scenarios)

---

# 1. Python Core & Internals

### Q1.1: How does Python manage memory internally, and what is the difference between reference counting and the cyclic garbage collector?
**Answer**:
Python (specifically CPython) employs a two-tier memory management system:
1. **Reference Counting**: Every Python object (`PyObject`) contains an internal counter (`ob_refcnt`). When an object is referenced (assigned to a variable, passed to a function, appended to a list), `ob_refcnt` is incremented. When a reference goes out of scope or is deleted (`del`), `ob_refcnt` is decremented. When `ob_refcnt == 0`, the memory is immediately deallocated back to Python's memory allocator (PyMalloc).
2. **Generational Cyclic Garbage Collector (GC)**: Reference counting alone cannot detect circular references (e.g., Object A references Object B, and Object B references Object A, but both are unreachable from the root scope). Python's cyclic GC runs periodically, tracking container objects (`list`, `dict`, `tuple`, custom class instances) across three generations (Gen 0, Gen 1, Gen 2). Objects surviving collection in Gen 0 are promoted to Gen 1, and so on. In NetWatch, we prevent memory leaks in the telemetry loop by ensuring transient socket objects and Paramiko sessions are explicitly closed within context managers.

### Q1.2: What is the Global Interpreter Lock (GIL), why does it exist in CPython, and how does NetWatch achieve multi-core CPU scaling?
**Answer**:
The GIL is a mutex that protects access to Python objects, preventing multiple native threads from executing Python bytecode simultaneously within a single CPython process. It exists because CPython's memory management is not thread-safe (preventing race conditions on reference counts).
- **CPU-bound vs I/O-bound**: For I/O-bound tasks (ICMP socket probing, SSH network waits, SNMP UDP round-trips), Python threads release the GIL while waiting on kernel I/O syscalls (`select`, `poll`, `epoll`).
- **Scaling in NetWatch**: Rather than running heavy CPU workloads inside the Django web thread, NetWatch uses **Celery worker processes with pre-fork pools** and an event-driven architecture. Each worker is an isolated operating system process with its own CPython interpreter, heap, and GIL, executing across multiple CPU cores in parallel.

### Q1.3: What is the difference between shallow copy and deep copy in Python, and where does this matter in NetWatch?
**Answer**:
- **Shallow Copy** (`copy.copy()` or slicing `[:]`): Creates a new outer container object, but inserts references to the objects found in the original. If a nested object is modified, both copies reflect the change.
- **Deep Copy** (`copy.deepcopy()`): Recursively creates a new container and clones every nested object within it.
- **In NetWatch**: When the `KafkaEventBus` processes streaming events with mutable dictionaries containing device metrics (`payload = {'interfaces': [...]}`), deep copies are dispatched to registered consumer handlers to prevent handler callbacks from mutating or corrupting the global event payload or ring buffer.

### Q1.4: Explain Python's Method Resolution Order (MRO) and the C3 Linearization algorithm.
**Answer**:
MRO determines the order in which Python searches for attributes and methods in class hierarchies supporting multiple inheritance. Python uses the **C3 Linearization** algorithm, which enforces three properties:
1. Children precede parents.
2. Order of parent classes listed in the class definition is preserved.
3. Monotonicity (if Class A precedes Class B in one subclass, it must precede Class B in all subclasses).
You can inspect MRO in Python via `ClassName.__mro__` or `ClassName.mro()`. In NetWatch, MRO is relevant in custom DRF permission classes and Django custom model managers where multiple mixins (`PermissionsMixin`, `BaseUserManager`) are composed.

### Q1.5: How do Python `*args` and `**kwargs` work under the hood, and how are dictionary unpackings handled?
**Answer**:
`*args` collects positional arguments into a `tuple`, while `**kwargs` collects named keyword arguments into a standard `dict`. When calling a function, `*iterable` unpacks elements into positional arguments, and `**dict` unpacks key-value pairs into keyword arguments. In NetWatch's `ParamikoSSHEngine` and `CircuitBreaker`, `*args` and `**kwargs` are used extensively in decorators and wrapper methods to transparently pass arbitrary parameters to probed target functions without altering their signatures.

---

# 2. Python Advanced Language Features

### Q2.1: How do Python Decorators work under the hood, and how do you preserve function metadata?
**Answer**:
A decorator is a callable that takes a function as an argument and returns a replacement callable (closure). Because the wrapper replaces the original function, properties like `__name__`, `__doc__`, and `__module__` are overwritten by the wrapper unless `@functools.wraps(func)` is applied.
In NetWatch, decorators are used for:
- Role-based view guards.
- Circuit breaker state evaluation.
- Execution latency timers (`@measure_latency`).

```python
import functools
import time

def measure_latency(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        duration_ms = (time.perf_counter() - start) * 1000.0
        return result, duration_ms
    return wrapper
```

### Q2.2: Explain Context Managers, the `__enter__` and `__exit__` lifecycle, and `contextlib.contextmanager`.
**Answer**:
Context managers guarantee deterministic resource acquisition and release (RAII pattern) via the `with` statement:
1. `__enter__()`: Executed before the block; its return value is bound to the `as` variable.
2. `__exit__(exc_type, exc_val, exc_tb)`: Executed after the block. If an exception occurred, `exc_type` contains the exception class. If `__exit__` returns `True`, the exception is suppressed; if `False` or `None`, the exception bubbles up.
In NetWatch's `ParamikoSSHEngine`, context managers ensure SSH channels and transport sessions are cleanly closed (`client.close()`) even if network timeouts, socket disconnections, or authentication errors occur.

### Q2.3: What are Generators, what is the `yield` keyword, and how do they optimize memory when processing network telemetry?
**Answer**:
A generator is a function containing the `yield` expression that returns an iterator object conforming to Python's iterator protocol (`__iter__()`, `__next__()`). When `yield` is encountered, execution is suspended, local state and instruction pointer are saved, and the value is returned to the caller.
- **Memory Optimization**: Unlike returning a complete list of 100,000 MIB metrics or log lines allocated upfront in RAM ($O(N)$ memory), a generator yields metrics lazily one item at a time ($O(1)$ memory).
- In NetWatch, when running SNMP subtree walks (`walk_oids`), OID bindings are yielded lazily as UDP response packets arrive, preventing memory spikes.

### Q2.4: What are `__slots__` in Python classes, and when should you use them?
**Answer**:
By default, Python class instances store attributes in a dynamic dictionary (`__dict__`). This allows adding arbitrary attributes at runtime, but introduces memory overhead (~150-200 bytes per instance). Defining `__slots__ = ('attr1', 'attr2')` instructs CPython to allocate a fixed-size array of attribute pointers inside the C struct instead of allocating a `__dict__`.
In high-throughput NMS engines processing hundreds of thousands of live network metric packets per minute, using `__slots__` on data transport objects reduces memory footprint by up to 60%.

---

# 3. Python Concurrency & Parallelism Models

### Q3.1: Compare `asyncio`, `threading`, `multiprocessing`, and `Celery`. When should each be chosen?
**Answer**:
| Model | Mechanism | Concurrency Type | Best For | Limitation |
|---|---|---|---|---|
| **`asyncio`** | Single-threaded event loop (`epoll`/`kqueue`), cooperative multitasking | Single process, non-blocking I/O | 10,000+ simultaneous slow network connections (WebSockets, async HTTP) | A single CPU-intensive or blocking synchronous call blocks the entire event loop. |
| **`threading`** | OS native threads scheduled by kernel | Preemptive multithreading (GIL-bound in Python) | I/O-bound tasks with legacy synchronous libraries (e.g. Paramiko, PySNMP) | Subject to GIL; true multi-core parallel execution cannot be achieved for CPU tasks. |
| **`multiprocessing`** | Separate OS processes, IPC via pipes/shared memory | True multi-core parallelism | CPU-intensive data transformations, parsing huge telemetry streams | Higher memory overhead (forking/spawning processes); serialization cost via `pickle`. |
| **`Celery`** | Distributed task queue across multiple server nodes via message broker | Distributed, fault-tolerant asynchronous execution | Background periodic jobs, fleet polling, alert workflows, long-running automation | Requires infrastructure (Redis/RabbitMQ); higher operational overhead. |

**NetWatch Design Decision**: NetWatch uses **Celery with Redis** for fleet orchestration because network monitoring jobs must survive server restarts, execute on distributed worker nodes across different network subnets, and support rate-limiting and circuit-breaking.

---

# 4. Django Framework Internals

### Q4.1: Trace the complete Django Request-Response Lifecycle from the moment an HTTP packet arrives at the server.
**Answer**:
1. **WSGI / ASGI Gateway**: Gunicorn or Uvicorn receives the HTTP request from Nginx/reverse proxy and translates it into a standard WSGI environment dictionary (`environ`).
2. **`WSGIHandler`**: Initializes `HttpRequest` instance and loads `ROOT_URLCONF`.
3. **Middleware Request Processing**: Runs through `MIDDLEWARE` list in top-down order (e.g., Security, Session, CORS, Authentication, Audit Logging).
4. **URL Routing & Resolver**: `URLResolver` matches request path against `urlpatterns` in `urls.py`, extracting URL kwargs and determining the target View/ViewSet.
5. **View Execution**: View processes request, executes business logic, invokes Model ORM or serializers, and returns `HttpResponse`.
6. **Middleware Response Processing**: Runs back through `MIDDLEWARE` in reverse order (bottom-up), applying headers, audit records, or exception transformations.
7. **WSGI Gateway Output**: Converts `HttpResponse` to HTTP bytes and transmits back to the network client.

### Q4.2: Explain Django Middleware architecture and describe NetWatch's custom `AuditLoggingMiddleware`.
**Answer**:
Django middleware is a framework of hooks into request/response processing implemented as a callable chain (`get_response`). Each middleware wrapper executes logic before and after calling the next layer.
In NetWatch, `AuditLoggingMiddleware` intercepts all state-modifying requests (`POST`, `PUT`, `PATCH`, `DELETE`), captures the authenticated user email, role, client IP, target endpoint, and execution status, and records an immutable log in the `AuditLog` table. It also sanitizes request payloads to ensure sensitive credentials (passwords, community strings) are masked before persistence.

```python
class AuditLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 1. Pre-view processing (extract client IP, user context)
        response = self.get_response(request)
        # 2. Post-view processing (record audit event for state mutations)
        if request.method in ['POST', 'PUT', 'PATCH', 'DELETE'] and request.user.is_authenticated:
            self._log_audit_trail(request, response)
        return response
```

### Q4.3: What is the N+1 Query Problem in Django ORM, and how do `select_related` and `prefetch_related` resolve it?
**Answer**:
- **N+1 Problem**: Occurs when querying a list of $N$ parent objects, and then accessing a related foreign key or many-to-many field in a loop. Django executes 1 initial query for the parents, plus $N$ additional database queries for each parent's child relation ($1 + N$ queries total), causing severe latency.
- **`select_related`**: Resolves single-valued relationships (`ForeignKey`, `OneToOneField`) by performing a single SQL `INNER JOIN` or `LEFT OUTER JOIN` in the initial query.
- **`prefetch_related`**: Resolves multi-valued relationships (`ManyToManyField`, reverse `ForeignKey`) by executing exactly 2 SQL queries: one for parents and one for children with `WHERE parent_id IN (...)`, joining them in Python memory.
- In NetWatch: When listing `Device` objects with their related `Alert` records and `AutomationJob` associations, we use `prefetch_related('alerts')` to avoid executing hundreds of database queries during dashboard loading.

---

# 5. Django REST Framework (DRF) & API Architecture

### Q5.1: How does NetWatch implement 3-Tier Role-Based Access Control (RBAC)?
**Answer**:
NetWatch implements custom DRF permission classes extending `BasePermission`:
- `IsAdminRole`: Grants full administrative control (device creation, deletion, user role assignment, full audit access).
- `IsOperatorRole`: Allows operators to trigger network diagnostics, run Paramiko SSH commands, execute SNMP walks, and acknowledge/resolve alerts.
- `IsViewerRole`: Read-only access to device statuses, telemetry charts, and incident dashboards; write operations return `403 Forbidden`.

```python
class IsOperatorRole(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.role in [UserRole.ADMIN, UserRole.OPERATOR]
```

### Q5.2: What is the RFC-7807 specification for Problem Details, and why is it implemented in NetWatch's custom exception handler?
**Answer**:
RFC-7807 defines a standardized JSON schema for HTTP API error responses, eliminating inconsistent error formatting across endpoints. NetWatch's `custom_exception_handler` catches all DRF and Django exceptions (`ValidationError`, `AuthenticationFailed`, `PermissionDenied`, `NotFound`, `Http404`), mapping them to a structured envelope:
```json
{
  "type": "https://netwatch.io/errors/permission-denied",
  "title": "Permission Denied",
  "status": 403,
  "detail": "Role 'VIEWER' is not authorized to trigger SSH automation commands.",
  "instance": "/api/devices/cead343e-a803/ssh/",
  "timestamp": "2026-09-01T10:57:54.775Z"
}
```

### Q5.3: How do JWT access and refresh tokens work, and how does NetWatch handle token blacklisting upon logout?
**Answer**:
1. **Access Token**: Short-lived (typically 15-60 minutes) cryptographically signed JSON object (HMAC-SHA256 or RSA) containing user claims (`user_id`, `email`, `role`, `exp`). The client sends it in the `Authorization: Bearer <token>` header. DRF validates the signature statelessly without querying the database on every request.
2. **Refresh Token**: Longer-lived (e.g. 7 days) token used exclusively against `POST /api/auth/token/refresh/` to issue a new access token.
3. **Blacklisting**: When a user logs out, the refresh token's unique ID (`jti` - JWT ID) is sent to `POST /api/auth/logout/` and saved to the `BlacklistedToken` database table, preventing any future access tokens from being generated from that refresh token.

---

# 6. PostgreSQL & Relational Data Engineering

### Q6.1: Explain ACID properties in PostgreSQL and provide examples from NetWatch.
**Answer**:
- **Atomicity**: All operations in a database transaction succeed or all roll back. In NetWatch, when a device is deleted, the device record, its encrypted credentials, and associated check logs are removed within an atomic `transaction.atomic()` block.
- **Consistency**: The database moves from one valid state to another, satisfying all schema constraints (`UNIQUE`, `FOREIGN KEY`, `CHECK`). NetWatch enforces unique IP addresses and unique user emails.
- **Isolation**: Concurrent transactions do not interfere with one another (PostgreSQL default: `Read Committed`).
- **Durability**: Once a transaction is committed, changes survive server crashes or power failures via PostgreSQL's Write-Ahead Log (WAL).

### Q6.2: What database indexes exist in NetWatch, and how do B-Tree indexes accelerate network queries?
**Answer**:
NetWatch defines B-Tree indexes on:
1. `Device.ip_address` (`unique=True`, `db_index=True`): Fast $O(\log N)$ lookup during ICMP polling and Celery task execution.
2. `Device.status` and `Device.device_type`: Filtering the inventory by state (`ONLINE`, `OFFLINE`) or type (`ROUTER`, `SWITCH`).
3. `AuditLog.timestamp` and `AuditLog.user_email`: Rapid compliance range queries.
**B-Tree Mechanism**: PostgreSQL B-Trees maintain a balanced tree of ordered keys. Instead of performing a sequential table scan ($O(N)$), index traversal reduces disk page reads to $O(\log N)$, essential when polling thousands of devices every 30 seconds.

---

# 7. MongoDB & Telemetry Time-Series Storage

### Q7.1: Why does NetWatch store SNMP telemetry and time-series metrics in MongoDB instead of PostgreSQL?
**Answer**:
1. **Dynamic / Polymorphic Schema**: Different network vendors (Cisco, Juniper, Arista, Linux) return vastly different MIB trees and interface tables. Storing varying interface counts, OID maps, and vendor-specific metrics in PostgreSQL requires complex schema migrations, EAV (Entity-Attribute-Value) anti-patterns, or unstructured JSONB columns lacking dedicated time-series indexing.
2. **High Ingestion Write Throughput**: MongoDB's memory-mapped storage engine (WiredTiger) handles high write volumes with document-level locking, ideal for storing thousands of SNMP metric snapshots per minute without locking relational tables.
3. **TTL (Time-To-Live) Collections**: MongoDB supports automatic data expiration (e.g. purging raw telemetry older than 90 days via `expireAfterSeconds` index), preventing database bloat without requiring cron purge scripts.

### Q7.2: How is PyMongo connection pooling configured in NetWatch?
**Answer**:
In `netwatch_core/mongo.py`, NetWatch maintains a singleton `MongoClient` instance initialized with:
- `maxPoolSize=50`: Allows up to 50 concurrent socket connections to MongoDB across Celery worker threads.
- `minPoolSize=5`: Keeps 5 warm connections active.
- `serverSelectionTimeoutMS=2000`: Fast-fails within 2 seconds if MongoDB is unreachable, allowing the application to gracefully fall back without blocking HTTP request threads.

---

# 8. Dual-Database Strategy & Polyglot Persistence

### Q8.1: Explain the Polyglot Persistence architecture in NetWatch and how data consistency is maintained between PostgreSQL and MongoDB.
**Answer**:
- **PostgreSQL**: Serves as the **Relational Source of Truth** for structured, relational, high-integrity entities (Users, RBAC Roles, Device Inventory, Credentials, Alert Incidents, Audit Logs).
- **MongoDB**: Serves as the **High-Volume Telemetry Store** for polymorphic, append-heavy metric time-series (CPU load, memory pools, interface octet counters).
- **Linking Key**: Every MongoDB telemetry document stores the device's PostgreSQL UUID (`device_id`).
- **Consistency Model**: Eventual consistency. The Django backend reads device metadata from PostgreSQL and fetches recent metric graphs from MongoDB. If MongoDB encounters a transient network partition, device management and ICMP monitoring continue uninterrupted (graceful degradation).

---

# 9. Networking Fundamentals & TCP/IP Protocol Suite

### Q9.1: Walk through the 7 layers of the OSI model and map NetWatch's operations to their respective layers.
**Answer**:
| OSI Layer | Protocol / Concept | NetWatch Implementation |
|---|---|---|
| **Layer 7 (Application)** | HTTP, SSH, SNMP, DNS | Django REST API, Paramiko SSH automation, SNMP v2c/v3 client |
| **Layer 6 (Presentation)** | SSL/TLS, ASN.1/BER | Fernet encryption, ASN.1 encoding in SNMP packets, JWT signing |
| **Layer 5 (Session)** | Sockets, NetBIOS | TCP socket connection sessions, SSH Transport channels |
| **Layer 4 (Transport)** | TCP, UDP | TCP 3-Way Handshake scanner (port 22/80/443), UDP socket for SNMP (port 161) |
| **Layer 3 (Network)** | IP, ICMP, Routing | Native ICMP Echo engine, IP address validation, packet TTL inspection |
| **Layer 2 (Data Link)** | Ethernet, MAC, ARP | Interface MAC table collection via SNMP MIB-II (`ifPhysAddress`) |
| **Layer 1 (Physical)** | Bits, Cabling, SFP | Interface status flags (`ifOperStatus`, `ifAdminStatus`) |

---

# 10. Transport Layer & Low-Level Socket Programming

### Q10.1: Explain the TCP 3-Way Handshake, TCP Flags (SYN, ACK, RST, FIN), and how NetWatch verifies service ports.
**Answer**:
- **Handshake Sequence**:
  1. **SYN**: Client sends a packet with `SYN=1` and an initial sequence number ($ISN_C$) to the target port.
  2. **SYN-ACK**: If the port is open and listening, the server responds with `SYN=1`, `ACK=1`, acknowledging $ISN_C + 1$ and sending its own sequence number ($ISN_S$).
  3. **ACK**: Client sends `ACK=1`, acknowledging $ISN_S + 1$. The TCP connection is now `ESTABLISHED`.
- **Port Closed**: If the port is closed, the server kernel immediately responds with a `RST` (Reset) packet.
- **Port Filtered (Firewall)**: The firewall drops the SYN packet silently; the client times out.
- **In NetWatch**: `apps/network_engine/icmp.py` implements a non-blocking TCP socket connect mechanism using Python's `socket` library to probe open management ports (SSH port 22, Telnet 23, HTTP 80, HTTPS 443) and measures the exact TCP handshake latency in milliseconds.

---

# 11. ICMP Engine & Network Diagnostics

### Q11.1: How does ICMP Echo Request and Reply work, and what is the difference between latency, packet loss, and jitter?
**Answer**:
- **ICMP (Internet Control Message Protocol)** operates directly on top of IP (IP Protocol 1).
- **Echo Request (Type 8, Code 0)**: Sent from client to target node with an identifier, sequence number, and timestamp payload.
- **Echo Reply (Type 0, Code 0)**: Sent back by target node with identical payload.
- **Key Metrics in NetWatch**:
  1. **Round Trip Time (Latency)**: Time difference $\Delta t = t_{\text{reply}} - t_{\text{request}}$ measured in milliseconds.
  2. **Packet Loss (%)**: $\frac{\text{Packets Sent} - \text{Packets Received}}{\text{Packets Sent}} \times 100$.
  3. **Jitter ($\text{ms}$)**: The statistical variance in latency between consecutive packets:
     $$\text{Jitter} = \frac{1}{N-1} \sum_{i=1}^{N-1} |RTT_{i+1} - RTT_i|$$
  In NetWatch, jitter is computed on multi-packet ping sweeps to detect network congestion or link flapping before full node failure occurs.

---

# 12. SNMP Architecture (v2c / v3 USM) & MIB Parsing

### Q12.1: Compare SNMP v1, v2c, and v3. Why is SNMP v3 required in enterprise networks?
**Answer**:
- **SNMP v1 / v2c**: Authenticates using plain-text "Community Strings" (e.g. `public`, `private`). Packets are unencrypted and transmitted in clear text over UDP port 161, making them vulnerable to packet sniffing, spoofing, and unauthorized device reconfiguration.
- **SNMP v3**: Introduces the **User-based Security Model (USM)** and View-based Access Control Model (VACM), providing:
  1. **Authentication (Auth)**: Verifies sender identity and packet integrity using cryptographic hashes (HMAC-MD5, HMAC-SHA1, HMAC-SHA256).
  2. **Privacy / Encryption (Priv)**: Encrypts the entire SNMP PDU payload using symmetric ciphers (DES, 3DES, AES-128, AES-256).
  3. **Replay Protection**: Timers and engine boots/engine time counters prevent replay attacks.
- **In NetWatch**: Supports both SNMP v2c and SNMP v3 USM (`AuthPriv`, `AuthNoPriv`, `NoAuthNoPriv`), storing encrypted credentials in PostgreSQL.

### Q12.2: Explain OIDs, MIBs, and SMI. List key standard MIB-II OIDs polled by NetWatch.
**Answer**:
- **SMI (Structure of Management Information)**: Defines the ASN.1 data types and rules for structuring network management information.
- **MIB (Management Information Base)**: A hierarchical, tree-structured database of manageable objects.
- **OID (Object Identifier)**: Dotted-decimal string identifying an exact node in the MIB tree.
- **Key Standard OIDs in NetWatch**:
  - `1.3.6.1.2.1.1.1.0` (`sysDescr`): Hardware, OS version, and firmware description.
  - `1.3.6.1.2.1.1.3.0` (`sysUpTime`): Time in hundredths of a second since device reboot.
  - `1.3.6.1.2.1.2.2.1` (`ifTable`): Interface table (names, operational status, speeds, byte counters).
  - `1.3.6.1.2.1.25.3.3.1.2` (`hrProcessorLoad`): Host resources CPU utilization per core.
  - `1.3.6.1.4.1.9.9.48.1.1.1.5` (`ciscoMemoryPoolUsed`): Cisco enterprise memory pool used bytes.

---

# 13. SSH Automation & Paramiko Engineering

### Q13.1: How does NetWatch prevent Remote Code Execution (RCE) and command injection in its SSH automation engine?
**Answer**:
NetWatch implements a multi-layer defense-in-depth model:
1. **Strict Command Whitelisting**: Only pre-approved, read-only diagnostic commands (`show version`, `show ip interface brief`, `show running-config`, `uname -a`, `df -h`, `uptime`) are permitted.
2. **Destructive Regex Blacklist**: Reject commands containing shell injection tokens (`|`, `;`, `&&`, `` ` ``, `$()`), path traversal (`..`), or destructive operations (`rm -rf`, `reboot`, `reload`, `erase`, `format`).
3. **RBAC Guard**: Only users with `ADMIN` or `OPERATOR` roles can dispatch SSH automation jobs.
4. **Immutable Audit Logging**: Every executed command, exit code, execution latency, and client IP is recorded in the PostgreSQL audit log.

```python
WHITELISTED_COMMANDS = {
    'show version', 'show ip interface brief', 'show interfaces',
    'show running-config', 'show ip route', 'uname -a', 'df -h', 'uptime'
}
FORBIDDEN_PATTERN = re.compile(r'(;|&&|\||`|\$\(|\brm\b|\breboot\b|\breload\b|\berase\b)', re.IGNORECASE)
```

---

# 14. Distributed Task Queues (Celery & Redis/RabbitMQ)

### Q14.1: Explain Celery architecture, task routing, worker queues, and why queue separation is critical in NetWatch.
**Answer**:
- **Architecture**: Celery uses a message broker (Redis or RabbitMQ) to distribute tasks asynchronously to worker pools.
- **Queue Separation in NetWatch**:
  1. `high_priority_icmp`: Dedicated workers polling fast ICMP reachability checks (1-2s timeouts). High concurrency, zero blocking.
  2. `snmp_telemetry`: Workers handling MIB-II UDP queries and MongoDB insertions.
  3. `automation_jobs`: Long-running Paramiko SSH commands and multi-device config backups (up to 30s timeouts).
  4. `default`: General housekeeping, alert notifications, and audit processing.
- **Why Separation Matters**: If long-running SSH commands ran on the same queue as ICMP probes, slow or unresponsive routers would saturate all Celery worker threads, causing ICMP reachability polling to stall and producing false-positive network outage alerts across the fleet.

---

# 15. Periodic Scheduling & High-Frequency Fleet Polling

### Q15.1: How does Celery Beat coordinate fleet polling without causing the "Thundering Herd" problem?
**Answer**:
1. **Coordinator Task (`run_periodic_fleet_polling_task`)**: Triggered every 30 seconds by Celery Beat.
2. **Asynchronous Task Fan-Out**: Instead of executing polls sequentially in a loop, the coordinator iterates over active devices in PostgreSQL and dispatches individual asynchronous Celery tasks (`poll_device_icmp_task.delay(device.id)` and `poll_device_snmp_task.delay(device.id)`).
3. **Queue Distribution**: Tasks are distributed across worker processes via the broker.
4. **Jitter / Staggering**: Tasks incorporate minor millisecond random jitter to prevent all ICMP packets from hitting the network switch at the exact same microsecond.

---

# 16. Resilience Engineering & Circuit Breaker Pattern

### Q16.1: Explain the Circuit Breaker Pattern and its implementation in NetWatch.
**Answer**:
The Circuit Breaker pattern prevents an application from repeatedly attempting an operation that is guaranteed to fail, saving CPU cycles, thread pools, and network socket descriptors.
- **Three States**:
  1. **`CLOSED`** (Normal): All network requests pass through to the target device. Consecutive failure counter is reset on success.
  2. **`OPEN`** (Tripped): When consecutive failures reach the threshold (e.g. 3 failed ICMP probes), the circuit trips to `OPEN`. All subsequent calls to this device are **short-circuited immediately** (returning cached failure without sending network packets) for a cooldown period (e.g. 60 seconds).
  3. **`HALF_OPEN`** (Trial Probe): After cooldown expires, the breaker allows a single trial probe through. If it succeeds, the breaker resets to `CLOSED`; if it fails, it trips back to `OPEN` for another cooldown cycle.

```
       +---------+  Success   +-------------+
       |         |<-----------|             |
       | CLOSED  |            |  HALF_OPEN  |
       |         |----------->|             |
       +---------+  Trip      +-------------+
            |      (3 Fails)         ^
            |                        | Cooldown
            v                        | Elapsed
       +-----------------------------+
       |            OPEN             |
       | (Short-Circuit Immediately) |
       +-----------------------------+
```

---

# 17. Event Streaming & Apache Kafka Architecture

### Q17.1: Compare Message Queues (RabbitMQ/Celery) vs Event Streaming Platforms (Apache Kafka). Why are both used in NetWatch?
**Answer**:
- **Message Queues (Celery/RabbitMQ)**: Designed for **Point-to-Point Task Execution**. A task is dispatched to a queue, processed by exactly *one* worker, and acknowledged/deleted. Ideal for executing actions (e.g., "Run SSH config backup on Router 1").
- **Event Streaming (Kafka)**: Designed for **Publish-Subscribe Event Log Broadcasting**. An event is published to an append-only, partitioned log and retained. Multiple independent consumer groups can read the same event stream concurrently at their own pace.
- **In NetWatch**: Celery executes the directed polling tasks; when a device status changes or telemetry is gathered, it publishes a domain event to Kafka (`netwatch.device.status`). The live web dashboard, incident management engine, time-series store, and ML anomaly detector consume the event simultaneously.

---

# 18. Real-Time Stream Processing & Anomaly Detection

### Q18.1: How does NetWatch's `EventStreamProcessor` detect cascading network failures?
**Answer**:
When a core switch fails, dozens of connected access points and servers drop simultaneously. Rather than triggering 50 individual, uncoordinated critical alerts that overwhelm the NOC team (alert fatigue):
1. `EventStreamProcessor` consumes from `netwatch.device.status`.
2. It maintains an in-memory sliding timestamp window (15 seconds).
3. If $\ge 3$ distinct network nodes transition to `OFFLINE` within that window, it detects a **`CASCADING_OUTAGE_DETECTED`** anomaly.
4. It flags an aggregated root-cause incident on the dashboard, identifying an upstream power or core switch failure.

---

# 19. Enterprise Security, Cryptography & Audit Trails

### Q19.1: How does NetWatch encrypt network device credentials at rest, and how are secrets masked in the API?
**Answer**:
1. **Fernet Symmetric Encryption (`cryptography.fernet`)**:
   - Uses AES-128 in CBC mode with PKCS7 padding, HMAC-SHA256 for message authentication, and dynamic IVs.
   - Device passwords and SNMP community strings are encrypted before being written to PostgreSQL.
2. **Secret Masking**:
   - `DeviceSerializer` marks password fields as `write_only=True`.
   - Serialized responses return masked representations (`••••••••••••`), preventing credential leakage over HTTP or in browser dev tools.

---

# 20. Linux Systems Programming & Network Utilities

### Q20.1: Explain the difference between `SIGTERM` (15) and `SIGKILL` (9), and how NetWatch handles graceful shutdown.
**Answer**:
- **`SIGTERM` (Signal 15)**: A graceful termination request sent to a process. The process can catch the signal, flush open file buffers, complete in-flight Celery tasks, close SSH channels, disconnect database pools, and exit cleanly.
- **`SIGKILL` (Signal 9)**: An uncatchable kernel-level kill command that immediately halts process execution. Operating systems clean up memory and file descriptors, but in-flight database transactions and network sockets may terminate abruptly without proper state cleanup.
- NetWatch registers signal handlers on Celery workers and Kafka consumers (`signal.signal(signal.SIGTERM, handler)`) to guarantee zero data loss during rolling deployments.

### Q20.2: What Linux CLI tools would you use to troubleshoot a network connectivity issue on a monitored server?
**Answer**:
1. **`ping -c 4 <ip>`**: Verify Layer 3 ICMP reachability and round-trip time.
2. **`traceroute <ip>` / `mtr <ip>`**: Identify routing hops and isolate which intermediate gateway is dropping packets.
3. **`ip a` / `ifconfig`**: Inspect local IP addresses, interface states (`UP`/`DOWN`), and MTU.
4. **`ip route` / `netstat -rn`**: Verify routing table and default gateway.
5. **`ss -tulpn` / `netstat -tulpn`**: Check listening TCP/UDP ports and bound sockets.
6. **`tcpdump -i eth0 icmp or port 161 -nn`**: Capture raw packet captures to verify if SNMP/ICMP packets are leaving the NIC and if responses arrive.
7. **`curl -Iv https://<target>`**: Test Layer 7 TLS handshake and HTTP response headers.

---

# 21. DevOps, Docker Containerization & Testing

### Q21.1: Describe NetWatch's Docker Compose topology and service dependencies.
**Answer**:
NetWatch is containerized into a multi-service orchestration topology:
1. `netwatch-backend`: Django REST API running under Gunicorn.
2. `netwatch-celery-worker`: Distributed polling worker pool.
3. `netwatch-celery-beat`: 30-second periodic scheduler.
4. `netwatch-kafka-consumer`: Real-time anomaly stream processor.
5. `netwatch-postgres`: PostgreSQL 16 relational database.
6. `netwatch-mongodb`: MongoDB 7 time-series telemetry store.
7. `netwatch-redis`: In-memory broker for Celery queues.
8. `netwatch-kafka` & `zookeeper`: Distributed event streaming cluster.
9. `netwatch-frontend`: Nginx serving the responsive glassmorphism web SPA.

---

# 22. EverestIMS Product Alignment & System Design Scenarios

### Q22.1: How does NetWatch map directly to EverestIMS Technologies' enterprise product suite?
**Answer**:
- **Infraon IMS (Infrastructure Management System)**: NetWatch replicates Infraon's core capabilities: multi-vendor device inventory, SNMP MIB polling, automated topology diagnostics, and credential management.
- **Infraon ITOM (IT Operations Management)**: NetWatch delivers automated scheduled config backups, bulk SSH command execution, and compliance audit logs.
- **Infraon AIOps / Alerting**: NetWatch implements automated incident lifecycles, sliding-window anomaly detection, cascading outage correlation, and real-time Kafka event streaming.

### Q22.2: System Design Scenario — "How would you scale NetWatch to monitor 50,000 network devices polling every 60 seconds?"
**Answer**:
1. **Polling Math**: 50,000 devices / 60 seconds $\approx 833$ polls/second.
2. **Distributed Celery Worker Scaling**: Deploy 20 Celery worker nodes with 50 concurrency slots each across regional network zones (total: 1,000 worker threads).
3. **Regional Polling Proxies (Collector Nodes)**: Deploy lightweight collector daemon agents local to each datacenter/VPC to poll devices locally and publish telemetry to a central Kafka cluster, eliminating WAN latency bottlenecks.
4. **PostgreSQL Partitioning**: Partition `check_logs` and `audit_logs` by month (`PARTITION BY RANGE (timestamp)`).
5. **MongoDB Sharding**: Shard `telemetry_metrics` collection across a 3-node replica set using `device_id` and `timestamp` as the composite shard key.
6. **Kafka Partitioning**: Create 16 partitions for `netwatch.telemetry.snmp`, allowing 16 parallel consumer workers to ingest metrics concurrently without consumer lag.
