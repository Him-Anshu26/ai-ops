from io import StringIO
from unittest.mock import MagicMock, Mock, patch, call

import pytest

from django.core.management import call_command
from django.core.management.base import CommandError

from monitoring.models import Log, LogStatus


# ============================================================
# Valid Arguments
# ============================================================


@pytest.mark.django_db
class TestGenerateLogsValidArguments:
    """
    Tests for valid argument parsing and execution.
    """

    @patch("monitoring.management.commands.generate_logs.BenchmarkService")
    def test_generates_with_required_count(self, mock_bench, service):
        mock_bench.measure_execution_time.side_effect = lambda fn: (fn(), 100.0)[1]
        mock_bench.measure_memory_usage.return_value = {
            "before_mb": 0, "after_mb": 0, "diff_mb": 0,
        }
        mock_bench.format_result.return_value = {
            "label": "generate_logs", "status": "SUCCESS",
        }

        call_command("generate_logs", "--count=10", stdout=StringIO())

        assert Log.objects.count() == 10

    @patch("monitoring.management.commands.generate_logs.BenchmarkService")
    def test_custom_batch_size(self, mock_bench, service):
        mock_bench.measure_execution_time.side_effect = lambda fn: (fn(), 50.0)[1]
        mock_bench.measure_memory_usage.return_value = {
            "before_mb": 0, "after_mb": 0, "diff_mb": 0,
        }
        mock_bench.format_result.return_value = {"label": "test", "status": "SUCCESS"}

        call_command(
            "generate_logs", "--count=25", "--batch-size=5", stdout=StringIO()
        )

        assert Log.objects.count() == 25

    @patch("monitoring.management.commands.generate_logs.BenchmarkService")
    def test_service_by_name(self, mock_bench, service):
        mock_bench.measure_execution_time.side_effect = lambda fn: (fn(), 10.0)[1]
        mock_bench.measure_memory_usage.return_value = {
            "before_mb": 0, "after_mb": 0, "diff_mb": 0,
        }
        mock_bench.format_result.return_value = {"label": "test", "status": "SUCCESS"}

        call_command(
            "generate_logs", "--count=5",
            f"--service={service.name}", stdout=StringIO(),
        )

        assert Log.objects.filter(service=service).count() == 5

    @patch("monitoring.management.commands.generate_logs.BenchmarkService")
    def test_service_by_id(self, mock_bench, service):
        mock_bench.measure_execution_time.side_effect = lambda fn: (fn(), 10.0)[1]
        mock_bench.measure_memory_usage.return_value = {
            "before_mb": 0, "after_mb": 0, "diff_mb": 0,
        }
        mock_bench.format_result.return_value = {"label": "test", "status": "SUCCESS"}

        call_command(
            "generate_logs", "--count=5",
            f"--service={service.pk}", stdout=StringIO(),
        )

        assert Log.objects.filter(service=service).count() == 5


# ============================================================
# Invalid Arguments
# ============================================================


@pytest.mark.django_db
class TestGenerateLogsInvalidArguments:
    """
    Tests for invalid argument handling.
    """

    def test_negative_count_raises_error(self, service):
        with pytest.raises(CommandError, match="--count must be a positive integer"):
            call_command(
                "generate_logs", "--count=-5", stdout=StringIO()
            )

    def test_zero_count_raises_error(self, service):
        with pytest.raises(CommandError, match="--count must be a positive integer"):
            call_command(
                "generate_logs", "--count=0", stdout=StringIO()
            )

    def test_negative_batch_size_raises_error(self, service):
        with pytest.raises(CommandError, match="--batch-size must be a positive integer"):
            call_command(
                "generate_logs", "--count=10", "--batch-size=-1",
                stdout=StringIO(),
            )

    def test_zero_batch_size_raises_error(self, service):
        with pytest.raises(CommandError, match="--batch-size must be a positive integer"):
            call_command(
                "generate_logs", "--count=10", "--batch-size=0",
                stdout=StringIO(),
            )


# ============================================================
# Service Lookup
# ============================================================


