# =============================================================================
# Dockerfile — AI Ops (Django REST Framework)
# =============================================================================
# Production-grade Dockerfile for the AI Ops backend.
# Optimized for security, layer caching, and minimal image size.
#
# Build notes:
#   - Single-stage build keeps the structure simple. A true multi-stage
#     build (separate builder stage for compiling C extensions, runtime
#     stage for the final image) can be introduced later to remove
#     build tools from the runtime image and shrink the final layer.
# =============================================================================


# -----------------------------------------------------------------------------
# Stage: Base Image
# -----------------------------------------------------------------------------
# Use the official Python 3.13 slim image based on Debian Bookworm.
# The "slim" variant excludes development headers and compilers,
# producing a significantly smaller image (~150 MB vs ~1 GB for full).
#
# Reproducibility: the base image is pinned by digest (multi-arch
# manifest digest). This guarantees bit-for-bit identical builds
# regardless of when or where the image is built. To refresh the
# pin, pull the desired tag locally and inspect its digest:
#     docker pull python:3.13-slim
#     docker inspect python:3.13-slim --format '{{index .RepoDigests 0}}'
# -----------------------------------------------------------------------------
FROM python:3.13-slim@sha256:6771159cd4fa5d9bba1258caf0b82e6b73458c694d178ad97c5e925c2d0e1a91 AS base

# OCI image labels — standard annotation keys from the OCI image spec.
# https://github.com/opencontainers/image-spec/blob/main/annotations.md
LABEL org.opencontainers.image.title="AI Ops" \
      org.opencontainers.image.description="Production-grade backend for real-time service monitoring, intelligent alert generation, and incident lifecycle management." \
      org.opencontainers.image.source="https://github.com/Him-Anshu26/ai-ops" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.vendor="AI Ops" \
      org.opencontainers.image.version="1.0.0"


# -----------------------------------------------------------------------------
# Python Environment Variables
# -----------------------------------------------------------------------------

# Prevent Python from writing .pyc bytecode files to disk.
# In containers, bytecode caching provides no benefit — the filesystem
# is ephemeral, and skipping .pyc writes reduces image size and avoids
# stale cache issues.
ENV PYTHONDONTWRITEBYTECODE=1

# Force Python's stdout and stderr to be unbuffered.
# Without this, log output may be held in a buffer and never reach
# Docker's log driver (docker logs). This is critical for observability
# in production — you need real-time access to application logs.
ENV PYTHONUNBUFFERED=1

# Disable pip's version check on every install.
# Speeds up builds and avoids unnecessary network calls.
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Disable pip's cache directory.
# Cached wheels serve no purpose inside a container — the image is
# immutable after build. Disabling the cache reduces the final layer size.
ENV PIP_NO_CACHE_DIR=1

# Gunicorn worker count.
# The default of 4 follows the (2 × CPU cores) + 1 formula for a
# typical 2-core host. Override at runtime, e.g.:
#     docker run -e WEB_CONCURRENCY=8 ...
#     docker compose up -e WEB_CONCURRENCY=8
#     kubectl set env deployment/ai-ops WEB_CONCURRENCY=8
# No rebuild required.
ENV WEB_CONCURRENCY=4

# Container port Gunicorn binds to.
# Override at runtime to match the host's published port without
# rebuilding the image:
#     docker run -e PORT=8080 -p 8080:8080 ...
ENV PORT=8000


