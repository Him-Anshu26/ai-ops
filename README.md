<![CDATA[<div align="center">

# 🔮 AI Ops — Monitoring & Alerting Platform

**Production-grade backend for real-time service monitoring, intelligent alert generation, and incident lifecycle management.**

![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-5.2-092E20?logo=django&logoColor=white)
![DRF](https://img.shields.io/badge/DRF-3.16-ff1709?logo=django&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-336791?logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-8.0-DC382D?logo=redis&logoColor=white)
![Celery](https://img.shields.io/badge/Celery-5.6-37814A?logo=celery&logoColor=white)
![License](https://img.shields.io/badge/License-TBD-lightgrey)

</div>

---

## 📖 Project Overview

**AI Ops** is a backend platform built with Django REST Framework that provides centralized monitoring and alerting for distributed services. It ingests structured logs from monitored services, automatically evaluates alert rules against incoming data, generates alerts with severity classification, and dispatches notifications through configurable channels.

### Business Problem

Modern infrastructure teams need a single pane of glass to monitor service health, detect anomalies, and manage incidents from detection through resolution. AI Ops provides:

- **Log Ingestion** — Centralized collection of monitoring logs from any service.
- **Automated Alert Generation** — Rule-based alert engine that detects errors and high-latency conditions.
- **Incident Lifecycle Management** — Structured workflow for acknowledging and resolving alerts.
- **Notification Dispatch** — Email notifications with Slack placeholder for future expansion.
- **Scheduled Cleanup** — Automated retention policies to prevent database bloat.

### High-Level Architecture

```
Client → DRF API → Views → Service Layer → Models/Database
                      ↓
               Celery Worker → Alert Engine → Notification Service → Email/Slack
                      ↑
               Celery Beat → Scheduled Cleanup Tasks
                      ↑
                    Redis (Broker + Result Backend)
```

---

## ✨ Key Features

### Authentication & Authorization
- **Custom User Model** — Email-based authentication (no username field)
- **JWT Authentication** — Access tokens (15 min) and refresh tokens (7 days) via SimpleJWT
- **Session-Based Token Management** — Each login creates a DB-tracked session with hashed refresh tokens
- **Google OAuth 2.0 Login** — Full Google Sign-In flow with token verification, automatic user provisioning, and internal JWT issuance
- **Email Verification** — Mandatory email verification with secure hashed tokens (24-hour expiry)
- **Password Reset** — Token-based password reset with hashed tokens (30-minute expiry), invalidates all sessions on reset
- **Logout** — Soft session deactivation preserving audit history

### Monitoring
- **Log Ingestion API** — Create, list, and retrieve structured monitoring log entries
- **Service Model** — Track registered services with status (`active`, `down`, `maintenance`), slug generation, and soft delete
- **Structured Log Data** — Status, severity, HTTP status code, response time (ms), message, and JSON metadata per log entry
- **Cursor Pagination** — Efficient cursor-based pagination for time-series log data
- **Advanced Filtering** — Filter by service, status, status code, time range, response time range, and message text
- **Ordering** — Sort by `created_at` or `response_time_ms`

### Alert Engine
- **Automated Alert Generation** — Logs are evaluated against alert rules via Celery background tasks
- **Error Detection** — Triggers on error status or HTTP 5xx status codes
- **High Latency Detection** — Triggers when response time exceeds 1000ms threshold
- **Severity Classification** — Automatic severity assignment (`low`, `medium`, `high`, `critical`) based on status code and latency buckets
- **Alert Deduplication** — Unique constraint per service + type + alert key prevents duplicate active alerts
- **Cooldown Window** — 30-second cooldown prevents alert flooding
- **Trigger Count Tracking** — Atomic counter increments on repeated alert triggers
- **Race Condition Recovery** — IntegrityError fallback with row-level locking (`SELECT FOR UPDATE`)
- **Alert Lifecycle** — `open` → `acknowledged` → `resolved` workflow with resolution notes
- **Immutable Incident Records** — Alerts are treated as append-only; no generic update/delete operations

### Notification Service
- **Email Notifications** — SMTP-based alert email delivery via Django's `send_mail`
- **HTML Email Templates** — Professional HTML email template for alert notifications
- **Notification Orchestration** — Provider-isolated dispatch with per-provider error handling
- **Slack Placeholder** — Structured placeholder ready for Slack Incoming Webhooks integration
- **Feature Flags** — `EMAIL_NOTIFICATIONS_ENABLED` and `SLACK_NOTIFICATIONS_ENABLED` toggle notifications

### Cleanup Services
- **Accounts Cleanup** — Hourly scheduled task: expired email verification tokens, expired password reset tokens, inactive sessions (90-day retention)
- **Monitoring Cleanup** — Daily scheduled task (3 AM): monitoring logs older than 120 days
- **Alerts Cleanup** — Daily scheduled task (4 AM): resolved alerts older than 90 days

### Background Processing
- **Celery Workers** — Asynchronous task execution for alert processing and notification dispatch
- **Celery Beat** — Periodic scheduling for all cleanup tasks
- **Redis** — Message broker and result backend
- **Retry Strategy** — Exponential backoff with jitter for transient failures (`ConnectionError`, `DatabaseError`), max 5 retries
- **Transaction Safety** — `transaction.on_commit()` ensures Celery tasks run only after DB commits

### API Quality
- **Swagger / OpenAPI 3.0** — Auto-generated interactive API documentation via drf-spectacular
- **ReDoc** — Alternative API documentation viewer
- **Request/Response Examples** — Rich OpenAPI examples for every endpoint
- **Cursor Pagination** — Both logs and alerts use cursor-based pagination for large datasets
- **Input Validation** — Field-level and object-level validation on all serializers
- **Rate Limiting** — IP-based rate limiting on all auth endpoints via django-ratelimit
- **Anonymous Throttling** — Global 100 requests/day for unauthenticated requests

### Security
- **Password Hashing** — Django's PBKDF2 password hashing
- **Token Hashing** — SHA-256 hashing for verification, reset, and refresh tokens before DB storage
- **HSTS / SSL** — Production settings enforce HTTPS redirect, HSTS preload, secure cookies
- **CSRF Protection** — Django CSRF middleware enabled
- **Clickjacking Protection** — `X-Frame-Options: DENY` in production
- **Content Type Sniffing Prevention** — `SECURE_CONTENT_TYPE_NOSNIFF` enabled
- **Email Enumeration Prevention** — Generic responses on registration, verification resend, and password reset
- **Split Settings** — Separate `dev.py` and `prod.py` configurations
- **Environment Variables** — All secrets managed via `django-environ`

### Admin Interface
- **Custom User Admin** — Search, filter, and manage users with verification status
- **Service Admin** — Bulk status actions (active/down/maintenance), auto-assigned `created_by`
- **Log Admin** — Read-only log viewer with formatted JSON metadata display, no add/edit/delete
- **Alert Admin** — Bulk lifecycle actions (open/acknowledge/resolve), autocomplete fields, date hierarchy

---

## 🏗️ Architecture

### Request Flow

```
HTTP Request
    │
    ▼
┌────────────────┐
│   Django URL    │ ─── URL routing (/api/v1/...)
│   Router       │
└────────┬───────┘
         │
         ▼
┌────────────────┐
│   Views /      │ ─── Request validation, permission checks
│   ViewSets     │
└────────┬───────┘
         │
         ▼
┌────────────────┐
│  Serializers   │ ─── Input validation, output formatting
└────────┬───────┘
         │
         ▼
┌────────────────┐
│  Service Layer │ ─── Business logic, orchestration
└────────┬───────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌────────────┐
│ Models │ │   Celery    │ ─── Async alert processing,
│  (DB)  │ │   Tasks     │     notification dispatch,
└────────┘ └─────┬──────┘     cleanup jobs
                 │
                 ▼
           ┌──────────┐
           │  Redis    │ ─── Broker + Result Backend
           └──────────┘
```

### Component Responsibilities

| Component | Responsibility |
|-----------|---------------|
| **Views / ViewSets** | HTTP handling, permission enforcement, schema decoration |
| **Serializers** | Input validation, read/write separation, response formatting |
| **Services** | Business logic, DB transactions, token management, orchestration |
| **Models** | Data persistence, constraints, indexes, domain methods |
| **Tasks** | Async processing, retry policies, Celery Beat scheduling |
| **Schemas** | OpenAPI documentation decorators with examples |
| **Filters** | `django-filter` backends for query parameter filtering |
| **Pagination** | Cursor-based pagination for time-series data |
| **Throttling** | IP-based rate limiting per endpoint |

---

## 🛠️ Tech Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.12+ | Runtime |
| Django | 5.2.1 | Web framework |
| Django REST Framework | 3.16.0 | REST API |
| PostgreSQL | 15+ | Primary database |
| Redis | 8.0.1 | Celery broker & result backend |
| Celery | 5.6.3 | Async task processing |
| Celery Beat | 2.9.0 | Periodic task scheduling (`django-celery-beat`) |
| SimpleJWT | 5.5.1 | JWT authentication |
| drf-spectacular | 0.29.0 | OpenAPI 3.0 schema generation |
| django-allauth | 65.18.0 | Google OAuth 2.0 |
| django-filter | 25.1 | API filtering |
| django-ratelimit | 4.1.0 | Rate limiting |
| django-environ | 0.12.0 | Environment variable management |
| django-anymail | 15.0 | Email provider abstraction |
| django-extensions | 4.1 | Development utilities |
| google-auth | 2.56.0 | Google ID token verification |
| psycopg2-binary | 2.9.10 | PostgreSQL adapter |
| PyJWT | 2.13.0 | JWT token handling |

---

## 📁 Project Structure

```
ai_ops/
├── ai_ops/                    # Django project configuration
│   ├── settings/
│   │   ├── base.py            # Shared settings (DB, JWT, Celery, logging, email)
│   │   ├── dev.py             # Development overrides (DEBUG, BrowsableAPI, AllowAny)
│   │   └── prod.py            # Production hardening (HSTS, secure cookies, SSL)
│   ├── celery.py              # Celery application setup
│   ├── urls.py                # Root URL configuration with API versioning
│   ├── wsgi.py                # WSGI entry point
│   └── asgi.py                # ASGI entry point
│
├── accounts/                  # Authentication & user management app
│   ├── models.py              # User, EmailVerificationToken, PasswordResetToken, UserSession
│   ├── managers.py            # Custom UserManager (email-based)
│   ├── views.py               # Auth API views (register, login, verify, reset, Google)
│   ├── services.py            # Auth business logic (service classes)
│   ├── serializers.py         # Request/response serializers
│   ├── tokens.py              # JWT token generation and decoding
│   ├── utils.py               # Token generation, hashing, email sending
│   ├── throttling.py          # Per-endpoint rate limiting
│   ├── tasks.py               # Celery cleanup tasks
│   ├── admin.py               # Custom UserAdmin
│   ├── schemas/
│   │   └── auth_schema.py     # OpenAPI schema decorators
│   └── urls.py                # Auth URL routes
│
├── monitoring/                # Service monitoring & log ingestion app
│   ├── models.py              # Service, Log models with indexes
│   ├── views.py               # LogViewSet (create, list, retrieve)
│   ├── serializers/
│   │   └── log_serializer.py  # LogWriteSerializer, LogReadSerializer
│   ├── services/
│   │   ├── alert_service.py   # Alert rule engine & alert processing
│   │   └── cleanup_service.py # Log retention cleanup
│   ├── filters.py             # Log filtering (status, service, time range, response time)
│   ├── pagination.py          # LogCursorPagination
│   ├── tasks.py               # Celery tasks (alert processing, log cleanup)
│   ├── admin.py               # ServiceAdmin, LogAdmin (read-only)
│   ├── schemas/
│   │   └── log_schema.py      # OpenAPI schema decorators
│   └── urls.py                # Monitoring URL routes
│
├── alerts/                    # Alert management & notification app
│   ├── models.py              # Alert model with lifecycle, constraints, indexes
│   ├── views.py               # AlertViewSet (create, list, retrieve, resolve)
│   ├── serializers/
│   │   └── alert_serializer.py # AlertWrite, AlertRead, AlertResolve serializers
│   ├── services/
│   │   ├── notification_service.py  # Notification orchestrator
│   │   ├── email_service.py         # SMTP email delivery
│   │   ├── slack_service.py         # Slack webhook placeholder
│   │   └── cleanup_service.py       # Resolved alert cleanup
│   ├── filters.py             # Alert filtering (status, type, severity, time, trigger count)
│   ├── pagination.py          # AlertCursorPagination
│   ├── tasks.py               # Celery tasks (notification dispatch, alert cleanup)
│   ├── admin.py               # AlertAdmin with bulk lifecycle actions
│   ├── schemas/
│   │   └── alert_schema.py    # OpenAPI schema decorators
│   ├── templates/emails/
│   │   ├── alert_created.html # HTML alert notification template
│   │   └── alert_created.txt  # Plain-text alert notification template
│   └── urls.py                # Alert URL routes
│
├── templates/
│   └── google_login_test/
│       └── google_test.html   # Google OAuth test page
│
├── manage.py                  # Django management script
├── requirements.txt           # Python dependencies
├── .env.example               # Environment variable template
└── .gitignore                 # Git ignore rules
```

---

## 🚀 Installation

### Prerequisites

- Python 3.12+
- PostgreSQL 15+
- Redis 7+

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/ai-ops.git
cd ai-ops
```

### 2. Create Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

```bash
cp .env.example .env.dev
```

Edit `.env.dev` with your local configuration (see [Environment Variables](#-environment-variables) below).

### 5. Run Database Migrations

```bash
python manage.py migrate
```

### 6. Create Superuser

```bash
python manage.py createsuperuser
```

### 7. Start Redis

```bash
# Docker
docker run -d -p 6379:6379 redis:latest

# Or use your local Redis installation
redis-server
```

### 8. Start Celery Worker

```bash
celery -A ai_ops worker --loglevel=info
```

### 9. Start Celery Beat

```bash
celery -A ai_ops beat --loglevel=info
```

### 10. Run Development Server

```bash
python manage.py runserver
```

The API is now available at `http://localhost:8000/api/v1/`.

---

## 🔐 Environment Variables

| Variable | Required | Description | Default | Example |
|----------|----------|-------------|---------|---------|
| `SECRET_KEY` | ✅ | Django secret key | — | `your-secret-key` |
| `DB_NAME` | ✅ | PostgreSQL database name | `postgres` | `ai_ops_db` |
| `DB_USER` | ✅ | PostgreSQL username | `postgres` | `postgres` |
| `DB_PASSWORD` | ✅ | PostgreSQL password | — | `your-db-password` |
| `DB_HOST` | ❌ | PostgreSQL host | `localhost` | `localhost` |
| `DB_PORT` | ❌ | PostgreSQL port | `5432` | `5432` |
| `CELERY_BROKER_URL` | ✅ | Redis broker URL | — | `redis://localhost:6379/0` |
| `CELERY_RESULT_BACKEND` | ✅ | Redis result backend URL | — | `redis://localhost:6379/0` |
| `EMAIL_PROVIDER` | ✅ | Email provider name | — | `gmail` |
| `EMAIL_BACKEND` | ✅ | Django email backend | — | `django.core.mail.backends.smtp.EmailBackend` |
| `EMAIL_HOST` | ✅ | SMTP host | — | `smtp.gmail.com` |
| `EMAIL_PORT` | ✅ | SMTP port | — | `587` |
| `EMAIL_USE_TLS` | ✅ | Enable TLS | — | `True` |
| `EMAIL_HOST_USER` | ✅ | SMTP username | — | `you@gmail.com` |
| `EMAIL_HOST_PASSWORD` | ✅ | SMTP password / app password | — | `your-app-password` |
| `DEFAULT_FROM_EMAIL` | ✅ | Default sender address | — | `AI Ops <noreply@example.com>` |
| `ALERT_EMAIL_RECIPIENTS` | ✅ | Comma-separated alert recipients | — | `admin@example.com` |
| `FRONTEND_URL` | ❌ | Frontend base URL for links | `http://localhost:3000` | `https://app.example.com` |
| `BACKEND_URL` | ❌ | Backend base URL | `http://localhost:8000` | `https://api.example.com` |
| `GOOGLE_CLIENT_ID` | ✅ | Google OAuth client ID | — | `xxxx.apps.googleusercontent.com` |
| `GOOGLE_CLIENT_SECRET` | ✅ | Google OAuth client secret | — | `GOCSPX-xxxx` |
| `EMAIL_NOTIFICATIONS_ENABLED` | ❌ | Enable email alert notifications | `True` | `True` |
| `SLACK_NOTIFICATIONS_ENABLED` | ❌ | Enable Slack notifications | `False` | `False` |
| `ALLOWED_HOSTS` | ✅ (prod) | Comma-separated allowed hosts | — | `api.example.com` |

---

## 📡 API Documentation

### Interactive Documentation

| URL | Interface |
|-----|-----------|
| `/api/v1/docs/` | Swagger UI |
| `/api/v1/docs/redoc/` | ReDoc |
| `/api/v1/schema/` | Raw OpenAPI 3.0 JSON schema |

### API Endpoints

#### Authentication — `/api/v1/accounts/`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/register/` | Register new user account |
| `POST` | `/login/` | Authenticate and receive JWT tokens |
| `GET` | `/verify-email/?token=<token>` | Verify email address |
| `POST` | `/resend-verification/` | Resend verification email |
| `POST` | `/refresh/` | Refresh access token |
| `POST` | `/logout/` | Invalidate current session |
| `POST` | `/password-reset/` | Request password reset email |
| `POST` | `/password-reset-confirm/` | Reset password with token |
| `POST` | `/google-login/` | Authenticate via Google ID token |

#### Monitoring — `/api/v1/monitoring/`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/logs/` | List monitoring logs (paginated, filterable) |
| `POST` | `/logs/` | Create a new monitoring log entry |
| `GET` | `/logs/{id}/` | Retrieve a single log entry |

#### Alerts — `/api/v1/alerts/`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | List alerts (paginated, filterable) |
| `POST` | `/` | Create an alert (testing/QA) |
| `GET` | `/{id}/` | Retrieve a single alert |
| `POST` | `/{id}/resolve/` | Resolve an alert with resolution note |

---

## 🔑 Authentication Flow

### Registration & Email Verification

```
1. POST /api/v1/accounts/register/
   → User created (is_verified=False)
   → Raw token generated (secrets.token_urlsafe)
   → Token SHA-256 hashed before DB storage
   → Verification email sent with raw token link
   → Token expires in 24 hours

2. GET /api/v1/accounts/verify-email/?token=<raw_token>
   → Incoming token hashed with SHA-256
   → Hash compared against DB record
   → User marked is_verified=True
   → Token deleted (one-time use)
```

### Login & JWT Lifecycle

```
3. POST /api/v1/accounts/login/
   → Credentials validated (email + password)
   → Email verification enforced
   → Unique session_id generated
   → Access token generated (15 min, contains user_id + session_id)
   → Refresh token generated (7 days, contains user_id + session_id)
   → Refresh token SHA-256 hashed and stored in UserSession
   → Both tokens returned to client

4. POST /api/v1/accounts/refresh/
   → Refresh token JWT decoded and validated
   → Active session lookup by user_id + session_id
   → Incoming refresh token hash compared against DB hash
   → New access token issued (same session_id)

5. POST /api/v1/accounts/logout/
   → session_id extracted from JWT payload
   → UserSession marked is_active=False (soft logout)
   → Session preserved for audit history
```

### Password Reset

```
6. POST /api/v1/accounts/password-reset/
   → Generic response regardless of email existence
   → Reset token generated and hashed (30 min expiry)
   → Reset email sent with raw token link

7. POST /api/v1/accounts/password-reset-confirm/
   → Token validated and expiry checked
   → Password updated (hashed)
   → ALL user sessions invalidated
   → Token deleted (one-time use)
```

### Google OAuth 2.0

```
8. POST /api/v1/accounts/google-login/
   → Google ID token verified via google.oauth2.id_token
   → Issuer validated (accounts.google.com)
   → Email verification status checked
   → Existing user found or new user auto-provisioned
   → SocialAccount record created/linked
   → Internal session created with JWT tokens
   → Standard access + refresh tokens returned
```

---

## ⚙️ Background Processing

### Celery Configuration

| Setting | Value |
|---------|-------|
| Broker | Redis |
| Result Backend | Redis |
| Serializer | JSON |
| Soft Time Limit | 300 seconds |
| Hard Time Limit | 600 seconds |

### Asynchronous Tasks

| Task | App | Trigger | Description |
|------|-----|---------|-------------|
| `process_log_for_alerts_task` | monitoring | On log creation (`transaction.on_commit`) | Evaluates alert rules against new log |
| `dispatch_alert_notifications_task` | alerts | On alert creation/update | Dispatches email/Slack notifications |
| `cleanup_accounts` | accounts | Celery Beat — every hour | Cleans expired tokens and inactive sessions |
| `cleanup_monitoring` | monitoring | Celery Beat — daily at 3:00 AM | Deletes logs older than 120 days |
| `cleanup_alerts_task` | alerts | Celery Beat — daily at 4:00 AM | Deletes resolved alerts older than 90 days |

### Retry Strategy

The `process_log_for_alerts_task` and `dispatch_alert_notifications_task` implement production-grade retry policies:

- **Auto-retry on**: `ConnectionError`, `DatabaseError`
- **Max retries**: 5
- **Backoff**: Exponential with jitter
- **Max backoff**: 300 seconds

---

## 🛡️ Security

| Feature | Implementation |
|---------|----------------|
| JWT Authentication | SimpleJWT with HS256, 15-min access / 7-day refresh |
| Password Hashing | Django PBKDF2 (default) |
| Token Hashing | SHA-256 for all verification, reset, and refresh tokens |
| Refresh Token Validation | Hash comparison against DB-stored session |
| Session Management | DB-tracked sessions with soft logout |
| Email Verification | Mandatory before login, 24-hour token expiry |
| Email Enumeration Prevention | Generic responses on all public auth endpoints |
| Rate Limiting | IP-based via `django-ratelimit` (5-10 req/min per endpoint) |
| Anonymous Throttling | 100 requests/day global via DRF `AnonRateThrottle` |
| Password Validation | Django's built-in validators (similarity, length, common, numeric) |
| CSRF Protection | Django CSRF middleware enabled |
| HSTS | 1-year duration, include subdomains, preload (production) |
| SSL Redirect | Enforced in production |
| Secure Cookies | `SESSION_COOKIE_SECURE` and `CSRF_COOKIE_SECURE` (production) |
| Clickjacking Protection | `X-Frame-Options: DENY` (production) |
| Content Type Sniffing | `SECURE_CONTENT_TYPE_NOSNIFF` (production) |
| Input Validation | Field-level and object-level serializer validation |
| Split Settings | Separate dev/prod configurations |
| Secret Management | All secrets via environment variables (`django-environ`) |

---

## 🗄️ Database

### Models

#### `accounts` App

| Model | Description |
|-------|-------------|
| **User** | Custom user model; email as primary identifier; `is_verified`, `auth_provider` (`local`/`google`), `provider_id` fields |
| **EmailVerificationToken** | SHA-256 hashed verification tokens with 24-hour expiry |
| **PasswordResetToken** | SHA-256 hashed reset tokens with 30-minute expiry |
| **UserSession** | Tracks active sessions; stores hashed refresh tokens; supports soft logout |

#### `monitoring` App

| Model | Description |
|-------|-------------|
| **Service** | Monitored service with name, slug (auto-generated), status, soft delete; unique per user |
| **Log** | Monitoring log entry with status (`success`/`warning`/`error`), severity, HTTP status code, response time, JSON metadata |

#### `alerts` App

| Model | Description |
|-------|-------------|
| **Alert** | Incident record with type (`error`/`downtime`/`high_latency`), severity, lifecycle status, trigger count, resolution notes |

### Key Relationships

```
User ──┬── EmailVerificationToken (1:N)
       ├── PasswordResetToken (1:N)
       ├── UserSession (1:N)
       └── Service (1:N, via created_by)
                └── Log (1:N)
                      └── Alert (N:1 via log, N:1 via service)
```

### Database Optimizations

- **Composite indexes** on frequently queried field combinations
- **Partial indexes** for active-only queries (e.g., `idx_active_alerts_per_service`)
- **Unique constraints** with conditions to enforce business rules (e.g., one active alert per service+type+key)
- **`select_related`** on all ViewSet querysets to prevent N+1 queries
- **`select_for_update`** for row-level locking in concurrent alert processing

---

## 📋 Logging

### Configuration

AI Ops uses Django's structured logging framework with a standardized format:

```
[2026-07-20 10:30:00] INFO monitoring: Starting alert processing for log 42
```

| Logger | Level | Propagate | Purpose |
|--------|-------|-----------|---------|
| `root` | INFO | — | Catch-all |
| `django` | INFO | No | Framework logs |
| `ai_ops` | INFO | No | Application-wide logs |
| `monitoring` | INFO | No | Log ingestion and alert engine |
| `alerts` | INFO | No | Alert lifecycle and notifications |

### What Gets Logged

- User registration, login, logout, email verification
- Alert rule evaluation (matching rules, cooldown skips, create/update decisions)
- Notification dispatch (email sent/failed, Slack placeholder)
- Cleanup task execution (deleted token/session/log/alert counts)
- Race condition recovery (IntegrityError fallbacks)
- Celery task start/finish with log and alert IDs

---

## 📦 API Response Format

### Success Response

```json
{
    "message": "Login successful.",
    "tokens": {
        "access": "eyJhbGciOiJIUzI1NiIs...",
        "refresh": "eyJhbGciOiJIUzI1NiIs..."
    }
}
```

### Paginated Response (Cursor)

```json
{
    "next": "http://localhost:8000/api/v1/monitoring/logs/?cursor=cD0yMDI2...",
    "previous": null,
    "results": [
        {
            "id": 1,
            "service": 1,
            "service_name": "Auth Service",
            "status": "error",
            "status_code": 500,
            "response_time_ms": 3200,
            "message": "Database connection failed",
            "created_at": "2026-07-20T10:30:00Z"
        }
    ]
}
```

### Validation Error

```json
{
    "email": [
        "A user with this email already exists."
    ],
    "password": [
        "This password is too common."
    ]
}
```

### Authentication Error

```json
{
    "detail": "Authentication credentials were not provided."
}
```

---

## 🧪 Running Tests

> **Note:** Automated tests have not yet been added to this project. Test files exist but are currently empty. Manual testing is supported through the Swagger UI at `/api/v1/docs/` and the Django admin at `/admin/`.

---

## 🏭 Production Readiness

The following production practices are already implemented:

| Practice | Status |
|----------|--------|
| Service layer architecture | ✅ |
| Read/write serializer separation | ✅ |
| Cursor-based pagination | ✅ |
| Advanced filtering (django-filter) | ✅ |
| JWT authentication (SimpleJWT) | ✅ |
| OAuth 2.0 (Google) | ✅ |
| Background task processing (Celery) | ✅ |
| Periodic task scheduling (Celery Beat) | ✅ |
| Redis broker & result backend | ✅ |
| Rate limiting (per-endpoint) | ✅ |
| Environment variable management | ✅ |
| Split dev/prod settings | ✅ |
| Production security hardening (HSTS, SSL, secure cookies) | ✅ |
| Structured logging | ✅ |
| Database indexing & constraints | ✅ |
| N+1 query prevention | ✅ |
| Transaction safety (`atomic`, `on_commit`) | ✅ |
| Race condition handling (row locking, IntegrityError recovery) | ✅ |
| Alert deduplication & cooldown | ✅ |
| Retry strategy with exponential backoff | ✅ |
| Data retention & cleanup automation | ✅ |
| OpenAPI 3.0 documentation | ✅ |
| Email notification system | ✅ |
| HTML email templates | ✅ |
| Custom Django admin interface | ✅ |

---

## 🗺️ Roadmap

The following items have **not yet been implemented** and represent potential future improvements:

- [ ] **Docker & Docker Compose** — Containerized development and deployment
- [ ] **CI/CD Pipeline** — GitHub Actions or GitLab CI for automated testing and deployment
- [ ] **Automated Test Suite** — Unit tests, integration tests, and API tests
- [ ] **Slack Integration** — Complete Slack Incoming Webhooks notification delivery
- [ ] **WebSocket Support** — Real-time alert streaming via Django Channels
- [ ] **Monitoring Dashboard** — Frontend dashboard for visualizing service health
- [ ] **RBAC / Multi-Tenancy** — Organization-scoped access control
- [ ] **Downtime Detection** — Heartbeat-based service downtime alerting
- [ ] **Full-Text Search** — PostgreSQL trigram or Elasticsearch for log/alert search
- [ ] **Gunicorn / Uvicorn** — Production WSGI/ASGI server configuration
- [ ] **Static File Serving** — WhiteNoise or CDN integration
- [ ] **Health Check Endpoints** — Liveness and readiness probes for orchestration
- [ ] **Metrics Export** — Prometheus or StatsD metrics integration

---

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. **Fork** the repository.
2. **Create a feature branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Follow existing patterns** — service layer, serializer separation, schema decorators.
4. **Write clear commit messages** — use conventional commits where possible.
5. **Add or update OpenAPI schemas** for any new endpoints.
6. **Test your changes** — ensure the application runs and API responses are correct.
7. **Submit a Pull Request** with a clear description of the changes.

### Code Style

- Follow PEP 8 conventions.
- Use type hints in service layer functions.
- Keep views thin — delegate business logic to services.
- Use `transaction.atomic()` for multi-step database operations.
- Use `transaction.on_commit()` for Celery task dispatch.

---

## 📄 License

License to be added.

---

## 👤 Maintainer

| Field | Details |
|-------|---------|
| **Name** | Your Name |
| **GitHub** | [@your-username](https://github.com/your-username) |
| **LinkedIn** | [Your LinkedIn](https://linkedin.com/in/your-profile) |
| **Email** | your.email@example.com |

---

<div align="center">

**Built with Django REST Framework** · **Designed for Production**

</div>
]]>