@pytest.mark.django_db
class TestGenerateLogsServiceLookup:
    """
    Tests for service resolution.
    """

    def test_nonexistent_service_name_raises_error(self, service):
        with pytest.raises(CommandError, match="does not exist"):
            call_command(
                "generate_logs", "--count=5",
                "--service=nonexistent_service_xyz",
                stdout=StringIO(),
            )

    def test_nonexistent_service_id_raises_error(self, service):
        with pytest.raises(CommandError, match="does not exist"):
            call_command(
                "generate_logs", "--count=5",
                "--service=999999",
                stdout=StringIO(),
            )

    def test_no_services_raises_error(self, db):
        with pytest.raises(CommandError, match="No services found"):
            call_command(
                "generate_logs", "--count=5", stdout=StringIO(),
            )


# ============================================================
# Status Validation
# ============================================================


@pytest.mark.django_db
class TestGenerateLogsStatusValidation:
    """
    Tests for --status argument validation.
    """

    @patch("monitoring.management.commands.generate_logs.BenchmarkService")
    def test_locked_status_success(self, mock_bench, service):
        mock_bench.measure_execution_time.side_effect = lambda fn: (fn(), 10.0)[1]
        mock_bench.measure_memory_usage.return_value = {
            "before_mb": 0, "after_mb": 0, "diff_mb": 0,
        }
        mock_bench.format_result.return_value = {"label": "test", "status": "SUCCESS"}

        call_command(
            "generate_logs", "--count=10", "--status=success",
            stdout=StringIO(),
        )

        assert Log.objects.filter(status=LogStatus.SUCCESS).count() == 10

    @patch("monitoring.management.commands.generate_logs.BenchmarkService")
    def test_locked_status_error(self, mock_bench, service):
        mock_bench.measure_execution_time.side_effect = lambda fn: (fn(), 10.0)[1]
        mock_bench.measure_memory_usage.return_value = {
            "before_mb": 0, "after_mb": 0, "diff_mb": 0,
        }
        mock_bench.format_result.return_value = {"label": "test", "status": "SUCCESS"}

        call_command(
            "generate_logs", "--count=10", "--status=error",
            stdout=StringIO(),
        )

        assert Log.objects.filter(status=LogStatus.ERROR).count() == 10

    @patch("monitoring.management.commands.generate_logs.BenchmarkService")
    def test_locked_status_warning(self, mock_bench, service):
        mock_bench.measure_execution_time.side_effect = lambda fn: (fn(), 10.0)[1]
        mock_bench.measure_memory_usage.return_value = {
            "before_mb": 0, "after_mb": 0, "diff_mb": 0,
        }
        mock_bench.format_result.return_value = {"label": "test", "status": "SUCCESS"}

        call_command(
            "generate_logs", "--count=10", "--status=warning",
            stdout=StringIO(),
        )

        assert Log.objects.filter(status=LogStatus.WARNING).count() == 10

    def test_invalid_status_raises_error(self, service):
        with pytest.raises(CommandError):
            call_command(
                "generate_logs", "--count=10", "--status=invalid_status",
                stdout=StringIO(), stderr=StringIO(),
            )


# ============================================================
# Deterministic Seed
# ============================================================


@pytest.mark.django_db
class TestGenerateLogsSeed:
    """
    Tests for --seed deterministic generation.
    """

    @patch("monitoring.management.commands.generate_logs.BenchmarkService")
    def test_same_seed_produces_same_statuses(self, mock_bench, service):
        mock_bench.measure_execution_time.side_effect = lambda fn: (fn(), 10.0)[1]
        mock_bench.measure_memory_usage.return_value = {
            "before_mb": 0, "after_mb": 0, "diff_mb": 0,
        }
        mock_bench.format_result.return_value = {"label": "test", "status": "SUCCESS"}

        call_command(
            "generate_logs", "--count=20", "--seed=42",
            stdout=StringIO(),
        )
        statuses_1 = list(
            Log.objects.order_by("pk").values_list("status", flat=True)
        )

        Log.objects.all().delete()

        call_command(
            "generate_logs", "--count=20", "--seed=42",
            stdout=StringIO(),
        )
        statuses_2 = list(
            Log.objects.order_by("pk").values_list("status", flat=True)
        )

        assert statuses_1 == statuses_2

    @patch("monitoring.management.commands.generate_logs.BenchmarkService")
    def test_different_seeds_produce_different_data(self, mock_bench, service):
        mock_bench.measure_execution_time.side_effect = lambda fn: (fn(), 10.0)[1]
        mock_bench.measure_memory_usage.return_value = {
            "before_mb": 0, "after_mb": 0, "diff_mb": 0,
        }
        mock_bench.format_result.return_value = {"label": "test", "status": "SUCCESS"}

        call_command(
            "generate_logs", "--count=50", "--seed=42",
            stdout=StringIO(),
        )
        messages_1 = list(
            Log.objects.order_by("pk").values_list("message", flat=True)
        )

        Log.objects.all().delete()

        call_command(
            "generate_logs", "--count=50", "--seed=99",
            stdout=StringIO(),
        )
        messages_2 = list(
            Log.objects.order_by("pk").values_list("message", flat=True)
        )

        assert messages_1 != messages_2


