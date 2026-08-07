"""
Benchmark Service — Reusable Performance Measurement Infrastructure.

Stateless utility service for capturing execution time, memory usage,
queryset performance, API response metrics, and management command
benchmarks.

All methods are ``@staticmethod`` — no instance attributes, no global
mutable state.

Architecture:

    BenchmarkService
        ├── capture_system_info()          ← OS, Python, Django, PG, CPU, RAM
        ├── measure_execution_time()       ← time.perf_counter() wrapper
        ├── measure_memory_usage()         ← psutil before/after/diff
        ├── measure_queryset_time()        ← count/first/exists/iterator/list
        ├── measure_api_response()         ← APIClient request wrapper
        ├── measure_admin_response()       ← Django Client request wrapper
        ├── benchmark_queryset()           ← high-level queryset benchmark
        ├── benchmark_api()                ← high-level API benchmark
        ├── benchmark_function()           ← high-level callable benchmark
        ├── benchmark_management_command() ← call_command benchmark
        ├── write_csv()                    ← append results to CSV
        ├── append_markdown()              ← append formatted results to MD
        ├── format_result()                ← normalize raw data into schema
        ├── calculate_improvement()        ← before/after comparison
        └── print_summary()               ← readable console output
"""

import csv
import logging
import os
import platform
import sys
import time
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Any, Callable, Optional

import django
import psutil
from django.conf import settings
from django.core.management import call_command
from django.db.models import QuerySet


logger = logging.getLogger(__name__)


# ----------------------------------------------------------------
# Constants
# ----------------------------------------------------------------

BENCHMARK_CSV_PATH: Path = (
    Path(settings.BASE_DIR) / "docs" / "benchmarks" / "benchmark-results.csv"
)

BENCHMARK_MARKDOWN_DIR: Path = (
    Path(settings.BASE_DIR) / "docs" / "benchmarks"
)

_CSV_HEADERS: list[str] = [
    "timestamp",
    "label",
    "dataset_size",
    "execution_time_ms",
    "memory_before_mb",
    "memory_after_mb",
    "memory_diff_mb",
    "rows",
    "status",
]


