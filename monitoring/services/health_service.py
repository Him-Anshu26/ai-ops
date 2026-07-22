"""
Health Service — Single Source of Truth for Application Health Checks.

This module is the sole owner of all health-check logic.
API views must only call ``get_health_status()`` and return
the resulting dictionary — no business logic in the view layer.

Architecture:

    get_health_status()              ← public orchestrator (never crashes)
        ├── _check_application()     ← always healthy if code reaches here
        ├── _check_database()        ← Django DB connection + cursor test
        ├── _check_redis()           ← redis-py ping via CELERY_BROKER_URL
        ├── _check_celery()          ← broker connectivity + worker detection
        ├── _check_celery_beat()     ← structured placeholder (extensible)
        └── _build_response()        ← assemble final dict with metadata
"""

import logging
import socket
import time
from datetime import datetime, timezone
from typing import Any

import django
from django.conf import settings
from django.db import connections

from ai_ops.celery import app as celery_app


logger = logging.getLogger(__name__)


# Constants

# Captured once at import time.
# Used to calculate server uptime for the health response.
_START_TIME: float = time.monotonic()

_HEALTHY: str = "healthy"
_UNHEALTHY: str = "unhealthy"
_UNKNOWN: str = "unknown"

# Timeout for Celery worker inspect ping (seconds).
_CELERY_PING_TIMEOUT: float = 2.0

# Timeout for Redis PING (seconds).
_REDIS_SOCKET_TIMEOUT: int = 3

# Timeout for Celery broker connection (seconds).
_BROKER_CONNECTION_TIMEOUT: int = 3


# Public API

def get_health_status() -> dict[str, Any]:
    """
    Orchestrate all health checks and return a consistent response.

    This is the single public entry point for the health service.
    It **never** raises — any unexpected exception is caught, logged,
    and surfaced as an unhealthy response.

    Returns:
        A JSON-serialisable dictionary containing the status of every
        subsystem, metadata, and timing information.
    """

    logger.info("Health check started.")

    check_start = time.monotonic()

    try:
        checks = {
            "application": _check_application(),
            "database": _check_database(),
            "redis": _check_redis(),
            "celery": _check_celery(),
            "celery_beat": _check_celery_beat(),
        }

        return _build_response(checks, check_start)

    except Exception:
        logger.exception("Unexpected exception during health check.")

        return _fallback_response(check_start)


# Private Health Checks

def _check_application() -> dict[str, Any]:
    """
    Verify the Django application is running.

    If execution reaches this function the application process is
    alive, so the check always returns healthy.
    """

    logger.info("Application healthy.")

    return {"status": _HEALTHY}


def _check_database() -> dict[str, Any]:
    """
    Verify database connectivity using the default Django connection.

    Opens a cursor and executes ``SELECT 1`` to confirm the database
    is reachable and can process queries.
    """

    try:
        connection = connections["default"]
        connection.ensure_connection()

        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()

        logger.info("Database healthy.")

        return {
            "status": _HEALTHY,
            "backend": connection.vendor,
        }

    except Exception as exc:
        logger.error("Database connection failed. error=%s", exc)

        return {
            "status": _UNHEALTHY,
            "error": str(exc),
        }


def _check_redis() -> dict[str, Any]:
    """
    Verify Redis connectivity by sending a PING command.

    Parses the broker URL from ``settings.CELERY_BROKER_URL``
    and uses the ``redis`` library directly so the check is
    independent of Celery's internal state.
    """

    try:
        import redis

        broker_url: str = getattr(settings, "CELERY_BROKER_URL", "")

        if not broker_url:
            logger.warning(
                "Redis check skipped. CELERY_BROKER_URL is not configured."
            )
            return {
                "status": _UNHEALTHY,
                "error": "CELERY_BROKER_URL is not configured.",
            }

        client = redis.Redis.from_url(
            broker_url,
            socket_timeout=_REDIS_SOCKET_TIMEOUT,
        )
        client.ping()
        client.close()

        logger.debug("Redis healthy.")

        return {"status": _HEALTHY}

    except Exception as exc:
        logger.error("Redis unavailable. error=%s", exc)

        return {
            "status": _UNHEALTHY,
            "error": str(exc),
        }


