from io import StringIO
from unittest.mock import MagicMock, Mock, call, mock_open, patch

import pytest

from monitoring.services.benchmark_service import (
    BENCHMARK_CSV_PATH,
    BENCHMARK_MARKDOWN_DIR,
    BenchmarkService,
    _CSV_HEADERS,
)


# ============================================================
# capture_system_info()
# ============================================================


class TestCaptureSystemInfo:
    """
    Tests for BenchmarkService.capture_system_info().
    """

    @patch("monitoring.services.benchmark_service.psutil")
    @patch("monitoring.services.benchmark_service.BenchmarkService._get_postgres_version")
    def test_returns_dict(self, mock_pg, mock_psutil):
        mock_pg.return_value = "PostgreSQL 15.3"
        mock_memory = MagicMock()
        mock_memory.total = 16 * 1024 ** 2
        mock_memory.available = 8 * 1024 ** 2
        mock_psutil.virtual_memory.return_value = mock_memory
        mock_psutil.cpu_count.return_value = 4

        result = BenchmarkService.capture_system_info()

        assert isinstance(result, dict)

    @patch("monitoring.services.benchmark_service.psutil")
    @patch("monitoring.services.benchmark_service.BenchmarkService._get_postgres_version")
    def test_contains_required_keys(self, mock_pg, mock_psutil):
        mock_pg.return_value = None
        mock_memory = MagicMock()
        mock_memory.total = 16 * 1024 ** 2
        mock_memory.available = 8 * 1024 ** 2
        mock_psutil.virtual_memory.return_value = mock_memory
        mock_psutil.cpu_count.return_value = 4

        result = BenchmarkService.capture_system_info()

        expected_keys = [
            "os",
            "python_version",
            "django_version",
            "postgresql_version",
            "cpu_model",
            "physical_cores",
            "logical_cores",
            "total_ram_mb",
            "available_ram_mb",
            "timestamp",
        ]

        for key in expected_keys:
            assert key in result

    @patch("monitoring.services.benchmark_service.psutil")
    @patch("monitoring.services.benchmark_service.BenchmarkService._get_postgres_version")
    def test_ram_values_are_numeric(self, mock_pg, mock_psutil):
        mock_pg.return_value = None
        mock_memory = MagicMock()
        mock_memory.total = 32 * 1024 ** 2
        mock_memory.available = 16 * 1024 ** 2
        mock_psutil.virtual_memory.return_value = mock_memory
        mock_psutil.cpu_count.return_value = 8

        result = BenchmarkService.capture_system_info()

        assert isinstance(result["total_ram_mb"], float)
        assert isinstance(result["available_ram_mb"], float)

    @patch("monitoring.services.benchmark_service.psutil")
    @patch("monitoring.services.benchmark_service.BenchmarkService._get_postgres_version")
    def test_ram_conversion_is_correct(self, mock_pg, mock_psutil):
        mock_pg.return_value = None
        mock_memory = MagicMock()
        mock_memory.total = 1024 * 1024 * 1024  # 1 GB
        mock_memory.available = 512 * 1024 * 1024  # 512 MB
        mock_psutil.virtual_memory.return_value = mock_memory
        mock_psutil.cpu_count.return_value = 4

        result = BenchmarkService.capture_system_info()

        assert result["total_ram_mb"] == 1024.0
        assert result["available_ram_mb"] == 512.0

    @patch("monitoring.services.benchmark_service.psutil")
    @patch("monitoring.services.benchmark_service.BenchmarkService._get_postgres_version")
    def test_postgres_version_included_when_available(self, mock_pg, mock_psutil):
        mock_pg.return_value = "PostgreSQL 15.3"
        mock_memory = MagicMock()
        mock_memory.total = 16 * 1024 ** 2
        mock_memory.available = 8 * 1024 ** 2
        mock_psutil.virtual_memory.return_value = mock_memory
        mock_psutil.cpu_count.return_value = 4

        result = BenchmarkService.capture_system_info()

        assert result["postgresql_version"] == "PostgreSQL 15.3"

    @patch("monitoring.services.benchmark_service.psutil")
    @patch("monitoring.services.benchmark_service.BenchmarkService._get_postgres_version")
    def test_postgres_version_none_when_unavailable(self, mock_pg, mock_psutil):
        mock_pg.return_value = None
        mock_memory = MagicMock()
        mock_memory.total = 16 * 1024 ** 2
        mock_memory.available = 8 * 1024 ** 2
        mock_psutil.virtual_memory.return_value = mock_memory
        mock_psutil.cpu_count.return_value = 4

        result = BenchmarkService.capture_system_info()

        assert result["postgresql_version"] is None

    @patch("monitoring.services.benchmark_service.psutil")
    @patch("monitoring.services.benchmark_service.BenchmarkService._get_postgres_version")
    def test_timestamp_is_iso_format(self, mock_pg, mock_psutil):
        mock_pg.return_value = None
        mock_memory = MagicMock()
        mock_memory.total = 16 * 1024 ** 2
        mock_memory.available = 8 * 1024 ** 2
        mock_psutil.virtual_memory.return_value = mock_memory
        mock_psutil.cpu_count.return_value = 4

        result = BenchmarkService.capture_system_info()

        assert "T" in result["timestamp"]


