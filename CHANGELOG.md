# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Placeholder for upcoming features and improvements.

### Changed
- Nothing yet.

### Fixed
- Nothing yet.

---

## [1.0.0] — 2026-07-20

### Added

#### Authentication & User Management (`accounts`)
- Custom `User` model with email-based authentication — username field removed entirely.
- JWT authentication via `djangorestframework-simplejwt` with 15-minute access tokens and 7-day refresh tokens.
- Session-based token management — each login creates a database-tracked `UserSession` with SHA-256 hashed refresh tokens.
- Google OAuth 2.0 login flow with `google-auth` ID token verification, automatic user provisioning, and internal JWT issuance.
- Google OAuth test page served via Django template with environment-injected client ID.
- Mandatory email verification with secure SHA-256 hashed tokens and 24-hour expiry.
- Token-based password reset with SHA-256 hashed tokens and 30-minute expiry; invalidates all active sessions on reset.
- Resend verification email endpoint with email enumeration prevention.
- Soft logout preserving session audit history (`is_active=False`).
- Custom `UserManager` for email-based user creation.
- `RegisterSerializer`, `LoginSerializer`, `EmailSerializer`, `PasswordResetConfirmSerializer`, `RefreshTokenSerializer`, and `GoogleLoginSerializer` with field-level and object-level validation.

#### Monitoring (`monitoring`)
- `Service` model with name, auto-generated slug (collision-resistant), description, status (`active`/`down`/`maintenance`), soft delete, and `created_by` foreign key with `PROTECT` on delete.
- `Log` model with structured fields: status (`success`/`warning`/`error`), severity (`low`/`medium`/`high`), HTTP status code (100–599 validated), response time in milliseconds, message, and JSON metadata.
- `LogViewSet` with create, list, and retrieve actions — update and delete intentionally blocked.
- Read/write serializer separation: `LogWriteSerializer` for ingestion, `LogReadSerializer` for API responses.
- Cursor-based pagination via `LogCursorPagination` for efficient time-series data traversal.
- Advanced filtering via `django-filter`: service, status, status code, time range (`created_after`/`created_before`), response time range (`min_response_time`/`max_response_time`), and case-insensitive message search.
- Ordering support on `created_at` and `response_time_ms` fields.

#### Alert Engine (`monitoring.services.alert_service`)
- Rule-based alert engine triggered asynchronously via Celery on log creation.
- Error detection rule — triggers on `error` log status or HTTP 5xx status codes.
- High latency detection rule — triggers when `response_time_ms` exceeds 1000ms threshold.
- Automatic severity classification: `critical` for HTTP 503, `high` for other 5xx codes, `medium`/`high` for latency buckets.
- Alert key generation with latency buckets (`medium`/`high`/`very_high`) for granular deduplication.
- `UniqueConstraint` on `(service, alert_type, alert_key)` for active alerts prevents duplicate incidents.
- 30-second cooldown window to prevent alert flooding.
- Atomic trigger count increment (`F('trigger_count') + 1`) on repeated alert matches.
- Row-level locking via `SELECT FOR UPDATE` to handle concurrent alert processing.
- `IntegrityError` fallback with recovery logic for race conditions.

#### Alert Management (`alerts`)
- `Alert` model with type (`error`/`downtime`/`high_latency`), severity (`low`/`medium`/`high`/`critical`), lifecycle status (`open`/`acknowledged`/`resolved`), trigger count, resolution notes, and timestamp tracking.
- `AlertViewSet` with create, list, retrieve, and custom `resolve` workflow action — generic update and delete intentionally blocked.
- Immutable incident record pattern — alerts are append-only with controlled state transitions.
- Default queryset filters to show only unresolved alerts (`open`/`acknowledged`) unless `status` query parameter is explicitly provided.
- Read/write/resolve serializer separation: `AlertWriteSerializer`, `AlertReadSerializer`, `AlertResolveSerializer`.
- Cursor-based pagination via `AlertCursorPagination`.
- Advanced filtering via `django-filter`: service, status, alert type, severity, created/triggered time ranges, trigger count range, and case-insensitive message search.
- Ordering support on `created_at`, `severity`, `trigger_count`, and `last_triggered_at`.