# ============================================================
# Random Mode
# ============================================================


@pytest.mark.django_db
class TestGenerateLogsRandomMode:
    """
    Tests for --random mode.
    """

    @patch("monitoring.management.commands.generate_logs.BenchmarkService")
    def test_random_generates_mixed_statuses(self, mock_bench, service):
        mock_bench.measure_execution_time.side_effect = lambda fn: (fn(), 10.0)[1]
        mock_bench.measure_memory_usage.return_value = {
            "before_mb": 0, "after_mb": 0, "diff_mb": 0,
        }
        mock_bench.format_result.return_value = {"label": "test", "status": "SUCCESS"}

        call_command(
            "generate_logs", "--count=100", "--random",
            "--seed=42", stdout=StringIO(),
        )

        statuses = set(
            Log.objects.values_list("status", flat=True)
        )

        # With 100 random logs and seed=42, expect multiple statuses
        assert len(statuses) >= 2


# ============================================================
# Dry Run
# ============================================================


@pytest.mark.django_db
class TestGenerateLogsDryRun:
    """
    Tests for --dry-run mode.
    """

    @patch("monitoring.management.commands.generate_logs.BenchmarkService")
    def test_dry_run_creates_no_records(self, mock_bench, service):
        mock_bench.measure_execution_time.side_effect = lambda fn: (fn(), 10.0)[1]
        mock_bench.measure_memory_usage.return_value = {
            "before_mb": 0, "after_mb": 0, "diff_mb": 0,
        }
        mock_bench.format_result.return_value = {"label": "test", "status": "SUCCESS"}

        call_command(
            "generate_logs", "--count=100", "--dry-run",
            stdout=StringIO(),
        )

        assert Log.objects.count() == 0

    @patch("monitoring.management.commands.generate_logs.BenchmarkService")
    def test_dry_run_still_prints_progress(self, mock_bench, service):
        mock_bench.measure_execution_time.side_effect = lambda fn: (fn(), 10.0)[1]
        mock_bench.measure_memory_usage.return_value = {
            "before_mb": 0, "after_mb": 0, "diff_mb": 0,
        }
        mock_bench.format_result.return_value = {"label": "test", "status": "SUCCESS"}

        stdout = StringIO()

        call_command(
            "generate_logs", "--count=10", "--batch-size=5",
            "--dry-run", stdout=stdout,
        )

        output = stdout.getvalue()

        assert "5 / 10" in output
        assert "10 / 10" in output


# ============================================================
# Clear Existing
# ============================================================


@pytest.mark.django_db
class TestGenerateLogsClearExisting:
    """
    Tests for --clear-existing mode.
    """

    @patch("monitoring.management.commands.generate_logs.BenchmarkService")
    def test_clear_existing_deletes_old_logs(self, mock_bench, service, log):
        mock_bench.measure_execution_time.side_effect = lambda fn: (fn(), 10.0)[1]
        mock_bench.measure_memory_usage.return_value = {
            "before_mb": 0, "after_mb": 0, "diff_mb": 0,
        }
        mock_bench.format_result.return_value = {"label": "test", "status": "SUCCESS"}

        initial_count = Log.objects.count()
        assert initial_count >= 1

        call_command(
            "generate_logs", "--count=5", "--clear-existing",
            f"--service={service.pk}", stdout=StringIO(),
        )

        assert Log.objects.count() == 5

    @patch("monitoring.management.commands.generate_logs.BenchmarkService")
    def test_clear_existing_dry_run_does_not_delete(self, mock_bench, service, log):
        mock_bench.measure_execution_time.side_effect = lambda fn: (fn(), 10.0)[1]
        mock_bench.measure_memory_usage.return_value = {
            "before_mb": 0, "after_mb": 0, "diff_mb": 0,
        }
        mock_bench.format_result.return_value = {"label": "test", "status": "SUCCESS"}

        initial_count = Log.objects.count()

        call_command(
            "generate_logs", "--count=5", "--clear-existing", "--dry-run",
            stdout=StringIO(),
        )

        assert Log.objects.count() == initial_count