# ============================================================
# measure_execution_time()
# ============================================================


class TestMeasureExecutionTime:
    """
    Tests for BenchmarkService.measure_execution_time().
    """

    @patch("monitoring.services.benchmark_service.time.perf_counter")
    def test_returns_float(self, mock_perf):
        mock_perf.side_effect = [0.0, 0.1]

        result = BenchmarkService.measure_execution_time(lambda: None)

        assert isinstance(result, float)

    @patch("monitoring.services.benchmark_service.time.perf_counter")
    def test_calculates_milliseconds(self, mock_perf):
        mock_perf.side_effect = [1.0, 1.5]

        result = BenchmarkService.measure_execution_time(lambda: None)

        assert result == 500.0

    @patch("monitoring.services.benchmark_service.time.perf_counter")
    def test_callable_is_invoked(self, mock_perf):
        mock_perf.side_effect = [0.0, 0.01]
        func = MagicMock()

        BenchmarkService.measure_execution_time(func)

        func.assert_called_once()

    @patch("monitoring.services.benchmark_service.time.perf_counter")
    def test_returns_zero_for_instant_execution(self, mock_perf):
        mock_perf.side_effect = [5.0, 5.0]

        result = BenchmarkService.measure_execution_time(lambda: None)

        assert result == 0.0

    @patch("monitoring.services.benchmark_service.time.perf_counter")
    def test_result_is_rounded(self, mock_perf):
        mock_perf.side_effect = [0.0, 0.12345678]

        result = BenchmarkService.measure_execution_time(lambda: None)

        assert result == 123.46


# ============================================================
# measure_memory_usage()
# ============================================================


class TestMeasureMemoryUsage:
    """
    Tests for BenchmarkService.measure_memory_usage().
    """

    @patch("monitoring.services.benchmark_service.psutil.Process")
    def test_returns_dict(self, mock_process_cls):
        process = MagicMock()
        before_info = MagicMock()
        before_info.rss = 100 * 1024 * 1024
        after_info = MagicMock()
        after_info.rss = 110 * 1024 * 1024
        process.memory_info.side_effect = [before_info, after_info]
        mock_process_cls.return_value = process

        result = BenchmarkService.measure_memory_usage(lambda: None)

        assert isinstance(result, dict)

    @patch("monitoring.services.benchmark_service.psutil.Process")
    def test_contains_required_keys(self, mock_process_cls):
        process = MagicMock()
        mem_info = MagicMock()
        mem_info.rss = 100 * 1024 * 1024
        process.memory_info.return_value = mem_info
        mock_process_cls.return_value = process

        result = BenchmarkService.measure_memory_usage(lambda: None)

        assert "before_mb" in result
        assert "after_mb" in result
        assert "diff_mb" in result

    @patch("monitoring.services.benchmark_service.psutil.Process")
    def test_calculates_diff_correctly(self, mock_process_cls):
        process = MagicMock()
        before_info = MagicMock()
        before_info.rss = 100 * 1024 * 1024  # 100 MB
        after_info = MagicMock()
        after_info.rss = 150 * 1024 * 1024  # 150 MB
        process.memory_info.side_effect = [before_info, after_info]
        mock_process_cls.return_value = process

        result = BenchmarkService.measure_memory_usage(lambda: None)

        assert result["before_mb"] == 100.0
        assert result["after_mb"] == 150.0
        assert result["diff_mb"] == 50.0

    @patch("monitoring.services.benchmark_service.psutil.Process")
    def test_callable_is_invoked(self, mock_process_cls):
        process = MagicMock()
        mem_info = MagicMock()
        mem_info.rss = 100 * 1024 * 1024
        process.memory_info.return_value = mem_info
        mock_process_cls.return_value = process
        func = MagicMock()

        BenchmarkService.measure_memory_usage(func)

        func.assert_called_once()

    @patch("monitoring.services.benchmark_service.psutil.Process")
    def test_negative_diff_when_memory_freed(self, mock_process_cls):
        process = MagicMock()
        before_info = MagicMock()
        before_info.rss = 200 * 1024 * 1024
        after_info = MagicMock()
        after_info.rss = 180 * 1024 * 1024
        process.memory_info.side_effect = [before_info, after_info]
        mock_process_cls.return_value = process

        result = BenchmarkService.measure_memory_usage(lambda: None)

        assert result["diff_mb"] == -20.0


