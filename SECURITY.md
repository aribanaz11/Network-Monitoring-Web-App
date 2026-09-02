# Security Policy & Cryptographic Practices

## 🛡️ Overview

NetWatch is an enterprise-oriented Network Monitoring & Automation system designed with defense-in-depth principles:
- **Zero Hardcoded Secrets**: All production secrets, database credentials, cryptographic keys, and connection strings are strictly loaded via environment variables.
- **Symmetric Cryptography at Rest**: Remote SSH credentials and SNMP v2c/v3 community strings are encrypted at rest using AES-CBC (Fernet symmetric encryption).
- **Stateless RBAC & JWT Security**: 3-Tier Role-Based Access Control (`ADMIN`, `OPERATOR`, `VIEWER`) enforced through signed HMAC-SHA256 JSON Web Tokens with automated blacklist rotation on logout.
- **Audit Trail Immutability**: All diagnostic executions, SSH commands, configuration backups, and user activities are permanently logged and automatically sanitized of sensitive fields.

---

## 🔒 Secret & Credential Management

### 1. Cryptographic Keys

| Secret / Key | Minimum Complexity | Purpose | Loss Impact |
|---|---|---|---|
| `DJANGO_SECRET_KEY` | 50+ random characters | JWT signing, session protection, CSRF validation | Invalidates active user sessions |
| `FERNET_KEY` | 32-byte URL-safe base64 string | Encrypting stored SSH passwords & SNMP strings | **Permanent loss**: Encrypted device credentials become unrecoverable |

#### How to Generate Secure Production Keys:
```bash
# Generate Django Secret Key:
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# Generate 32-Byte URL-Safe Fernet Key:
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

> ⚠️ **CRITICAL WARNING**:
> The `FERNET_KEY` must remain persistent across application restarts and backups. Never generate a new key on server startup, as any existing encrypted device credentials in the database will be corrupted and rendered unreadable.

---

## 🔄 Historical Demo Credential Rotation Notice

> [!IMPORTANT]
> Early prototype commits in repository history contained public demo credentials and a sample Fernet encryption key used exclusively for automated continuous integration (CI) and local sandbox simulations.
> 
> **Security Policy**:
> 1. If any sample Fernet keys or sample credentials from previous commit history were ever loaded into a production environment, they **MUST be rotated immediately**.
> 2. Never deploy production instances using development or fallback keys.
> 3. Production deployments must provide freshly generated values for `DJANGO_SECRET_KEY`, `FERNET_KEY`, `DATABASE_URL`, and database access passwords via environment variables or cloud secret managers (e.g., AWS Secrets Manager, HashiCorp Vault, Railway/Render Secrets).

---

## 🚀 Environment Hardening Guidelines

### Local Development
1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Set `DEBUG=True` for local troubleshooting.
3. `.env` is ignored by `.gitignore` and must never be committed to Git.
4. Use `python backend/manage.py createsuperuser` to create your own unique administrator account.

### Production Deployments
1. **Always Set `DEBUG=False`**: Prevents Django debug stack traces from leaking server state or environment variables.
2. **Restrict `ALLOWED_HOSTS`**: Specify exact production domains and cloud hostnames (never use wildcard `*` in high-security production deployments).
3. **Configure SSL / HTTPS**: Ensure `SECURE_PROXY_SSL_HEADER` and `CSRF_TRUSTED_ORIGINS` match your live HTTPS reverse proxy or CDN.
4. **Isolate Network Access**: Restrict database and Redis ports to the internal container network; never expose PostgreSQL (port 5432) or Redis (port 6379) directly to the public internet.

---

## 🔍 Reporting a Vulnerability

If you discover a potential security vulnerability or sensitive information exposure within this repository, please report it responsibly:

1. **Do not create public GitHub issues** for security vulnerabilities.
2. Send an email to **`security@netwatch.io`** (or open a private security advisory via GitHub Security Advisories).
3. Include:
   - A detailed description of the issue.
   - Step-by-step reproduction steps or proof-of-concept.
   - Affected versions and environments.

Reports will be acknowledged within 48 hours, with a remediation timeline provided.
