# Contributing to AI Ops

Thank you for your interest in contributing to **AI Ops** — a production-grade monitoring and alerting platform built with Django REST Framework. This document provides guidelines and instructions to help you contribute effectively.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Fork & Clone](#fork--clone)
  - [Python Environment](#python-environment)
  - [Environment Variables](#environment-variables)
  - [PostgreSQL Setup](#postgresql-setup)
  - [Redis Setup](#redis-setup)
  - [Database Migrations](#database-migrations)
  - [Starting the Development Server](#starting-the-development-server)
  - [Starting Celery Worker & Beat](#starting-celery-worker--beat)
- [Project Architecture](#project-architecture)
- [Coding Standards](#coding-standards)
  - [Python Style](#python-style)
  - [Django & DRF Conventions](#django--drf-conventions)
  - [Service Layer Pattern](#service-layer-pattern)
  - [Serializer Separation](#serializer-separation)
  - [Database Guidelines](#database-guidelines)
  - [Async Task Guidelines](#async-task-guidelines)
  - [Logging](#logging)
  - [API Documentation](#api-documentation)
- [Commit Message Conventions](#commit-message-conventions)
- [Branch Naming Conventions](#branch-naming-conventions)
- [Pull Request Process](#pull-request-process)
- [Testing Guidelines](#testing-guidelines)
- [Security Reporting](#security-reporting)

---

## Code of Conduct

Be respectful, constructive, and professional. We are building production-grade software and expect all contributors to maintain a collaborative and inclusive environment.

---

## Getting Started

### Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| **Python** | 3.12+ | Runtime |
| **PostgreSQL** | 15+ | Primary database |
| **Redis** | 7+ | Celery broker & result backend |
| **Git** | Latest | Version control |

### Fork & Clone

```bash
# Fork the repository on GitHub, then:
git clone https://github.com/<your-username>/ai-ops.git
cd ai-ops
git remote add upstream https://github.com/Him-Anshu26/ai-ops.git
```

### Python Environment

Create and activate a virtual environment:

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

### Environment Variables

Copy the example environment file and configure it for local development:

```bash
cp .env.example .env.dev
```

Edit `.env.dev` with your local values. At minimum, you need:

```env
SECRET_KEY=your-local-secret-key

DB_NAME=ai_ops_dev
DB_USER=postgres
DB_PASSWORD=your-db-password
DB_HOST=localhost
DB_PORT=5432

CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

EMAIL_PROVIDER=gmail
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=you@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=AI Ops <noreply@example.com>

ALERT_EMAIL_RECIPIENTS=admin@example.com

FRONTEND_URL=http://localhost:3000
BACKEND_URL=http://localhost:8000

GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

EMAIL_NOTIFICATIONS_ENABLED=True
SLACK_NOTIFICATIONS_ENABLED=False
```

> **Tip:** For local development, set `EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend` to print emails to the terminal instead of sending them via SMTP.

### PostgreSQL Setup

Create the development database:

```sql
-- Connect to PostgreSQL
psql -U postgres

-- Create the database
CREATE DATABASE ai_ops_dev;
```

### Redis Setup

Start Redis locally:

```bash
# Using Docker (recommended)
docker run -d -p 6379:6379 redis:latest

# Or using a local installation
redis-server
```

Verify Redis is running:

```bash
redis-cli ping
# Expected output: PONG
```

### Database Migrations

Apply all migrations:

```bash
python manage.py migrate
```

Create a superuser for admin access:

```bash
python manage.py createsuperuser
```

### Starting the Development Server

```bash
python manage.py runserver
```

The API will be available at:

| URL | Description |
|-----|-------------|
| `http://localhost:8000/api/v1/docs/` | Swagger UI |
| `http://localhost:8000/api/v1/docs/redoc/` | ReDoc |
| `http://localhost:8000/admin/` | Django Admin |

> **Note:** In development mode (`ai_ops.settings.dev`), the BrowsableAPI renderer is enabled and all endpoints default to `AllowAny` permissions for easier testing.

### Starting Celery Worker & Beat

Open **two additional terminal windows** (with the virtual environment activated):

**Terminal 2 — Celery Worker:**

```bash
celery -A ai_ops worker --loglevel=info
```

**Terminal 3 — Celery Beat (Scheduler):**

```bash
celery -A ai_ops beat --loglevel=info
```

Celery Beat schedules the following periodic tasks:

| Task | Schedule | Description |
|------|----------|-------------|
| `accounts-cleanup` | Every hour | Expired tokens & inactive sessions (90-day retention) |
| `monitoring-cleanup` | Daily at 3:00 AM | Monitoring logs older than 120 days |
| `alerts-cleanup` | Daily at 4:00 AM | Resolved alerts older than 90 days |

---

## Project Architecture

```
ai_ops/
├── ai_ops/                    # Django project configuration
│   ├── settings/
│   │   ├── base.py            # Shared settings
│   │   ├── dev.py             # Development overrides
│   │   └── prod.py            # Production hardening
│   ├── celery.py              # Celery application
│   └── urls.py                # Root URL configuration
│
├── accounts/                  # Authentication & user management
│   ├── models.py              # User, EmailVerificationToken, PasswordResetToken, UserSession
│   ├── views.py               # Auth API views
│   ├── services.py            # Business logic (service classes)
│   ├── serializers.py         # Request/response serializers
│   ├── tokens.py              # JWT generation and decoding
│   ├── utils.py               # Token generation, hashing, email sending
│   ├── throttling.py          # Per-endpoint rate limiting
│   ├── tasks.py               # Celery cleanup tasks
│   ├── admin.py               # Custom UserAdmin
│   └── schemas/               # OpenAPI schema decorators
│
├── monitoring/                # Service monitoring & log ingestion
│   ├── models.py              # Service, Log
│   ├── views.py               # LogViewSet
│   ├── serializers/           # LogWriteSerializer, LogReadSerializer
│   ├── services/              # Alert engine, cleanup
│   ├── filters.py             # django-filter backends
│   ├── pagination.py          # Cursor pagination
│   ├── tasks.py               # Celery tasks
│   ├── admin.py               # ServiceAdmin, LogAdmin
│   └── schemas/               # OpenAPI schema decorators
│
├── alerts/                    # Alert management & notifications
│   ├── models.py              # Alert
│   ├── views.py               # AlertViewSet
│   ├── serializers/           # AlertWrite, AlertRead, AlertResolve
│   ├── services/              # Notification, email, Slack, cleanup
│   ├── filters.py             # django-filter backends
│   ├── pagination.py          # Cursor pagination
│   ├── tasks.py               # Celery tasks
│   ├── admin.py               # AlertAdmin with bulk actions
│   ├── templates/emails/      # HTML & plain-text email templates
│   └── schemas/               # OpenAPI schema decorators
│
├── manage.py
├── requirements.txt
└── .env.example
```

### Key Design Decisions

| Pattern | Where | Why |
|---------|-------|-----|
| **Service Layer** | `services.py` / `services/` | Business logic stays out of views |
| **Read/Write Serializers** | `serializers/` | Separate validation from response formatting |
| **Schema Decorators** | `schemas/` | OpenAPI docs decoupled from view logic |
| **Cursor Pagination** | `pagination.py` | Efficient traversal of time-series data |
| **django-filter** | `filters.py` | Declarative, reusable query filtering |
| **Celery Tasks** | `tasks.py` | Async alert processing and cleanup |

---

## Coding Standards

### Python Style

- Follow **PEP 8** conventions.
- Use **type hints** in service layer functions and utility modules.
- Maximum line length: **120 characters** (relaxed from PEP 8's 79).
- Use **f-strings** for string formatting.
- Prefer **explicit imports** over wildcard imports (except in settings files).

### Django & DRF Conventions

- **Views must be thin.** Delegate all business logic to the service layer — views should only handle HTTP concerns (request parsing, response formatting, status codes).
- **Never put business logic in serializers.** Serializers handle validation and data transformation only.
- **Never put business logic in models.** Models define schema, constraints, and lightweight domain methods.
- **Use `APIView`** for authentication endpoints and **`ViewSet` mixins** for CRUD resources.
- **Block operations explicitly.** If a ViewSet should not support update or delete, restrict `http_method_names` and omit the corresponding mixins.

### Service Layer Pattern

All business logic lives in service classes within `services.py` or the `services/` directory. Services are instantiated as module-level callables:

```python
class MyService:
    @transaction.atomic
    def __call__(self, ...) -> ReturnType:
        # business logic here
        pass

# Module-level instance — imported and called directly
my_service = MyService()
```

When contributing a new service:

1. Create a service class with `__call__` as the entry point.
2. Use `@transaction.atomic` for multi-step database operations.
3. Use type hints on all parameters and return values.
4. Log meaningful events using the app-specific logger.
5. Instantiate the service as a module-level variable.

### Serializer Separation

Each app uses separate serializers for different operations:

| Serializer | Purpose | Convention |
|------------|---------|------------|
| `*WriteSerializer` | Input validation for create operations | Fields clients can write |
| `*ReadSerializer` | Output formatting for list/retrieve | Includes computed fields like `service_name` |
| `*ResolveSerializer` (alerts) | Workflow-specific validation | Isolated state-transition logic |

When adding a new resource, create at minimum a `WriteSerializer` and a `ReadSerializer`. Wire them in the ViewSet's `get_serializer_class()` method:

```python
def get_serializer_class(self):
    if self.action == 'create':
        return MyWriteSerializer
    return MyReadSerializer
```

### Database Guidelines

- Add **composite indexes** for frequently queried field combinations.
- Add **partial indexes** when queries consistently filter on a specific condition (e.g., active-only records).
- Use **conditional unique constraints** to enforce business rules at the database level.
- Use `select_related()` on all ViewSet querysets to prevent N+1 queries.
- Use `select_for_update()` when concurrent writes may cause race conditions.
- Use `F()` expressions for atomic field updates (e.g., counter increments).
- Use `update_fields` on `model.save()` when only specific fields changed.

### Async Task Guidelines

- Use `transaction.on_commit()` when dispatching Celery tasks after database writes — this prevents workers from querying uncommitted data.
- Configure `autoretry_for` with specific exception types (e.g., `ConnectionError`, `DatabaseError`).
- Set `retry_backoff=True` and `retry_jitter=True` for exponential backoff.
- Cap retries with `retry_kwargs={"max_retries": 5}`.
- Always use `select_related()` when loading objects inside tasks.
- Handle `DoesNotExist` gracefully — the source record may have been deleted between dispatch and execution.

### Logging

Use Python's `logging` module with the app-specific logger:

```python
import logging

logger = logging.getLogger(__name__)
```

- Log at `INFO` level for normal operations (user actions, task completion).
- Log at `WARNING` level for recoverable issues (missing records, race condition fallbacks).
- Log at `ERROR`/`EXCEPTION` level for failures.
- Use structured `extra={}` dictionaries for contextual data:

```python
logger.info(
    "User registered successfully",
    extra={"user_id": user.id},
)
```

- **Never log sensitive data** — no passwords, tokens, secrets, or PII.

### API Documentation

Every new endpoint must include OpenAPI schema decorators via `drf-spectacular`:

1. Create a schema file in `<app>/schemas/<resource>_schema.py`.
2. Define `extend_schema` decorators with `tags`, `summary`, `description`, `parameters`, `request`, `responses`, and `examples`.
3. Apply the decorator to the corresponding ViewSet method or APIView handler.

```python
from drf_spectacular.utils import extend_schema, OpenApiExample

my_endpoint_schema = extend_schema(
    tags=['MyResource'],
    summary='Create a resource',
    description='Detailed description of the endpoint.',
    examples=[
        OpenApiExample(
            'Example Name',
            value={'field': 'value'},
            request_only=True,
        ),
    ],
)
```

---

## Commit Message Conventions

This project uses **Conventional Commits**. Every commit message must follow this format:

```
<type>(<scope>): <description>
```

### Types

| Type | Usage |
|------|-------|
| `feat` | New feature |
| `fix` | Bug fix |
| `refactor` | Code restructuring without behavior change |
| `perf` | Performance improvement |
| `security` | Security-related change |
| `docs` | Documentation only |
| `style` | Formatting, whitespace, import ordering |
| `chore` | Build, tooling, configuration changes |
| `test` | Adding or modifying tests |
| `build` | Dependency or build system changes |
| `admin` | Django admin changes |

### Scopes

Use the Django app name as the scope where applicable:

- `accounts` — Authentication, users, sessions
- `monitoring` — Services, logs, alert engine
- `alerts` — Alert model, viewset, notifications
- `settings` — Django settings configuration

### Examples

```
feat(accounts): add Google OAuth 2.0 login flow
fix(alerts): resolve race condition in concurrent alert creation
perf(monitoring): optimize log queryset with select_related
refactor(accounts): replace debug prints with structured logging
security(settings): enforce HSTS preload in production
docs: update API endpoint table in README
chore(settings): configure Celery Beat schedules
admin(alerts): add bulk lifecycle actions to AlertAdmin
```

### Rules

- Use the **imperative mood** in the description ("add", not "added" or "adds").
- Keep the first line under **72 characters**.
- Do not end the description with a period.
- Reference issue numbers where applicable: `fix(alerts): resolve cooldown bug (#42)`.

---

## Branch Naming Conventions

Create feature branches from `main` using the following format:

```
<type>/<short-description>
```

### Examples

```
feature/google-oauth-login
fix/alert-deduplication-race-condition
refactor/service-layer-accounts
perf/monitoring-query-optimization
docs/contributing-guide
chore/celery-beat-schedule
security/token-hashing
```

### Rules

- Use **lowercase** with **hyphens** as separators.
- Keep branch names **short but descriptive**.
- Prefix with the change type matching commit conventions.
- Always branch from the latest `main`.

---

## Pull Request Process

### Before Submitting

1. **Sync with upstream:**

   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Verify the application starts cleanly:**

   ```bash
   python manage.py migrate
   python manage.py runserver
   ```

3. **Verify Celery workers start without errors:**

   ```bash
   celery -A ai_ops worker --loglevel=info
   ```

4. **Test your API changes** via Swagger UI at `/api/v1/docs/`.

5. **Ensure OpenAPI schema generates without errors:**

   ```bash
   python manage.py spectacular --validate --fail-on-warn
   ```

### Submitting

1. Push your branch to your fork.
2. Open a Pull Request against `Him-Anshu26/ai-ops:main`.
3. Fill out the PR description with:
   - **What** — Summary of changes.
   - **Why** — Problem being solved or feature being added.
   - **How** — Key implementation details, especially non-obvious decisions.
   - **Testing** — How you verified the changes work.

### PR Checklist

- [ ] Code follows the [service layer pattern](#service-layer-pattern) — no business logic in views or serializers.
- [ ] Read/write serializer separation for any new API resources.
- [ ] OpenAPI schema decorators added for any new or modified endpoints.
- [ ] Database queries use `select_related()` where applicable.
- [ ] Celery tasks use `transaction.on_commit()` for dispatch.
- [ ] New models include appropriate indexes and constraints.
- [ ] Structured logging added for significant operations.
- [ ] No hardcoded secrets, tokens, or credentials.
- [ ] Commit messages follow [Conventional Commits](#commit-message-conventions).
- [ ] Django admin configured for any new models.
- [ ] Changes tested via Swagger UI and/or Django admin.

### Review Process

- At least one maintainer review is required before merging.
- Address all review comments before requesting re-review.
- Squash fixup commits before merge where appropriate.

---

## Testing Guidelines

> **Note:** The automated test suite is not yet established for this project. Test files exist but are currently scaffolds. Contributions that add tests are highly welcome.

### Manual Testing

Until the automated test suite is in place, verify all changes manually:

1. **API endpoints** — Use the Swagger UI at `/api/v1/docs/` to test request/response flows.
2. **Admin interface** — Verify model admin pages at `/admin/`.
3. **Celery tasks** — Check worker terminal output for task execution and logging.
4. **Alert engine** — Create a monitoring log with `status: error` or `response_time_ms > 1000` and verify alert creation.
5. **Notifications** — Verify email dispatch in the Celery worker logs (use console email backend for development).

### Future Test Strategy

When contributing tests, follow these conventions:

| Test Type | Location | Framework |
|-----------|----------|-----------|
| Unit tests | `<app>/tests/test_services.py` | `pytest` + `pytest-django` |
| API tests | `<app>/tests/test_views.py` | DRF's `APITestCase` or `pytest` |
| Model tests | `<app>/tests/test_models.py` | `pytest` + `pytest-django` |
| Task tests | `<app>/tests/test_tasks.py` | `pytest` + `celery.contrib.pytest` |

Key testing principles:

- Test the **service layer** extensively — it contains all business logic.
- Use **factory functions or `pytest` fixtures** instead of raw `Model.objects.create()`.
- Mock external services (email, Google OAuth, Slack) in tests.
- Test **edge cases**: expired tokens, duplicate registrations, race conditions, disabled accounts.
- Test **serializer validation** for both valid and invalid inputs.

---

## Security Reporting

If you discover a security vulnerability, **do not open a public issue**.

Instead, report it privately:

1. Email the maintainer directly (see `README.md` for contact information).
2. Include a detailed description of the vulnerability.
3. Provide steps to reproduce the issue.
4. Allow reasonable time for the fix before public disclosure.

### Security Considerations for Contributors

When contributing code, keep these security practices in mind:

- **Never store raw tokens.** All verification, reset, and refresh tokens are SHA-256 hashed before database storage.
- **Never log sensitive data.** No passwords, raw tokens, or PII in log output.
- **Use generic error messages** on public endpoints to prevent enumeration attacks.
- **Apply rate limiting** to any new authentication or public-facing endpoint via `django-ratelimit`.
- **Use `transaction.atomic()`** for operations that modify multiple database records.
- **Validate all inputs** at the serializer level — never trust client data.
- **Use `update_fields`** on `model.save()` to avoid unintended field overwrites.

---

## Questions?

If you have questions about the codebase, architecture, or contribution process, open a [GitHub Discussion](https://github.com/Him-Anshu26/ai-ops/discussions) or reach out to the maintainer.

Thank you for contributing to AI Ops! 🚀