# ============================================================
# measure_queryset_time()
# ============================================================


class TestMeasureQuerysetTime:
    """
    Tests for BenchmarkService.measure_queryset_time().
    """

    @staticmethod
    def _make_queryset_mock():
        """Build a MagicMock that behaves like a QuerySet."""
        qs = MagicMock()
        qs.count.return_value = 0
        qs.first.return_value = None
        qs.exists.return_value = False
        qs.iterator.return_value = iter([])
        qs.__iter__ = Mock(return_value=iter([]))
        return qs

    def test_returns_dict(self):
        qs = self._make_queryset_mock()

        result = BenchmarkService.measure_queryset_time(qs)

        assert isinstance(result, dict)

    def test_contains_all_operation_keys(self):
        qs = self._make_queryset_mock()

        result = BenchmarkService.measure_queryset_time(qs)

        assert "count_ms" in result
        assert "first_ms" in result
        assert "exists_ms" in result
        assert "iterator_ms" in result
        assert "list_ms" in result

    def test_all_values_are_floats(self):
        qs = self._make_queryset_mock()

        result = BenchmarkService.measure_queryset_time(qs)

        for value in result.values():
            assert isinstance(value, float)

    def test_calls_queryset_operations(self):
        qs = MagicMock()
        qs.count.return_value = 10
        qs.first.return_value = MagicMock()
        qs.exists.return_value = True
        qs.iterator.return_value = iter([])
        qs.__iter__ = Mock(return_value=iter([]))

        BenchmarkService.measure_queryset_time(qs)

        qs.count.assert_called_once()
        qs.first.assert_called_once()
        qs.exists.assert_called_once()
        qs.iterator.assert_called_once()


# ============================================================
# measure_api_response()
# ============================================================


class TestMeasureApiResponse:
    """
    Tests for BenchmarkService.measure_api_response().
    """

    def test_returns_dict(self):
        client = MagicMock()
        response = MagicMock()
        response.status_code = 200
        response.content = b"OK"
        client.get.return_value = response

        result = BenchmarkService.measure_api_response(client, "/api/test/")

        assert isinstance(result, dict)

    def test_contains_required_keys(self):
        client = MagicMock()
        response = MagicMock()
        response.status_code = 200
        response.content = b"test response"
        client.get.return_value = response

        result = BenchmarkService.measure_api_response(client, "/api/test/")

        assert "status_code" in result
        assert "response_time_ms" in result
        assert "response_size_bytes" in result

    def test_captures_status_code(self):
        client = MagicMock()
        response = MagicMock()
        response.status_code = 201
        response.content = b"{}"
        client.post.return_value = response

        result = BenchmarkService.measure_api_response(
            client, "/api/test/", method="post"
        )

        assert result["status_code"] == 201

    def test_captures_response_size(self):
        client = MagicMock()
        response = MagicMock()
        response.status_code = 200
        response.content = b"x" * 512
        client.get.return_value = response

        result = BenchmarkService.measure_api_response(client, "/api/test/")

        assert result["response_size_bytes"] == 512

    def test_passes_payload_for_post(self):
        client = MagicMock()
        response = MagicMock()
        response.status_code = 201
        response.content = b"{}"
        client.post.return_value = response
        payload = {"name": "test"}

        BenchmarkService.measure_api_response(
            client, "/api/test/", method="post", payload=payload
        )

        client.post.assert_called_once()
        _, kwargs = client.post.call_args
        assert kwargs["data"] == payload
        assert kwargs["format"] == "json"

    def test_uses_correct_http_method(self):
        client = MagicMock()
        response = MagicMock()
        response.status_code = 204
        response.content = b""
        client.delete.return_value = response

        BenchmarkService.measure_api_response(
            client, "/api/test/1/", method="delete"
        )

        client.delete.assert_called_once()

    def test_response_time_is_float(self):
        client = MagicMock()
        response = MagicMock()
        response.status_code = 200
        response.content = b"OK"
        client.get.return_value = response

        result = BenchmarkService.measure_api_response(client, "/api/test/")

        assert isinstance(result["response_time_ms"], float)


# ============================================================
# measure_admin_response()
# ============================================================