# ============================================================
# Bulk Create
# ============================================================


@pytest.mark.django_db
class TestGenerateLogsBulkCreate:
    """
    Tests verifying bulk_create behavior.
    """

    @patch("monitoring.management.commands.generate_logs.BenchmarkService")
    @patch("monitoring.management.commands.generate_logs.Log.objects")
    def test_bulk_create_called(self, mock_manager, mock_bench, service):
        mock_bench.measure_execution_time.side_effect = lambda fn: (fn(), 10.0)[1]
        mock_bench.measure_memory_usage.return_value = {
            "before_mb": 0, "after_mb": 0, "diff_mb": 0,
        }
        mock_bench.format_result.return_value = {"label": "test", "status": "SUCCESS"}

        mock_manager.first.return_value = service

        call_command(
            "generate_logs", "--count=10", "--batch-size=5",
            stdout=StringIO(),
        )

        assert mock_manager.bulk_create.call_count == 2

    @patch("monitoring.management.commands.generate_logs.BenchmarkService")
    @patch("monitoring.management.commands.generate_logs.Log.objects")
    def test_bulk_create_receives_correct_batch_size(
        self, mock_manager, mock_bench, service
    ):
        mock_bench.measure_execution_time.side_effect = lambda fn: (fn(), 10.0)[1]
        mock_bench.measure_memory_usage.return_value = {
            "before_mb": 0, "after_mb": 0, "diff_mb": 0,
        }
        mock_bench.format_result.return_value = {"label": "test", "status": "SUCCESS"}

        mock_manager.first.return_value = service

        call_command(
            "generate_logs", "--count=7", "--batch-size=3",
            stdout=StringIO(),
        )

        # 3 batches: 3, 3, 1
        assert mock_manager.bulk_create.call_count == 3
        batch_sizes = [
            len(c.args[0]) for c in mock_manager.bulk_create.call_args_list
        ]
        assert batch_sizes == [3, 3, 1]


# ============================================================
# Progress Output
# ============================================================


@pytest.mark.django_db
class TestGenerateLogsProgressOutput:
    """
    Tests for progress output.
    """

    @patch("monitoring.management.commands.generate_logs.BenchmarkService")
    def test_progress_printed_per_batch(self, mock_bench, service):
        mock_bench.measure_execution_time.side_effect = lambda fn: (fn(), 10.0)[1]
        mock_bench.measure_memory_usage.return_value = {
            "before_mb": 0, "after_mb": 0, "diff_mb": 0,
        }
        mock_bench.format_result.return_value = {"label": "test", "status": "SUCCESS"}

        stdout = StringIO()

        call_command(
            "generate_logs", "--count=30", "--batch-size=10",
            stdout=stdout,
        )

        output = stdout.getvalue()

        assert "10 / 30" in output
        assert "20 / 30" in output
        assert "30 / 30" in output


# ============================================================
# Summary Output
# ============================================================


@pytest.mark.django_db
class TestGenerateLogsSummaryOutput:
    """
    Tests for benchmark summary output.
    """

    @patch("monitoring.management.commands.generate_logs.BenchmarkService")
    def test_print_summary_called(self, mock_bench, service):
        mock_bench.measure_execution_time.side_effect = lambda fn: (fn(), 10.0)[1]
        mock_bench.measure_memory_usage.return_value = {
            "before_mb": 0, "after_mb": 0, "diff_mb": 0,
        }
        mock_bench.format_result.return_value = {"label": "test", "status": "SUCCESS"}

        call_command(
            "generate_logs", "--count=5", stdout=StringIO(),
        )

        mock_bench.print_summary.assert_called_once()

    @patch("monitoring.management.commands.generate_logs.BenchmarkService")
    def test_format_result_called_with_correct_count(self, mock_bench, service):
        mock_bench.measure_execution_time.side_effect = lambda fn: (fn(), 10.0)[1]
        mock_bench.measure_memory_usage.return_value = {
            "before_mb": 0, "after_mb": 0, "diff_mb": 0,
        }
        mock_bench.format_result.return_value = {"label": "test", "status": "SUCCESS"}

        call_command(
            "generate_logs", "--count=50", stdout=StringIO(),
        )

        _, kwargs = mock_bench.format_result.call_args
        assert kwargs["rows"] == 50
        assert kwargs["dataset_size"] == 50