#### Notification Service (`alerts.services`)
- Provider-isolated notification orchestration with per-provider error handling — provider failures never interrupt alert processing.
- SMTP-based email notification delivery via Django's `send_mail` with configurable `ALERT_EMAIL_RECIPIENTS`.
- Structured plain-text email body with alert ID, service name, type, severity, status, message, trigger count, and timestamps.
- HTML email template (`alert_created.html`) and plain-text fallback (`alert_created.txt`) for alert notifications.
- `EMAIL_NOTIFICATIONS_ENABLED` and `SLACK_NOTIFICATIONS_ENABLED` feature flags for toggling notification channels.
- Slack notification placeholder service with structured integration points for Incoming Webhooks.

#### Background Processing
- Celery worker configuration with Redis as broker and result backend.
- Celery Beat periodic task scheduling for all cleanup operations.
- `process_log_for_alerts_task` — asynchronous alert evaluation triggered via `transaction.on_commit()` after log creation.
- `dispatch_alert_notifications_task` — asynchronous notification dispatch triggered via `transaction.on_commit()` after alert creation/update.
- `cleanup_accounts` — hourly task: expired email verification tokens, expired password reset tokens, inactive sessions (90-day retention).
- `cleanup_monitoring` — daily at 3:00 AM: monitoring logs older than 120 days.
- `cleanup_alerts_task` — daily at 4:00 AM: resolved alerts older than 90 days.
- Exponential backoff with jitter retry strategy for `ConnectionError` and `DatabaseError`, max 5 retries, 300-second max backoff.
- Celery soft time limit (300s) and hard time limit (600s).

#### API Documentation
- OpenAPI 3.0 schema generation via `drf-spectacular`.
- Interactive Swagger UI at `/api/v1/docs/`.
- ReDoc documentation viewer at `/api/v1/docs/redoc/`.
- Raw OpenAPI JSON schema at `/api/v1/schema/`.
- Rich request/response examples via `@extend_schema` decorators on all endpoints.

#### Admin Interface
- Custom `UserAdmin` with search and filter by verification status.
- `ServiceAdmin` with bulk status actions (`active`/`down`/`maintenance`) and auto-assigned `created_by`.
- Read-only `LogAdmin` with formatted JSON metadata display — add, edit, and delete disabled.
- `AlertAdmin` with bulk lifecycle actions (`mark_open`/`mark_acknowledged`/`mark_resolved`), autocomplete fields, date hierarchy, fieldsets, and `list_select_related` optimization.

#### Infrastructure & Configuration
- Split settings architecture: `base.py`, `dev.py`, `prod.py`.
- Environment variable management via `django-environ` with automatic `.env.dev`/`.env.prod` file loading based on `DJANGO_SETTINGS_MODULE`.
- API versioning under `/api/v1/` namespace.
- PostgreSQL as primary database with `psycopg2-binary` adapter.
- ASGI and WSGI entry points.

#### Database Optimizations
- Composite indexes on `(service, status)`, `(service, created_at)`, `(created_by, status, is_deleted)` for monitoring queries.
- Composite indexes on `(service, status)`, `(service, alert_type)`, `(service, severity)`, `(status, last_triggered_at)` for alert queries.
- Partial indexes: `idx_error_logs` (error status only), `idx_active_alerts_per_service` (non-resolved only), `idx_active_ser_last_triggered` (non-resolved only).
- Conditional unique constraints: `unique_active_service_name_per_user`, `unique_active_service_slug_per_user`, `unique_active_alert_per_service_type_alert_key`.
- `select_related` on all ViewSet querysets to prevent N+1 queries.
- `select_for_update` for row-level locking in concurrent alert processing.
- Composite indexes on `(session_id, is_active)` and `(user, is_active)` for session lookups.

### Security
- SHA-256 hashing for all verification, password reset, and refresh tokens before database storage.
- Refresh token validation via hash comparison against database-stored session record.
- Django PBKDF2 password hashing (default).
- Email enumeration prevention with generic responses on registration, verification resend, and password reset endpoints.
- IP-based rate limiting via `django-ratelimit` on all authentication endpoints: register (5/min), login (10/min), email verification (5/min), password reset (5/min), refresh (10/min), Google login (10/min).
- Global anonymous throttling at 100 requests/day via DRF `AnonRateThrottle`.
- Django's built-in password validators: similarity, minimum length, common password, numeric-only.
- CSRF middleware enabled.
- Production security hardening: `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_HSTS_SECONDS` (1 year), `SECURE_HSTS_INCLUDE_SUBDOMAINS`, `SECURE_HSTS_PRELOAD`, `SECURE_CONTENT_TYPE_NOSNIFF`, `X_FRAME_OPTIONS=DENY`.
- JWT signed with HS256 algorithm using Django `SECRET_KEY`.
- All secrets managed via environment variables — no hardcoded credentials.