class TestMeasureAdminResponse:
    """
    Tests for BenchmarkService.measure_admin_response().
    """

    def test_returns_dict(self):
        client = MagicMock()
        response = MagicMock()
        response.status_code = 200
        response.content = b"<html></html>"
        client.get.return_value = response

        result = BenchmarkService.measure_admin_response(
            client, "/admin/monitoring/log/"
        )

        assert isinstance(result, dict)

    def test_contains_required_keys(self):
        client = MagicMock()
        response = MagicMock()
        response.status_code = 200
        response.content = b"<html></html>"
        client.get.return_value = response

        result = BenchmarkService.measure_admin_response(
            client, "/admin/monitoring/log/"
        )

        assert "status_code" in result
        assert "response_time_ms" in result
        assert "response_size_bytes" in result

    def test_calls_client_get(self):
        client = MagicMock()
        response = MagicMock()
        response.status_code = 200
        response.content = b""
        client.get.return_value = response

        BenchmarkService.measure_admin_response(
            client, "/admin/monitoring/log/"
        )

        client.get.assert_called_once_with("/admin/monitoring/log/")

    def test_captures_status_code(self):
        client = MagicMock()
        response = MagicMock()
        response.status_code = 302
        response.content = b""
        client.get.return_value = response

        result = BenchmarkService.measure_admin_response(
            client, "/admin/monitoring/log/"
        )

        assert result["status_code"] == 302


# ============================================================
# benchmark_queryset()
# ============================================================


class TestBenchmarkQueryset:
    """
    Tests for BenchmarkService.benchmark_queryset().
    """

    @patch.object(BenchmarkService, "format_result")
    @patch.object(BenchmarkService, "measure_memory_usage")
    @patch.object(BenchmarkService, "measure_execution_time")
    @patch.object(BenchmarkService, "measure_queryset_time")
    def test_calls_all_measurement_methods(
        self, mock_qs_time, mock_exec, mock_mem, mock_format
    ):
        qs = MagicMock()
        qs.count.return_value = 5
        mock_qs_time.return_value = {"count_ms": 1.0}
        mock_exec.return_value = 10.0
        mock_mem.return_value = {"before_mb": 100.0, "after_mb": 110.0, "diff_mb": 10.0}
        mock_format.return_value = {"label": "test"}

        BenchmarkService.benchmark_queryset(qs, label="test")

        mock_qs_time.assert_called_once_with(qs)
        mock_exec.assert_called_once()
        mock_mem.assert_called_once()

    @patch.object(BenchmarkService, "format_result")
    @patch.object(BenchmarkService, "measure_memory_usage")
    @patch.object(BenchmarkService, "measure_execution_time")
    @patch.object(BenchmarkService, "measure_queryset_time")
    def test_passes_label_to_format_result(
        self, mock_qs_time, mock_exec, mock_mem, mock_format
    ):
        qs = MagicMock()
        qs.count.return_value = 0
        mock_qs_time.return_value = {}
        mock_exec.return_value = 5.0
        mock_mem.return_value = {"before_mb": 0, "after_mb": 0, "diff_mb": 0}
        mock_format.return_value = {}

        BenchmarkService.benchmark_queryset(qs, label="my_label")

        _, kwargs = mock_format.call_args
        assert kwargs["label"] == "my_label"

    @patch.object(BenchmarkService, "format_result")
    @patch.object(BenchmarkService, "measure_memory_usage")
    @patch.object(BenchmarkService, "measure_execution_time")
    @patch.object(BenchmarkService, "measure_queryset_time")
    def test_returns_format_result_output(
        self, mock_qs_time, mock_exec, mock_mem, mock_format
    ):
        qs = MagicMock()
        qs.count.return_value = 0
        mock_qs_time.return_value = {}
        mock_exec.return_value = 0
        mock_mem.return_value = {"before_mb": 0, "after_mb": 0, "diff_mb": 0}
        expected = {"label": "test", "status": "SUCCESS"}
        mock_format.return_value = expected

        result = BenchmarkService.benchmark_queryset(qs)

        assert result == expected


# ============================================================
# benchmark_api()
# ============================================================


