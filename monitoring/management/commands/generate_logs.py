"""
Management command to generate bulk monitoring log data.

Thin command — only responsible for:

    Parse arguments
    ↓
    Validate arguments
    ↓
    Generate batched log objects
    ↓
    bulk_create()
    ↓
    Call BenchmarkService
    ↓
    Print summary

All benchmarking logic lives in BenchmarkService.
"""

import random as random_module
import logging

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from monitoring.models import Log, LogStatus, Service
from monitoring.services.benchmark_service import BenchmarkService


logger = logging.getLogger(__name__)


# ----------------------------------------------------------------
# Realistic Data Templates
# ----------------------------------------------------------------

_SUCCESS_MESSAGES = [
    "GET /api/v1/services/ 200 OK",
    "POST /api/v1/logs/ 201 Created",
    "GET /api/v1/health/ 200 OK",
    "GET /api/v1/logs/?status=success 200 OK",
    "Authentication successful for user",
    "Database connection pool healthy",
    "Cache hit for service status lookup",
    "Celery task completed successfully",
    "Webhook delivery confirmed",
    "SSL certificate validation passed",
]

_WARNING_MESSAGES = [
    "GET /api/v1/logs/ 429 Too Many Requests",
    "Response time exceeded threshold: 1200ms",
    "Database connection pool at 80% capacity",
    "Memory usage above warning threshold",
    "Rate limit approaching for client IP",
    "Slow query detected: 850ms",
    "Retry attempt 2/5 for webhook delivery",
    "Cache eviction rate above normal",
    "Disk usage at 75% capacity",
    "DNS resolution latency elevated",
]

_ERROR_MESSAGES = [
    "POST /api/v1/logs/ 500 Internal Server Error",
    "GET /api/v1/services/ 502 Bad Gateway",
    "Database connection refused",
    "GET /api/v1/health/ 503 Service Unavailable",
    "Celery worker heartbeat lost",
    "Redis connection timeout after 3000ms",
    "SSL certificate expired for upstream service",
    "Unhandled exception in alert processing pipeline",
    "Memory allocation failed: out of memory",
    "Disk I/O error: read-only filesystem",
]

_STATUS_CODE_MAP = {
    LogStatus.SUCCESS: [200, 200, 200, 200, 201, 201, 204, 301],
    LogStatus.WARNING: [301, 400, 403, 404, 408, 429, 429, 429],
    LogStatus.ERROR: [500, 500, 500, 502, 502, 503, 503, 504],
}

_MESSAGE_MAP = {
    LogStatus.SUCCESS: _SUCCESS_MESSAGES,
    LogStatus.WARNING: _WARNING_MESSAGES,
    LogStatus.ERROR: _ERROR_MESSAGES,
}

_SEVERITY_MAP = {
    LogStatus.SUCCESS: ["low", "low", "low", "medium"],
    LogStatus.WARNING: ["medium", "medium", "high"],
    LogStatus.ERROR: ["high", "high", "high", "medium"],
}

_RESPONSE_TIME_RANGES = {
    LogStatus.SUCCESS: (10, 500),
    LogStatus.WARNING: (300, 3000),
    LogStatus.ERROR: (500, 5000),
}

_HTTP_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE"]

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    "python-requests/2.31.0",
    "curl/8.1.2",
    "PostmanRuntime/7.32.3",
]

_ENDPOINTS = [
    "/api/v1/services/",
    "/api/v1/logs/",
    "/api/v1/health/",
    "/api/v1/alerts/",
    "/admin/monitoring/log/",
]