class BenchmarkService:
    """
    Stateless utility service for performance measurement.

    Every method is a ``@staticmethod``. No instance attributes,
    no global mutable state.
    """

    # --------------------------------------------------------
    # System Info
    # --------------------------------------------------------

    @staticmethod
    def capture_system_info() -> dict[str, Any]:
        """
        Collect system information for benchmark context.

        Returns:
            dict containing OS, Python version, Django version,
            PostgreSQL version (if available), CPU model, cores,
            RAM, and current timestamp.
        """

        memory = psutil.virtual_memory()

        pg_version = BenchmarkService._get_postgres_version()

        info: dict[str, Any] = {
            "os": platform.platform(),
            "python_version": sys.version,
            "django_version": django.get_version(),
            "postgresql_version": pg_version,
            "cpu_model": platform.processor() or "unknown",
            "physical_cores": psutil.cpu_count(logical=False),
            "logical_cores": psutil.cpu_count(logical=True),
            "total_ram_mb": round(memory.total / (1024 ** 2), 2),
            "available_ram_mb": round(memory.available / (1024 ** 2), 2),
            "timestamp": datetime.now(tz=timezone.utc).isoformat(
                timespec="seconds"
            ),
        }

        logger.info(
            "System info captured. os=%s python=%s django=%s",
            info["os"],
            info["python_version"],
            info["django_version"],
        )

        return info

    # --------------------------------------------------------
    # Timing
    # --------------------------------------------------------

    @staticmethod
    def measure_execution_time(func: Callable) -> float:
        """
        Measure wall-clock execution time of a callable.

        Args:
            func: Zero-argument callable to benchmark.

        Returns:
            Execution time in milliseconds.
        """

        start = time.perf_counter()
        func()
        end = time.perf_counter()

        elapsed_ms = (end - start) * 1000

        logger.debug(
            "Execution time: %.2f ms",
            elapsed_ms,
        )

        return round(elapsed_ms, 2)

    # --------------------------------------------------------
    # Memory
    # --------------------------------------------------------

    @staticmethod
    def measure_memory_usage(func: Callable) -> dict[str, float]:
        """
        Measure memory consumption of a callable using psutil.

        Args:
            func: Zero-argument callable to benchmark.

        Returns:
            dict with ``before_mb``, ``after_mb``, and ``diff_mb``.
        """

        process = psutil.Process(os.getpid())

        before = process.memory_info().rss
        func()
        after = process.memory_info().rss

        result: dict[str, float] = {
            "before_mb": round(before / (1024 ** 2), 2),
            "after_mb": round(after / (1024 ** 2), 2),
            "diff_mb": round((after - before) / (1024 ** 2), 2),
        }

        logger.debug(
            "Memory usage: before=%.2f MB after=%.2f MB diff=%.2f MB",
            result["before_mb"],
            result["after_mb"],
            result["diff_mb"],
        )

        return result

    # --------------------------------------------------------
    # QuerySet
    # --------------------------------------------------------

    @staticmethod
    def measure_queryset_time(queryset: QuerySet) -> dict[str, float]:
        """
        Benchmark individual QuerySet operations.

        Measures ``count()``, ``first()``, ``exists()``,
        ``iterator()``, and ``list()`` separately.

        Args:
            queryset: Django QuerySet to benchmark.

        Returns:
            dict mapping operation names to execution times in ms.
        """

        timings: dict[str, float] = {}

        # count()
        start = time.perf_counter()
        queryset.count()
        timings["count_ms"] = round(
            (time.perf_counter() - start) * 1000, 2
        )

        # first()
        start = time.perf_counter()
        queryset.first()
        timings["first_ms"] = round(
            (time.perf_counter() - start) * 1000, 2
        )

        # exists()
        start = time.perf_counter()
        queryset.exists()
        timings["exists_ms"] = round(
            (time.perf_counter() - start) * 1000, 2
        )

        # iterator()
        start = time.perf_counter()
        for _ in queryset.iterator():
            pass
        timings["iterator_ms"] = round(
            (time.perf_counter() - start) * 1000, 2
        )

        # list()
        start = time.perf_counter()
        list(queryset)
        timings["list_ms"] = round(
            (time.perf_counter() - start) * 1000, 2
        )

        logger.debug(
            "QuerySet timings: %s",
            timings,
        )

        return timings

    # --------------------------------------------------------
    # API Response
    # --------------------------------------------------------

    @staticmethod
    def measure_api_response(
        client: Any,
        url: str,
        method: str = "get",
        payload: Optional[dict] = None,
        headers: Optional[dict] = None,
    ) -> dict[str, Any]:
        """
        Benchmark a DRF APIClient request.

        Args:
            client:  ``rest_framework.test.APIClient`` instance.
            url:     Request URL.
            method:  HTTP method (get, post, put, patch, delete).
            payload: Request body for write methods.
            headers: Extra HTTP headers.

        Returns:
            dict with ``status_code``, ``response_time_ms``,
            and ``response_size_bytes``.
        """

        request_method = getattr(client, method.lower())

        kwargs: dict[str, Any] = {}
        if payload is not None:
            kwargs["data"] = payload
            kwargs["format"] = "json"
        if headers is not None:
            kwargs.update(headers)

        start = time.perf_counter()
        response = request_method(url, **kwargs)
        elapsed_ms = (time.perf_counter() - start) * 1000

        result: dict[str, Any] = {
            "status_code": response.status_code,
            "response_time_ms": round(elapsed_ms, 2),
            "response_size_bytes": len(response.content),
        }

        logger.debug(
            "API response: status=%s time=%.2f ms size=%s bytes",
            result["status_code"],
            result["response_time_ms"],
            result["response_size_bytes"],
        )

        return result

    # --------------------------------------------------------
    # Admin Response
    # --------------------------------------------------------

    @staticmethod
    def measure_admin_response(
        client: Any,
        url: str,
    ) -> dict[str, Any]:
        """
        Benchmark a Django admin page using the test ``Client``.

        Args:
            client: ``django.test.Client`` instance.
            url:    Admin page URL.

        Returns:
            dict with ``status_code``, ``response_time_ms``,
            and ``response_size_bytes``.
        """

        start = time.perf_counter()
        response = client.get(url)
        elapsed_ms = (time.perf_counter() - start) * 1000

        result: dict[str, Any] = {
            "status_code": response.status_code,
            "response_time_ms": round(elapsed_ms, 2),
            "response_size_bytes": len(response.content),
        }

        logger.debug(
            "Admin response: status=%s time=%.2f ms size=%s bytes",
            result["status_code"],
            result["response_time_ms"],
            result["response_size_bytes"],
        )

        return result

    # --------------------------------------------------------
    # High-Level Benchmarks
    # --------------------------------------------------------

    @staticmethod
    def benchmark_queryset(
        queryset: QuerySet,
        label: str = "queryset",
    ) -> dict[str, Any]:
        """
        High-level queryset benchmark combining timing, execution,
        and memory measurements.

        Args:
            queryset: Django QuerySet to benchmark.
            label:    Human-readable label for the benchmark.

        Returns:
            Formatted benchmark result dictionary.
        """

        queryset_timings = BenchmarkService.measure_queryset_time(queryset)

        execution_ms = BenchmarkService.measure_execution_time(
            lambda: list(queryset)
        )

        memory = BenchmarkService.measure_memory_usage(
            lambda: list(queryset)
        )

        row_count = queryset.count()

        return BenchmarkService.format_result(
            label=label,
            execution_time_ms=execution_ms,
            memory=memory,
            rows=row_count,
            extra={"queryset_timings": queryset_timings},
        )

    @staticmethod
    def benchmark_api(
        client: Any,
        url: str,
        method: str = "get",
        payload: Optional[dict] = None,
        headers: Optional[dict] = None,
        label: str = "api",
    ) -> dict[str, Any]:
        """
        High-level API benchmark combining execution, memory,
        and response measurements.

        Args:
            client:  ``rest_framework.test.APIClient`` instance.
            url:     Request URL.
            method:  HTTP method.
            payload: Request body.
            headers: Extra HTTP headers.
            label:   Human-readable label.

        Returns:
            Formatted benchmark result dictionary.
        """

        api_response = BenchmarkService.measure_api_response(
            client=client,
            url=url,
            method=method,
            payload=payload,
            headers=headers,
        )

        execution_ms = BenchmarkService.measure_execution_time(
            lambda: getattr(client, method.lower())(url)
        )

        memory = BenchmarkService.measure_memory_usage(
            lambda: getattr(client, method.lower())(url)
        )

        return BenchmarkService.format_result(
            label=label,
            execution_time_ms=execution_ms,
            memory=memory,
            extra={"api_response": api_response},
        )

    @staticmethod
    def benchmark_function(
        func: Callable,
        label: str = "function",
    ) -> dict[str, Any]:
        """
        Benchmark any zero-argument Python callable.

        Args:
            func:  Callable to benchmark.
            label: Human-readable label.

        Returns:
            Formatted benchmark result dictionary.
        """

        execution_ms = BenchmarkService.measure_execution_time(func)
        memory = BenchmarkService.measure_memory_usage(func)

        return BenchmarkService.format_result(
            label=label,
            execution_time_ms=execution_ms,
            memory=memory,
        )

    @staticmethod
    def benchmark_management_command(
        command_name: str,
        *args: Any,
        label: Optional[str] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Benchmark a Django management command via ``call_command()``.

        Args:
            command_name: Management command name.
            *args:        Positional arguments for the command.
            label:        Human-readable label.
            **kwargs:     Keyword arguments for the command.

        Returns:
            Formatted benchmark result dictionary.
        """

        resolved_label = label or f"command:{command_name}"

        # Capture stdout to suppress command output during benchmark.
        stdout_capture = StringIO()
        kwargs.setdefault("stdout", stdout_capture)

        execution_ms = BenchmarkService.measure_execution_time(
            lambda: call_command(command_name, *args, **kwargs)
        )

        memory = BenchmarkService.measure_memory_usage(
            lambda: call_command(command_name, *args, **kwargs)
        )

        return BenchmarkService.format_result(
            label=resolved_label,
            execution_time_ms=execution_ms,
            memory=memory,
        )

    # --------------------------------------------------------
    # Persistence
    # --------------------------------------------------------

    @staticmethod
    def write_csv(result: dict[str, Any]) -> None:
        """
        Append a benchmark result row to the CSV file.

        Creates the file and writes headers if it does not exist.
        Never overwrites existing data.

        Args:
            result: Formatted benchmark result dictionary.
        """

        csv_path = BENCHMARK_CSV_PATH
        csv_path.parent.mkdir(parents=True, exist_ok=True)

        file_exists = csv_path.exists() and csv_path.stat().st_size > 0

        with csv_path.open("a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=_CSV_HEADERS)

            if not file_exists:
                writer.writeheader()

            row = {
                "timestamp": result.get("timestamp", ""),
                "label": result.get("label", ""),
                "dataset_size": result.get("dataset_size", ""),
                "execution_time_ms": result.get("execution_time_ms", ""),
                "memory_before_mb": result.get("memory_before_mb", ""),
                "memory_after_mb": result.get("memory_after_mb", ""),
                "memory_diff_mb": result.get("memory_diff_mb", ""),
                "rows": result.get("rows", ""),
                "status": result.get("status", ""),
            }

            writer.writerow(row)

        logger.info(
            "Benchmark result appended to %s",
            csv_path,
        )

    @staticmethod
    def append_markdown(
        filename: str,
        result: dict[str, Any],
    ) -> None:
        """
        Append a formatted benchmark section to a markdown file.

        Creates the file if it does not exist. Files are stored in
        ``BENCHMARK_MARKDOWN_DIR``.

        Args:
            filename: Markdown filename (e.g. ``10k-before.md``).
            result:   Formatted benchmark result dictionary.
        """

        md_path = BENCHMARK_MARKDOWN_DIR / filename
        md_path.parent.mkdir(parents=True, exist_ok=True)

        section = BenchmarkService._build_markdown_section(result)

        with md_path.open("a", encoding="utf-8") as f:
            f.write(section)

        logger.info(
            "Benchmark result appended to %s",
            md_path,
        )

    # --------------------------------------------------------
    # Formatting
    # --------------------------------------------------------

    @staticmethod
    def format_result(
        label: str,
        execution_time_ms: float = 0.0,
        memory: Optional[dict[str, float]] = None,
        rows: Optional[int] = None,
        dataset_size: Optional[int] = None,
        extra: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Normalize benchmark output into a consistent schema.

        Args:
            label:             Human-readable benchmark label.
            execution_time_ms: Total execution time in milliseconds.
            memory:            Memory measurement dict.
            rows:              Number of rows processed.
            dataset_size:      Size of the dataset.
            extra:             Additional benchmark-specific data.

        Returns:
            Normalized benchmark result dictionary.
        """

        result: dict[str, Any] = {
            "label": label,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(
                timespec="seconds"
            ),
            "execution_time_ms": round(execution_time_ms, 2),
            "memory_before_mb": 0.0,
            "memory_after_mb": 0.0,
            "memory_diff_mb": 0.0,
            "rows": rows,
            "dataset_size": dataset_size,
            "status": "SUCCESS",
        }

        if memory:
            result["memory_before_mb"] = memory.get("before_mb", 0.0)
            result["memory_after_mb"] = memory.get("after_mb", 0.0)
            result["memory_diff_mb"] = memory.get("diff_mb", 0.0)

        if extra:
            result["extra"] = extra

        return result

    @staticmethod
    def calculate_improvement(
        before: dict[str, Any],
        after: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Calculate performance improvement between two benchmark runs.

        Args:
            before: Benchmark result from the baseline run.
            after:  Benchmark result from the optimized run.

        Returns:
            dict with ``execution_diff_ms``, ``improvement_pct``,
            and ``speedup_multiplier``.
        """

        before_ms = before.get("execution_time_ms", 0.0)
        after_ms = after.get("execution_time_ms", 0.0)

        diff_ms = round(before_ms - after_ms, 2)

        improvement_pct = 0.0
        if before_ms > 0:
            improvement_pct = round((diff_ms / before_ms) * 100, 2)

        speedup = 0.0
        if after_ms > 0:
            speedup = round(before_ms / after_ms, 2)

        result: dict[str, Any] = {
            "before_ms": before_ms,
            "after_ms": after_ms,
            "execution_diff_ms": diff_ms,
            "improvement_pct": improvement_pct,
            "speedup_multiplier": speedup,
        }

        logger.info(
            "Improvement: diff=%.2f ms pct=%.2f%% speedup=%.2fx",
            diff_ms,
            improvement_pct,
            speedup,
        )

        return result

    # --------------------------------------------------------
    # Console Output
    # --------------------------------------------------------

    @staticmethod
    def print_summary(
        result: dict[str, Any],
        stdout: Any = None,
    ) -> None:
        """
        Print a readable benchmark summary to the console.

        Args:
            result: Formatted benchmark result dictionary.
            stdout: Output stream (defaults to ``sys.stdout``).
        """

        output = stdout or sys.stdout
        write = output.write

        label = result.get("label", "benchmark")
        rows = result.get("rows", "N/A")
        execution_ms = result.get("execution_time_ms", 0.0)
        memory_diff = result.get("memory_diff_mb", 0.0)
        status = result.get("status", "UNKNOWN")
        dataset_size = result.get("dataset_size")

        execution_display = f"{execution_ms / 1000:.2f} sec"

        write("\n")
        write("-" * 40 + "\n")
        write(f"  {'Dataset':<20}{dataset_size or rows} Logs\n")
        write(f"  {'Execution':<20}{execution_display}\n")
        write(f"  {'Memory':<20}{memory_diff} MB\n")
        write(f"  {'Rows':<20}{rows}\n")
        write(f"  {'Status':<20}{status}\n")
        write("-" * 40 + "\n")
        write("\n")

    # --------------------------------------------------------
    # Private Helpers
    # --------------------------------------------------------

    @staticmethod
    def _get_postgres_version() -> Optional[str]:
        """
        Retrieve the PostgreSQL server version.

        Returns:
            Version string or ``None`` if unavailable.
        """

        try:
            from django.db import connections

            connection = connections["default"]
            connection.ensure_connection()

            with connection.cursor() as cursor:
                cursor.execute("SELECT version()")
                row = cursor.fetchone()
                return row[0] if row else None

        except Exception as exc:
            logger.debug(
                "Could not retrieve PostgreSQL version. error=%s",
                exc,
            )
            return None

    @staticmethod
    def _build_markdown_section(result: dict[str, Any]) -> str:
        """
        Build a formatted markdown section from a benchmark result.

        Args:
            result: Formatted benchmark result dictionary.

        Returns:
            Markdown-formatted string.
        """

        label = result.get("label", "benchmark")
        timestamp = result.get("timestamp", "")
        execution_ms = result.get("execution_time_ms", 0.0)
        memory_diff = result.get("memory_diff_mb", 0.0)
        rows = result.get("rows", "N/A")
        status = result.get("status", "UNKNOWN")

        execution_display = f"{execution_ms / 1000:.2f} sec"

        lines = [
            f"\n## {label}\n",
            f"- **Timestamp**: {timestamp}\n",
            f"- **Execution**: {execution_display}\n",
            f"- **Memory Δ**: {memory_diff} MB\n",
            f"- **Rows**: {rows}\n",
            f"- **Status**: {status}\n",
            "\n---\n",
        ]

        return "".join(lines)