class TestBenchmarkApi:
    """
    Tests for BenchmarkService.benchmark_api().
    """

    @patch.object(BenchmarkService, "format_result")
    @patch.object(BenchmarkService, "measure_memory_usage")
    @patch.object(BenchmarkService, "measure_execution_time")
    @patch.object(BenchmarkService, "measure_api_response")
    def test_calls_all_measurement_methods(
        self, mock_api, mock_exec, mock_mem, mock_format
    ):
        client = MagicMock()
        client.get.return_value = MagicMock(status_code=200, content=b"")
        mock_api.return_value = {"status_code": 200}
        mock_exec.return_value = 15.0
        mock_mem.return_value = {"before_mb": 0, "after_mb": 0, "diff_mb": 0}
        mock_format.return_value = {}

        BenchmarkService.benchmark_api(client, "/api/test/")

        mock_api.assert_called_once()
        mock_exec.assert_called_once()
        mock_mem.assert_called_once()

    @patch.object(BenchmarkService, "format_result")
    @patch.object(BenchmarkService, "measure_memory_usage")
    @patch.object(BenchmarkService, "measure_execution_time")
    @patch.object(BenchmarkService, "measure_api_response")
    def test_passes_label(
        self, mock_api, mock_exec, mock_mem, mock_format
    ):
        client = MagicMock()
        client.get.return_value = MagicMock(status_code=200, content=b"")
        mock_api.return_value = {"status_code": 200}
        mock_exec.return_value = 0
        mock_mem.return_value = {"before_mb": 0, "after_mb": 0, "diff_mb": 0}
        mock_format.return_value = {}

        BenchmarkService.benchmark_api(
            client, "/api/test/", label="api_bench"
        )

        _, kwargs = mock_format.call_args
        assert kwargs["label"] == "api_bench"

    @patch.object(BenchmarkService, "format_result")
    @patch.object(BenchmarkService, "measure_memory_usage")
    @patch.object(BenchmarkService, "measure_execution_time")
    @patch.object(BenchmarkService, "measure_api_response")
    def test_includes_api_response_in_extra(
        self, mock_api, mock_exec, mock_mem, mock_format
    ):
        client = MagicMock()
        client.get.return_value = MagicMock(status_code=200, content=b"")
        api_data = {"status_code": 200, "response_time_ms": 5.0}
        mock_api.return_value = api_data
        mock_exec.return_value = 0
        mock_mem.return_value = {"before_mb": 0, "after_mb": 0, "diff_mb": 0}
        mock_format.return_value = {}

        BenchmarkService.benchmark_api(client, "/api/test/")

        _, kwargs = mock_format.call_args
        assert kwargs["extra"]["api_response"] == api_data


# ============================================================
# benchmark_function()
# ============================================================


class TestBenchmarkFunction:
    """
    Tests for BenchmarkService.benchmark_function().
    """

    @patch.object(BenchmarkService, "format_result")
    @patch.object(BenchmarkService, "measure_memory_usage")
    @patch.object(BenchmarkService, "measure_execution_time")
    def test_calls_execution_and_memory(self, mock_exec, mock_mem, mock_format):
        mock_exec.return_value = 42.0
        mock_mem.return_value = {"before_mb": 0, "after_mb": 0, "diff_mb": 0}
        mock_format.return_value = {}

        BenchmarkService.benchmark_function(lambda: None)

        mock_exec.assert_called_once()
        mock_mem.assert_called_once()

    @patch.object(BenchmarkService, "format_result")
    @patch.object(BenchmarkService, "measure_memory_usage")
    @patch.object(BenchmarkService, "measure_execution_time")
    def test_passes_label(self, mock_exec, mock_mem, mock_format):
        mock_exec.return_value = 0
        mock_mem.return_value = {"before_mb": 0, "after_mb": 0, "diff_mb": 0}
        mock_format.return_value = {}

        BenchmarkService.benchmark_function(lambda: None, label="my_func")

        _, kwargs = mock_format.call_args
        assert kwargs["label"] == "my_func"

    @patch.object(BenchmarkService, "format_result")
    @patch.object(BenchmarkService, "measure_memory_usage")
    @patch.object(BenchmarkService, "measure_execution_time")
    def test_default_label(self, mock_exec, mock_mem, mock_format):
        mock_exec.return_value = 0
        mock_mem.return_value = {"before_mb": 0, "after_mb": 0, "diff_mb": 0}
        mock_format.return_value = {}

        BenchmarkService.benchmark_function(lambda: None)

        _, kwargs = mock_format.call_args
        assert kwargs["label"] == "function"


# ============================================================
# benchmark_management_command()
# ============================================================