### Performance
- Cursor-based pagination on both logs and alerts for scalable large-dataset traversal without offset performance degradation.
- `select_related` joins on all ViewSet querysets to eliminate N+1 query patterns.
- Atomic field updates via `F()` expressions for trigger count increments — avoids read-modify-write race conditions.
- `update_fields` parameter on model saves to minimize database write overhead.
- Row-level locking (`select_for_update`) scoped to individual alert processing transactions.
- Partial database indexes to accelerate filtered queries on active/error subsets.
- Asynchronous task processing via Celery offloads alert evaluation and notification dispatch from the request/response cycle.
- `transaction.on_commit()` ensures Celery tasks only execute after successful database commits, preventing race conditions.

### Fixed
- Race condition in concurrent alert creation resolved with `SELECT FOR UPDATE` row-level locking and `IntegrityError` recovery fallback.
- Email normalization (case-insensitive, trimmed) applied consistently across registration, login, verification resend, password reset, and Google OAuth flows to prevent duplicate accounts.
- `transaction.on_commit()` used for Celery task dispatch to prevent `DoesNotExist` errors when workers execute before transaction commit.

---

## [0.2.0] — 2026-07-18

### Added
- Alert notification dispatch system with email and Slack (placeholder) providers.
- HTML email template for alert notifications (`alert_created.html` and `alert_created.txt`).
- Production-ready `AlertViewSet` with custom `resolve` workflow action.
- `AlertAdmin` with bulk lifecycle actions (open/acknowledge/resolve), autocomplete fields, and date hierarchy.
- Feature flags for notification channels: `EMAIL_NOTIFICATIONS_ENABLED`, `SLACK_NOTIFICATIONS_ENABLED`.

### Changed
- Alert engine notification dispatch moved to Celery background tasks with `transaction.on_commit()` safety.
- Alert model field renamed from `alert_message` to `message` for consistency.
- Alerts app configuration standardized.

### Performance
- Optimized monitoring task database queries with `select_related("service")` on log fetch.
- Optimized ViewSet queryset with `select_related` to prevent N+1 queries.

### Fixed
- Removed unused import from monitoring URL configuration.

---

## [0.1.0] — 2026-07-15

### Added
- Initial project scaffold with Django 5.2.1 and Django REST Framework 3.16.0.
- Custom `User` model with email-based authentication.
- JWT authentication with `djangorestframework-simplejwt`.
- User registration, login, email verification, password reset, and token refresh endpoints.
- Google OAuth 2.0 login with `google-auth` and `django-allauth`.
- `Service` and `Log` models for monitoring.
- `LogViewSet` with create, list, and retrieve actions.
- `Alert` model with lifecycle management.
- Celery and Celery Beat integration with Redis.
- Automated cleanup tasks for expired tokens, inactive sessions, old logs, and resolved alerts.
- OpenAPI 3.0 documentation via `drf-spectacular` with Swagger UI and ReDoc.
- Django admin customization for users, services, logs, and alerts.
- Split settings for development and production environments.
- Environment variable management via `django-environ`.
- Structured logging framework with per-app loggers.

### Security
- SHA-256 token hashing for verification, reset, and refresh tokens.
- IP-based rate limiting on authentication endpoints via `django-ratelimit`.
- Production HTTPS/HSTS configuration.
- Email enumeration prevention on public auth endpoints.

### Fixed
- Email verification authentication configuration aligned with project requirements.
- Superuser creation constraints enforced in custom `UserManager`.
- Debug print statements replaced with structured logging across account lifecycle.
- Production email configuration simplified.

---

[Unreleased]: https://github.com/Him-Anshu26/ai-ops/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/Him-Anshu26/ai-ops/compare/v0.2.0...v1.0.0
[0.2.0]: https://github.com/Him-Anshu26/ai-ops/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/Him-Anshu26/ai-ops/releases/tag/v0.1.0