def _check_celery() -> dict[str, Any]:
    """
    Verify Celery broker connectivity and worker availability.

    Broker:
        Uses the Celery application's connection pool to open a
        read connection and confirm the broker is reachable.

    Worker:
        Uses ``celery_app.control.inspect().ping()`` which broadcasts
        a ping to all workers and waits for responses.
    """

    # Broker check
    try:
        conn = celery_app.connection_for_read()
        conn.ensure_connection(max_retries=0, timeout=_BROKER_CONNECTION_TIMEOUT)
        conn.close()

    except Exception as exc:
        logger.error("Celery broker unavailable. error=%s", exc)

        return {
            "status": _UNHEALTHY,
            "broker": _UNHEALTHY,
            "error": str(exc),
        }

    # Worker check
    try:
        inspector = celery_app.control.inspect(
            timeout=_CELERY_PING_TIMEOUT,
        )
        ping_response = inspector.ping()

        if ping_response:
            worker_names = list(ping_response.keys())

            logger.debug("Celery healthy. workers=%s", worker_names)

            return {
                "status": _HEALTHY,
                "broker": _HEALTHY,
                "workers": len(worker_names),
            }

        logger.warning("Celery worker unavailable. No workers responded to ping.")

        return {
            "status": _UNHEALTHY,
            "broker": _HEALTHY,
            "workers": 0,
            "error": "No workers responded to ping.",
        }

    except Exception as exc:
        logger.error("Celery worker check failed. error=%s", exc)

        return {
            "status": _UNHEALTHY,
            "broker": _HEALTHY,
            "error": str(exc),
        }


def _check_celery_beat() -> dict[str, Any]:
    """
    Determine Celery Beat scheduler health.

    Direct verification of the Beat process is not practical
    without a shared heartbeat mechanism (e.g. a timestamp
    written to Redis or the database on each tick). This check
    is structured identically to the other checks so it can be
    swapped for a real implementation later.

    Future implementation ideas:
        - Beat writes a heartbeat timestamp to Redis on each tick.
        - This check reads the timestamp and compares against
          a staleness threshold.
        - If the timestamp is missing or stale, report unhealthy.
    """

    logger.debug("Celery Beat check not implemented. Reporting unknown.")

    return {
        "status": _UNKNOWN,
        "info": "Direct verification not yet implemented.",
    }


# Response Builder

def _build_response(
    checks: dict[str, dict[str, Any]],
    check_start: float,
) -> dict[str, Any]:
    """
    Assemble the final health-check response dictionary.

    The overall status is ``healthy`` only when **every** individual
    check reports ``healthy``. A single ``unhealthy`` check degrades
    the overall status.

    The ``unknown`` status (e.g. Celery Beat) does **not** degrade
    the overall status.
    """

    overall = _HEALTHY

    for check in checks.values():
        if check.get("status") == _UNHEALTHY:
            overall = _UNHEALTHY
            break

    elapsed_ms = (time.monotonic() - check_start) * 1000

    response: dict[str, Any] = {
        "status": overall,
        **checks,
        "environment": _get_environment(),
        "api_version": _get_api_version(),
        "version": django.get_version(),
        "hostname": socket.gethostname(),
        "timestamp": _utc_now_iso(),
        "uptime_seconds": _get_uptime_seconds(),
        "response_time_ms": round(elapsed_ms, 2),
    }

    logger.info(
        "Health check completed. status=%s response_time_ms=%.2f",
        overall,
        response["response_time_ms"],
    )

    return response


def _fallback_response(check_start: float) -> dict[str, Any]:
    """
    Minimal unhealthy response returned when the orchestrator
    itself raises an unexpected exception.
    """

    elapsed_ms = (time.monotonic() - check_start) * 1000

    return {
        "status": _UNHEALTHY,
        "environment": _get_environment(),
        "api_version": _get_api_version(),
        "version": django.get_version(),
        "hostname": socket.gethostname(),
        "timestamp": _utc_now_iso(),
        "uptime_seconds": _get_uptime_seconds(),
        "response_time_ms": round(elapsed_ms, 2),
    }


# Helpers

def _get_api_version() -> str:
    """Read the API version from ``SPECTACULAR_SETTINGS``."""

    spectacular = getattr(settings, "SPECTACULAR_SETTINGS", {})
    return spectacular.get("VERSION", "unknown")


def _get_environment() -> str:
    """
    Derive the current environment from ``settings.DEBUG``.

    Returns ``"development"`` when DEBUG is True,
    ``"production"`` otherwise.
    """

    return "development" if getattr(settings, "DEBUG", False) else "production"


def _utc_now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string."""

    return datetime.now(tz=timezone.utc).isoformat(timespec="seconds")


def _get_uptime_seconds() -> int:
    """Return server uptime in whole seconds since module import."""

    return int(time.monotonic() - _START_TIME)