class TestBenchmarkManagementCommand:
    """
    Tests for BenchmarkService.benchmark_management_command().
    """

    @patch.object(BenchmarkService, "format_result")
    @patch.object(BenchmarkService, "measure_memory_usage")
    @patch.object(BenchmarkService, "measure_execution_time")
    def test_calls_execution_and_memory(self, mock_exec, mock_mem, mock_format):
        mock_exec.return_value = 100.0
        mock_mem.return_value = {"before_mb": 0, "after_mb": 0, "diff_mb": 0}
        mock_format.return_value = {}

        BenchmarkService.benchmark_management_command("check")

        mock_exec.assert_called_once()
        mock_mem.assert_called_once()

    @patch.object(BenchmarkService, "format_result")
    @patch.object(BenchmarkService, "measure_memory_usage")
    @patch.object(BenchmarkService, "measure_execution_time")
    def test_default_label_includes_command_name(self, mock_exec, mock_mem, mock_format):
        mock_exec.return_value = 0
        mock_mem.return_value = {"before_mb": 0, "after_mb": 0, "diff_mb": 0}
        mock_format.return_value = {}

        BenchmarkService.benchmark_management_command("check")

        _, kwargs = mock_format.call_args
        assert kwargs["label"] == "command:check"

    @patch.object(BenchmarkService, "format_result")
    @patch.object(BenchmarkService, "measure_memory_usage")
    @patch.object(BenchmarkService, "measure_execution_time")
    def test_custom_label_overrides_default(self, mock_exec, mock_mem, mock_format):
        mock_exec.return_value = 0
        mock_mem.return_value = {"before_mb": 0, "after_mb": 0, "diff_mb": 0}
        mock_format.return_value = {}

        BenchmarkService.benchmark_management_command(
            "check", label="custom_label"
        )

        _, kwargs = mock_format.call_args
        assert kwargs["label"] == "custom_label"


# ============================================================
# write_csv()
# ============================================================


class TestWriteCsv:
    """
    Tests for BenchmarkService.write_csv().
    """

    def test_creates_file_when_missing(self, tmp_path):
        csv_path = tmp_path / "benchmark-results.csv"

        with patch(
            "monitoring.services.benchmark_service.BENCHMARK_CSV_PATH",
            csv_path,
        ):
            BenchmarkService.write_csv({"label": "test", "status": "SUCCESS"})

        assert csv_path.exists()

    def test_writes_headers_on_first_write(self, tmp_path):
        csv_path = tmp_path / "benchmark-results.csv"

        with patch(
            "monitoring.services.benchmark_service.BENCHMARK_CSV_PATH",
            csv_path,
        ):
            BenchmarkService.write_csv({"label": "test"})

        content = csv_path.read_text()
        header_line = content.splitlines()[0]

        for header in _CSV_HEADERS:
            assert header in header_line

    def test_appends_data_row(self, tmp_path):
        csv_path = tmp_path / "benchmark-results.csv"

        with patch(
            "monitoring.services.benchmark_service.BENCHMARK_CSV_PATH",
            csv_path,
        ):
            BenchmarkService.write_csv({"label": "test1"})
            BenchmarkService.write_csv({"label": "test2"})

        lines = csv_path.read_text().strip().splitlines()

        # header + 2 data rows
        assert len(lines) == 3

    def test_never_overwrites_existing_data(self, tmp_path):
        csv_path = tmp_path / "benchmark-results.csv"

        with patch(
            "monitoring.services.benchmark_service.BENCHMARK_CSV_PATH",
            csv_path,
        ):
            BenchmarkService.write_csv({"label": "first"})
            BenchmarkService.write_csv({"label": "second"})

        content = csv_path.read_text()

        assert "first" in content
        assert "second" in content

    def test_does_not_duplicate_headers(self, tmp_path):
        csv_path = tmp_path / "benchmark-results.csv"

        with patch(
            "monitoring.services.benchmark_service.BENCHMARK_CSV_PATH",
            csv_path,
        ):
            BenchmarkService.write_csv({"label": "first"})
            BenchmarkService.write_csv({"label": "second"})

        content = csv_path.read_text()
        header_count = content.count("timestamp,label")

        assert header_count == 1

    def test_creates_parent_directories(self, tmp_path):
        csv_path = tmp_path / "nested" / "dir" / "benchmark-results.csv"

        with patch(
            "monitoring.services.benchmark_service.BENCHMARK_CSV_PATH",
            csv_path,
        ):
            BenchmarkService.write_csv({"label": "test"})

        assert csv_path.exists()


# ============================================================
# append_markdown()
# ============================================================