class Command(BaseCommand):
    help = "Generate bulk monitoring log data for benchmarking."

    def add_arguments(self, parser):

        parser.add_argument(
            "--count",
            type=int,
            required=True,
            help="Number of log records to generate.",
        )

        parser.add_argument(
            "--batch-size",
            type=int,
            default=1000,
            help="Number of records per bulk_create batch. Default: 1000.",
        )

        parser.add_argument(
            "--service",
            type=str,
            default=None,
            help="Service name or ID. Uses first available if omitted.",
        )

        parser.add_argument(
            "--status",
            type=str,
            default=None,
            choices=[choice[0] for choice in LogStatus.choices],
            help="Lock all logs to a specific status.",
        )

        parser.add_argument(
            "--random",
            action="store_true",
            default=False,
            help="Use fully random data instead of weighted distribution.",
        )

        parser.add_argument(
            "--seed",
            type=int,
            default=None,
            help="Random seed for deterministic generation.",
        )

        parser.add_argument(
            "--clear-existing",
            action="store_true",
            default=False,
            help="Delete all existing logs before generating.",
        )

        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Simulate generation without writing to the database.",
        )

    def handle(self, *args, **options):

        count = options["count"]
        batch_size = options["batch_size"]
        service_ref = options["service"]
        locked_status = options["status"]
        use_random = options["random"]
        seed = options["seed"]
        clear_existing = options["clear_existing"]
        dry_run = options["dry_run"]

        # ------------------------------------------------
        # Validate
        # ------------------------------------------------

        if count <= 0:
            raise CommandError("--count must be a positive integer.")

        if batch_size <= 0:
            raise CommandError("--batch-size must be a positive integer.")

        service = self._resolve_service(service_ref)

        # ------------------------------------------------
        # Seed
        # ------------------------------------------------

        rng = random_module.Random(seed)

        # ------------------------------------------------
        # Clear existing
        # ------------------------------------------------

        if clear_existing and not dry_run:
            deleted_count, _ = Log.objects.all().delete()
            self.stdout.write(
                self.style.WARNING(
                    f"Cleared {deleted_count} existing log(s)."
                )
            )

        # ------------------------------------------------
        # Generate
        # ------------------------------------------------

        benchmark_result = BenchmarkService.measure_execution_time(
            lambda: self._generate_batches(
                count=count,
                batch_size=batch_size,
                service=service,
                locked_status=locked_status,
                use_random=use_random,
                rng=rng,
                dry_run=dry_run,
            )
        )

        memory = BenchmarkService.measure_memory_usage(lambda: None)

        # ------------------------------------------------
        # Summary
        # ------------------------------------------------

        result = BenchmarkService.format_result(
            label="generate_logs",
            execution_time_ms=benchmark_result,
            memory=memory,
            rows=count,
            dataset_size=count,
        )

        BenchmarkService.print_summary(result, stdout=self.stdout)

    # --------------------------------------------------------
    # Private Helpers
    # --------------------------------------------------------

    def _resolve_service(self, service_ref):
        """
        Resolve a service by name, ID, or pick the first available.
        """

        if service_ref is None:
            service = Service.objects.first()
            if service is None:
                raise CommandError(
                    "No services found. Create a service first."
                )
            return service

        # Try by ID
        if service_ref.isdigit():
            try:
                return Service.objects.get(pk=int(service_ref))
            except Service.DoesNotExist:
                raise CommandError(
                    f"Service with ID '{service_ref}' does not exist."
                )

        # Try by name
        try:
            return Service.objects.get(name=service_ref)
        except Service.DoesNotExist:
            raise CommandError(
                f"Service with name '{service_ref}' does not exist."
            )

    def _generate_batches(
        self, count, batch_size, service, locked_status,
        use_random, rng, dry_run,
    ):
        """
        Generate logs in batches and bulk_create each batch.
        """

        created = 0

        while created < count:
            current_batch_size = min(batch_size, count - created)

            batch = [
                self._build_log(
                    service=service,
                    locked_status=locked_status,
                    use_random=use_random,
                    rng=rng,
                )
                for _ in range(current_batch_size)
            ]

            if not dry_run:
                Log.objects.bulk_create(batch)

            created += current_batch_size

            self.stdout.write(f"  {created} / {count}")

            # Release references
            del batch

    def _build_log(self, service, locked_status, use_random, rng):
        """
        Build a single Log instance with realistic data.
        """

        if locked_status:
            status = locked_status
        elif use_random:
            status = rng.choice([c[0] for c in LogStatus.choices])
        else:
            # Weighted distribution: 70% success, 20% warning, 10% error
            status = rng.choices(
                [LogStatus.SUCCESS, LogStatus.WARNING, LogStatus.ERROR],
                weights=[70, 20, 10],
            )[0]

        status_code = rng.choice(_STATUS_CODE_MAP[status])
        message = rng.choice(_MESSAGE_MAP[status])
        severity = rng.choice(_SEVERITY_MAP[status])

        low, high = _RESPONSE_TIME_RANGES[status]
        response_time_ms = rng.randint(low, high)

        metadata = {
            "endpoint": rng.choice(_ENDPOINTS),
            "method": rng.choice(_HTTP_METHODS),
            "user_agent": rng.choice(_USER_AGENTS),
            "ip_address": f"{rng.randint(1, 255)}.{rng.randint(0, 255)}.{rng.randint(0, 255)}.{rng.randint(1, 255)}",
            "request_id": f"{rng.randint(100000, 999999):06d}",
        }

        return Log(
            service=service,
            status=status,
            severity=severity,
            status_code=status_code,
            response_time_ms=response_time_ms,
            message=message,
            metadata=metadata,
        )