# -----------------------------------------------------------------------------
# System Dependencies
# -----------------------------------------------------------------------------
# Install the minimal set of OS packages required at runtime:
#
#   libpq5  — PostgreSQL client library required by psycopg2 at runtime.
#             Even though psycopg2-binary bundles its own libpq, the
#             system library ensures compatibility and is required if
#             you later switch to the non-binary psycopg2 (recommended
#             for production by the psycopg2 maintainers).
#
# NOTE on build dependencies (build-essential, gcc, libpq-dev):
#   These are only required when compiling C extensions (e.g. the
#   non-binary psycopg2, or other packages without prebuilt wheels).
#   Since requirements.txt currently uses psycopg2-binary, no
#   compilation is needed at build time and they are intentionally
#   omitted to keep the image slim.
#
#   When you switch to non-binary psycopg2 (recommended for production),
#   add a multi-stage build:
#       FROM python:3.13-slim AS builder
#       RUN apt-get install -y build-essential gcc libpq-dev
#       RUN pip wheel --wheel-dir=/wheels -r requirements.txt
#       FROM python:3.13-slim
#       COPY --from=builder /wheels /wheels
#       RUN pip install --no-index --find-links=/wheels /wheels/*
#   This keeps the build tools out of the runtime image.
#
# NOTE on mime-support:
#   Removed. Most Django APIs don't depend on it — the package only
#   provides /etc/mime.types for OS-level MIME type detection, which
#   Django does not use for static file serving or email handling.
#
# The rm -rf /var/lib/apt/lists/* clears the apt package index cache,
# reclaiming ~30 MB from the image layer.
# -----------------------------------------------------------------------------
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpq5 \
    && rm -rf /var/lib/apt/lists/*


# -----------------------------------------------------------------------------
# Working Directory
# -----------------------------------------------------------------------------
# Set /app as the working directory for all subsequent instructions.
# This creates the directory if it does not exist and ensures all
# COPY, RUN, and CMD instructions execute relative to /app.
# -----------------------------------------------------------------------------
WORKDIR /app


# -----------------------------------------------------------------------------
# Python Dependencies (Layer Caching Optimization)
# -----------------------------------------------------------------------------
# Copy ONLY requirements.txt first, before the rest of the source code.
#
# Docker builds layers top-down. If a layer's inputs haven't changed,
# Docker reuses the cached layer. By isolating the dependency install:
#
#   1. requirements.txt changes infrequently.
#   2. Source code changes on every commit.
#
# This means `pip install` is only re-executed when dependencies change,
# not on every code edit — saving minutes on each build.
# -----------------------------------------------------------------------------
COPY requirements.txt .

RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt



# -----------------------------------------------------------------------------
# Application Source Code
# -----------------------------------------------------------------------------
# Copy the entire application source into the container.
# The .dockerignore file ensures only necessary files are included —
# no .git, venv, .env files, IDE configs, or local artifacts.
# -----------------------------------------------------------------------------
COPY . .


# -----------------------------------------------------------------------------
# Collect Static Files
# -----------------------------------------------------------------------------
# Run Django's collectstatic to gather all static assets into STATIC_ROOT.
# This must happen at build time so the container is ready to serve
# static files immediately on startup.
#
# --noinput prevents Django from prompting for confirmation.
#
# Why we do NOT use `|| true` here:
#   Silently swallowing a collectstatic failure would ship a broken
#   image to production. A failed collectstatic is a hard build error
#   and must fail the build so it can be fixed before deployment.
#
# DJANGO_SETTINGS_MODULE is set inline for this command only —
# it is NOT persisted as an ENV, keeping the image environment-agnostic.
# The SECRET_KEY placeholder is required because Django's settings
# import chain demands it, but collectstatic does not use it.
#
# Placeholder values below satisfy the import-time requirements of
# the settings module. The set can be shrunk by making the settings
# tolerate missing values during build (e.g. os.environ.get with
# sensible defaults), at which point most of these can be removed.
# -----------------------------------------------------------------------------
RUN DJANGO_SETTINGS_MODULE=ai_ops.settings.prod \
    SECRET_KEY=collectstatic-placeholder \
    DB_NAME=placeholder \
    DB_USER=placeholder \
    DB_PASSWORD=placeholder \
    DB_HOST=placeholder \
    DB_PORT=5432 \
    CELERY_BROKER_URL=redis://placeholder:6379/0 \
    CELERY_RESULT_BACKEND=redis://placeholder:6379/0 \
    EMAIL_PROVIDER=placeholder \
    EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend \
    EMAIL_HOST=placeholder \
    EMAIL_PORT=587 \
    EMAIL_USE_TLS=True \
    EMAIL_HOST_USER=placeholder \
    EMAIL_HOST_PASSWORD=placeholder \
    DEFAULT_FROM_EMAIL=placeholder \
    ALERT_EMAIL_RECIPIENTS=placeholder \
    GOOGLE_CLIENT_ID=placeholder \
    GOOGLE_CLIENT_SECRET=placeholder \
    ALLOWED_HOSTS=placeholder \
    python manage.py collectstatic --noinput


# -----------------------------------------------------------------------------
# Non-Root User
# -----------------------------------------------------------------------------
# Create a dedicated system user and group with no home directory,
# no login shell, and no password.
#
# Running as root inside a container is a security risk:
#   - A container escape exploit gains root on the host.
#   - Malicious code can modify system binaries.
#   - File permission issues when mounting volumes.
#
# The `chown` transfers ownership of /app to the new user so the
# application can read its own source files and write to any
# runtime directories (e.g., logs, media uploads).
# -----------------------------------------------------------------------------
RUN groupadd --system appgroup \
    && useradd --system --no-create-home --gid appgroup appuser \
    && chown -R appuser:appgroup /app

# Switch to the non-root user for all subsequent instructions and
# the container's runtime process.
USER appuser


# -----------------------------------------------------------------------------
# Expose Port
# -----------------------------------------------------------------------------
# Declare that the container listens on the port defined by the PORT
# env var (default 8000). This is documentation for operators — it
# does not publish the port. Use `docker run -p 8000:8000` or
# Docker Compose `ports:` to publish.
# -----------------------------------------------------------------------------
EXPOSE 8000


# -----------------------------------------------------------------------------
# Health Check
# -----------------------------------------------------------------------------
# Periodically verify the application is responsive.
# curl is not available in slim images, so we use Python's urllib.
# Docker marks the container as "unhealthy" if this command fails
# 3 consecutive times (retries), enabling orchestrators like
# Docker Compose or Kubernetes to restart it automatically.
#
# We hit a dedicated health endpoint rather than Swagger UI:
#   /api/v1/docs/  — may be disabled or behind auth in production.
#   /api/v1/health/ — a lightweight, unauthenticated liveness probe
#                     intended for orchestrators.
# -----------------------------------------------------------------------------
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
   CMD python -c "import sys, urllib.request; r=urllib.request.urlopen('http://localhost:8000/api/v1/health/'); sys.exit(0 if r.status==200 else 1)"

# -----------------------------------------------------------------------------
# Default Command
# -----------------------------------------------------------------------------
# Start Gunicorn, the production WSGI server.
#
#   ai_ops.wsgi:application
#       Points to the WSGI application object defined in ai_ops/wsgi.py.
#
#   --bind 0.0.0.0:${PORT}
#       Listen on all network interfaces inside the container, on the
#       port defined by the PORT env var (default 8000). Required for
#       Docker's port forwarding to work. Shell form is used so the
#       runtime PORT env var is expanded.
#
#   --workers ${WEB_CONCURRENCY}
#       Number of Gunicorn worker processes, read from the
#       WEB_CONCURRENCY env var (default 4). A common formula is
#       (2 × CPU cores) + 1 — tune per host without rebuilding.
#
#   --timeout 120
#       Kill and restart a worker if it hasn't responded within
#       120 seconds. Prevents hung workers from consuming resources.
#
#   --access-logfile -
#       Write access logs to stdout so Docker's log driver captures them.
#
#   --error-logfile -
#       Write error logs to stderr so Docker's log driver captures them.
# -----------------------------------------------------------------------------
CMD ["sh", "-c", "gunicorn ai_ops.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers ${WEB_CONCURRENCY:-4} --timeout 120 --access-logfile - --error-logfile -"]