class TestAppendMarkdown:
    """
    Tests for BenchmarkService.append_markdown().
    """

    def test_creates_file_when_missing(self, tmp_path):
        with patch(
            "monitoring.services.benchmark_service.BENCHMARK_MARKDOWN_DIR",
            tmp_path,
        ):
            BenchmarkService.append_markdown(
                "10k-before.md",
                {"label": "test", "status": "SUCCESS"},
            )

        md_path = tmp_path / "10k-before.md"

        assert md_path.exists()

    def test_appends_content(self, tmp_path):
        with patch(
            "monitoring.services.benchmark_service.BENCHMARK_MARKDOWN_DIR",
            tmp_path,
        ):
            BenchmarkService.append_markdown(
                "10k-before.md",
                {"label": "first"},
            )
            BenchmarkService.append_markdown(
                "10k-before.md",
                {"label": "second"},
            )

        content = (tmp_path / "10k-before.md").read_text()

        assert "first" in content
        assert "second" in content

    def test_contains_label_as_heading(self, tmp_path):
        with patch(
            "monitoring.services.benchmark_service.BENCHMARK_MARKDOWN_DIR",
            tmp_path,
        ):
            BenchmarkService.append_markdown(
                "test.md",
                {"label": "queryset_benchmark"},
            )

        content = (tmp_path / "test.md").read_text()

        assert "## queryset_benchmark" in content

    def test_contains_execution_info(self, tmp_path):
        with patch(
            "monitoring.services.benchmark_service.BENCHMARK_MARKDOWN_DIR",
            tmp_path,
        ):
            BenchmarkService.append_markdown(
                "test.md",
                {"label": "test", "execution_time_ms": 4180.0},
            )

        content = (tmp_path / "test.md").read_text()

        assert "Execution" in content

    def test_contains_memory_info(self, tmp_path):
        with patch(
            "monitoring.services.benchmark_service.BENCHMARK_MARKDOWN_DIR",
            tmp_path,
        ):
            BenchmarkService.append_markdown(
                "test.md",
                {"label": "test", "memory_diff_mb": 81.0},
            )

        content = (tmp_path / "test.md").read_text()

        assert "81.0 MB" in content

    def test_contains_status(self, tmp_path):
        with patch(
            "monitoring.services.benchmark_service.BENCHMARK_MARKDOWN_DIR",
            tmp_path,
        ):
            BenchmarkService.append_markdown(
                "test.md",
                {"label": "test", "status": "SUCCESS"},
            )

        content = (tmp_path / "test.md").read_text()

        assert "SUCCESS" in content


# ============================================================
# format_result()
# ============================================================


class TestFormatResult:
    """
    Tests for BenchmarkService.format_result().
    """

    def test_returns_dict(self):
        result = BenchmarkService.format_result(label="test")

        assert isinstance(result, dict)

    def test_contains_required_keys(self):
        result = BenchmarkService.format_result(label="test")

        required = [
            "label",
            "timestamp",
            "execution_time_ms",
            "memory_before_mb",
            "memory_after_mb",
            "memory_diff_mb",
            "rows",
            "status",
        ]

        for key in required:
            assert key in result

    def test_label_is_set(self):
        result = BenchmarkService.format_result(label="my_benchmark")

        assert result["label"] == "my_benchmark"

    def test_default_status_is_success(self):
        result = BenchmarkService.format_result(label="test")

        assert result["status"] == "SUCCESS"

    def test_execution_time_is_set(self):
        result = BenchmarkService.format_result(
            label="test", execution_time_ms=123.45
        )

        assert result["execution_time_ms"] == 123.45

    def test_memory_values_from_dict(self):
        memory = {"before_mb": 100.0, "after_mb": 150.0, "diff_mb": 50.0}

        result = BenchmarkService.format_result(
            label="test", memory=memory
        )

        assert result["memory_before_mb"] == 100.0
        assert result["memory_after_mb"] == 150.0
        assert result["memory_diff_mb"] == 50.0

    def test_rows_is_set(self):
        result = BenchmarkService.format_result(label="test", rows=5000)

        assert result["rows"] == 5000

    def test_dataset_size_is_set(self):
        result = BenchmarkService.format_result(
            label="test", dataset_size=100000
        )

        assert result["dataset_size"] == 100000

    def test_extra_data_included(self):
        extra = {"queryset_timings": {"count_ms": 5.0}}

        result = BenchmarkService.format_result(
            label="test", extra=extra
        )

        assert result["extra"] == extra

    def test_no_extra_key_when_none(self):
        result = BenchmarkService.format_result(label="test")

        assert "extra" not in result

    def test_default_memory_values_are_zero(self):
        result = BenchmarkService.format_result(label="test")

        assert result["memory_before_mb"] == 0.0
        assert result["memory_after_mb"] == 0.0
        assert result["memory_diff_mb"] == 0.0


# ============================================================
# calculate_improvement()
# ============================================================


class TestCalculateImprovement:
    """
    Tests for BenchmarkService.calculate_improvement().
    """

    def test_returns_dict(self):
        before = {"execution_time_ms": 1000.0}
        after = {"execution_time_ms": 500.0}

        result = BenchmarkService.calculate_improvement(before, after)

        assert isinstance(result, dict)

    def test_contains_required_keys(self):
        before = {"execution_time_ms": 1000.0}
        after = {"execution_time_ms": 500.0}

        result = BenchmarkService.calculate_improvement(before, after)

        assert "before_ms" in result
        assert "after_ms" in result
        assert "execution_diff_ms" in result
        assert "improvement_pct" in result
        assert "speedup_multiplier" in result

    def test_calculates_diff(self):
        before = {"execution_time_ms": 1000.0}
        after = {"execution_time_ms": 600.0}

        result = BenchmarkService.calculate_improvement(before, after)

        assert result["execution_diff_ms"] == 400.0

    def test_calculates_percentage(self):
        before = {"execution_time_ms": 1000.0}
        after = {"execution_time_ms": 500.0}

        result = BenchmarkService.calculate_improvement(before, after)

        assert result["improvement_pct"] == 50.0

    def test_calculates_speedup_multiplier(self):
        before = {"execution_time_ms": 1000.0}
        after = {"execution_time_ms": 500.0}

        result = BenchmarkService.calculate_improvement(before, after)

        assert result["speedup_multiplier"] == 2.0

    def test_handles_zero_before_time(self):
        before = {"execution_time_ms": 0.0}
        after = {"execution_time_ms": 500.0}

        result = BenchmarkService.calculate_improvement(before, after)

        assert result["improvement_pct"] == 0.0

    def test_handles_zero_after_time(self):
        before = {"execution_time_ms": 1000.0}
        after = {"execution_time_ms": 0.0}

        result = BenchmarkService.calculate_improvement(before, after)

        assert result["speedup_multiplier"] == 0.0

    def test_negative_improvement_when_slower(self):
        before = {"execution_time_ms": 500.0}
        after = {"execution_time_ms": 1000.0}

        result = BenchmarkService.calculate_improvement(before, after)

        assert result["execution_diff_ms"] == -500.0
        assert result["improvement_pct"] == -100.0

    def test_handles_missing_keys(self):
        result = BenchmarkService.calculate_improvement({}, {})

        assert result["before_ms"] == 0.0
        assert result["after_ms"] == 0.0
        assert result["execution_diff_ms"] == 0.0


# ============================================================
# print_summary()
# ============================================================


class TestPrintSummary:
    """
    Tests for BenchmarkService.print_summary().
    """

    def test_writes_to_stdout(self):
        output = StringIO()
        result = {
            "label": "test",
            "rows": 100,
            "execution_time_ms": 1500.0,
            "memory_diff_mb": 25.0,
            "status": "SUCCESS",
        }

        BenchmarkService.print_summary(result, stdout=output)

        content = output.getvalue()

        assert len(content) > 0

    def test_contains_dataset_info(self):
        output = StringIO()
        result = {
            "label": "test",
            "dataset_size": 100000,
            "rows": 100000,
            "execution_time_ms": 4180.0,
            "memory_diff_mb": 81.0,
            "status": "SUCCESS",
        }

        BenchmarkService.print_summary(result, stdout=output)

        content = output.getvalue()

        assert "100000" in content

    def test_contains_execution_time(self):
        output = StringIO()
        result = {
            "label": "test",
            "rows": 100,
            "execution_time_ms": 4180.0,
            "memory_diff_mb": 0,
            "status": "SUCCESS",
        }

        BenchmarkService.print_summary(result, stdout=output)

        content = output.getvalue()

        assert "4.18 sec" in content

    def test_contains_memory_info(self):
        output = StringIO()
        result = {
            "label": "test",
            "rows": 100,
            "execution_time_ms": 0,
            "memory_diff_mb": 81.0,
            "status": "SUCCESS",
        }

        BenchmarkService.print_summary(result, stdout=output)

        content = output.getvalue()

        assert "81.0" in content

    def test_contains_status(self):
        output = StringIO()
        result = {
            "label": "test",
            "rows": 100,
            "execution_time_ms": 0,
            "memory_diff_mb": 0,
            "status": "SUCCESS",
        }

        BenchmarkService.print_summary(result, stdout=output)

        content = output.getvalue()

        assert "SUCCESS" in content

    def test_contains_row_count(self):
        output = StringIO()
        result = {
            "label": "test",
            "rows": 50000,
            "execution_time_ms": 0,
            "memory_diff_mb": 0,
            "status": "SUCCESS",
        }

        BenchmarkService.print_summary(result, stdout=output)

        content = output.getvalue()

        assert "50000" in content

    def test_contains_separator_lines(self):
        output = StringIO()
        result = {
            "label": "test",
            "rows": 100,
            "execution_time_ms": 0,
            "memory_diff_mb": 0,
            "status": "SUCCESS",
        }

        BenchmarkService.print_summary(result, stdout=output)

        content = output.getvalue()

        assert "-" * 40 in content
