from unittest.mock import MagicMock, patch

import django
from django.test import SimpleTestCase
from django.conf import settings

from monitoring.services import health_service


class ApplicationHealthTests(SimpleTestCase):
    """
    Tests for _check_application()
    """

    def test_application_is_always_healthy(self):
        result = health_service._check_application()

        self.assertEqual(
            result,
            {
                "status": "healthy",
            },
        )


class DatabaseHealthTests(SimpleTestCase):
    """
    Tests for _check_database()
    """

    @patch("monitoring.services.health_service.connections")
    def test_database_healthy(
        self,
        mock_connections,
    ):
        connection = MagicMock()

        mock_connections.__getitem__.return_value = connection

        result = health_service._check_database()

        connection.ensure_connection.assert_called_once()

        connection.cursor.return_value.__enter__.return_value.execute.assert_called_once_with(
            "SELECT 1"
        )

        self.assertEqual(
            result["status"],
            "healthy",
        )

        self.assertEqual(
            result["backend"],
            connection.vendor,
        )

    @patch("monitoring.services.health_service.connections")
    def test_database_failure(
        self,
        mock_connections,
    ):
        connection = MagicMock()

        connection.ensure_connection.side_effect = Exception(
            "Database unavailable"
        )

        mock_connections.__getitem__.return_value = connection

        result = health_service._check_database()

        self.assertEqual(
            result["status"],
            "unhealthy",
        )

        self.assertIn(
            "Database unavailable",
            result["error"],
        )


class RedisHealthTests(SimpleTestCase):
    """
    Tests for _check_redis()
    """

    @patch("redis.Redis.from_url")
    def test_redis_ping_success(
        self,
        mock_from_url,
    ):
        client = MagicMock()

        mock_from_url.return_value = client

        with self.settings(
            CELERY_BROKER_URL="redis://localhost:6379/0",
        ):
            result = health_service._check_redis()

        client.ping.assert_called_once()
        client.close.assert_called_once()

        self.assertEqual(
            result,
            {
                "status": "healthy",
            },
        )

    def test_missing_broker_url(self):
        with self.settings(
            CELERY_BROKER_URL="",
        ):
            result = health_service._check_redis()

        self.assertEqual(
            result["status"],
            "unhealthy",
        )

        self.assertIn(
            "CELERY_BROKER_URL",
            result["error"],
        )

    @patch("redis.Redis.from_url")
    def test_redis_connection_failure(
        self,
        mock_from_url,
    ):
        client = MagicMock()

        client.ping.side_effect = Exception(
            "Redis down"
        )

        mock_from_url.return_value = client

        with self.settings(
            CELERY_BROKER_URL="redis://localhost:6379/0",
        ):
            result = health_service._check_redis()

        self.assertEqual(
            result["status"],
            "unhealthy",
        )

        self.assertIn(
            "Redis down",
            result["error"],
        )


class CeleryHealthTests(SimpleTestCase):
    """
    Tests for _check_celery()
    """

    @patch("monitoring.services.health_service.celery_app")
    def test_celery_fully_healthy(
        self,
        mock_celery,
    ):
        connection = MagicMock()

        mock_celery.connection_for_read.return_value = connection

        inspector = MagicMock()
        inspector.ping.return_value = {
            "worker1": {"ok": "pong"},
            "worker2": {"ok": "pong"},
        }

        mock_celery.control.inspect.return_value = inspector

        result = health_service._check_celery()

        connection.ensure_connection.assert_called_once()
        connection.close.assert_called_once()

        inspector.ping.assert_called_once()

        self.assertEqual(
            result["status"],
            "healthy",
        )

        self.assertEqual(
            result["broker"],
            "healthy",
        )

        self.assertEqual(
            result["workers"],
            2,
        )

    @patch("monitoring.services.health_service.celery_app")
    def test_celery_broker_failure(
        self,
        mock_celery,
    ):
        connection = MagicMock()

        connection.ensure_connection.side_effect = Exception(
            "Broker unavailable"
        )

        mock_celery.connection_for_read.return_value = connection

        result = health_service._check_celery()

        self.assertEqual(
            result["status"],
            "unhealthy",
        )

        self.assertEqual(
            result["broker"],
            "unhealthy",
        )

        self.assertIn(
            "Broker unavailable",
            result["error"],
        )

    @patch("monitoring.services.health_service.celery_app")
    def test_no_workers_running(
        self,
        mock_celery,
    ):
        connection = MagicMock()

        mock_celery.connection_for_read.return_value = connection

        inspector = MagicMock()
        inspector.ping.return_value = None

        mock_celery.control.inspect.return_value = inspector

        result = health_service._check_celery()

        self.assertEqual(
            result["status"],
            "unhealthy",
        )

        self.assertEqual(
            result["broker"],
            "healthy",
        )

        self.assertEqual(
            result["workers"],
            0,
        )

        self.assertIn(
            "No workers responded",
            result["error"],
        )

    @patch("monitoring.services.health_service.celery_app")
    def test_worker_ping_exception(
        self,
        mock_celery,
    ):
        connection = MagicMock()

        mock_celery.connection_for_read.return_value = connection

        inspector = MagicMock()
        inspector.ping.side_effect = Exception(
            "Worker timeout"
        )

        mock_celery.control.inspect.return_value = inspector

        result = health_service._check_celery()

        self.assertEqual(
            result["status"],
            "unhealthy",
        )

        self.assertEqual(
            result["broker"],
            "healthy",
        )

        self.assertIn(
            "Worker timeout",
            result["error"],
        )


class CeleryBeatTests(SimpleTestCase):
    """
    Tests for _check_celery_beat()
    """

    def test_celery_beat_returns_unknown(self):
        result = health_service._check_celery_beat()

        self.assertEqual(
            result["status"],
            "unknown",
        )

        self.assertIn(
            "Direct verification",
            result["info"],
        )



class GetHealthStatusTests(SimpleTestCase):
    """
    Tests for get_health_status()
    """

    @patch("monitoring.services.health_service._build_response")
    @patch("monitoring.services.health_service._check_celery_beat")
    @patch("monitoring.services.health_service._check_celery")
    @patch("monitoring.services.health_service._check_redis")
    @patch("monitoring.services.health_service._check_database")
    @patch("monitoring.services.health_service._check_application")
    def test_health_status_success(
        self,
        mock_application,
        mock_database,
        mock_redis,
        mock_celery,
        mock_beat,
        mock_build,
    ):
        mock_application.return_value = {"status": "healthy"}
        mock_database.return_value = {"status": "healthy"}
        mock_redis.return_value = {"status": "healthy"}
        mock_celery.return_value = {"status": "healthy"}
        mock_beat.return_value = {"status": "unknown"}

        mock_build.return_value = {
            "status": "healthy",
        }

        result = health_service.get_health_status()

        self.assertEqual(
            result["status"],
            "healthy",
        )

        mock_build.assert_called_once()

    @patch("monitoring.services.health_service._fallback_response")
    @patch("monitoring.services.health_service._check_application")
    def test_health_status_unexpected_exception(
        self,
        mock_application,
        mock_fallback,
    ):
        mock_application.side_effect = Exception(
            "Unexpected failure"
        )

        mock_fallback.return_value = {
            "status": "unhealthy",
        }

        result = health_service.get_health_status()

        self.assertEqual(
            result["status"],
            "unhealthy",
        )

        mock_fallback.assert_called_once()


class BuildResponseTests(SimpleTestCase):
    """
    Tests for _build_response()
    """

    @patch("monitoring.services.health_service._get_uptime_seconds")
    @patch("monitoring.services.health_service._utc_now_iso")
    @patch("monitoring.services.health_service._get_environment")
    @patch("monitoring.services.health_service._get_api_version")
    def test_all_checks_healthy(
        self,
        mock_api,
        mock_env,
        mock_time,
        mock_uptime,
    ):
        mock_api.return_value = "1.0.0"
        mock_env.return_value = "development"
        mock_time.return_value = "2026-01-01T00:00:00+00:00"
        mock_uptime.return_value = 120

        checks = {
            "application": {"status": "healthy"},
            "database": {"status": "healthy"},
            "redis": {"status": "healthy"},
            "celery": {"status": "healthy"},
            "celery_beat": {"status": "unknown"},
        }

        result = health_service._build_response(
            checks,
            0,
        )

        self.assertEqual(
            result["status"],
            "healthy",
        )

        self.assertEqual(
            result["environment"],
            "development",
        )

        self.assertEqual(
            result["api_version"],
            "1.0.0",
        )

        self.assertEqual(
            result["uptime_seconds"],
            120,
        )

        self.assertEqual(
            result["timestamp"],
            "2026-01-01T00:00:00+00:00",
        )

        self.assertEqual(
            result["version"],
            django.get_version(),
        )

    def test_unhealthy_component_changes_overall_status(self):
        checks = {
            "application": {"status": "healthy"},
            "database": {"status": "healthy"},
            "redis": {"status": "unhealthy"},
            "celery": {"status": "healthy"},
            "celery_beat": {"status": "unknown"},
        }

        result = health_service._build_response(
            checks,
            0,
        )

        self.assertEqual(
            result["status"],
            "unhealthy",
        )

    def test_unknown_status_does_not_make_system_unhealthy(self):
        checks = {
            "application": {"status": "healthy"},
            "database": {"status": "healthy"},
            "redis": {"status": "healthy"},
            "celery": {"status": "healthy"},
            "celery_beat": {"status": "unknown"},
        }

        result = health_service._build_response(
            checks,
            0,
        )

        self.assertEqual(
            result["status"],
            "healthy",
        )


class FallbackResponseTests(SimpleTestCase):
    """
    Tests for _fallback_response()
    """

    @patch("monitoring.services.health_service._get_uptime_seconds")
    @patch("monitoring.services.health_service._utc_now_iso")
    @patch("monitoring.services.health_service._get_environment")
    @patch("monitoring.services.health_service._get_api_version")
    def test_fallback_response(
        self,
        mock_api,
        mock_env,
        mock_timestamp,
        mock_uptime,
    ):
        mock_api.return_value = "1.0.0"
        mock_env.return_value = "development"
        mock_timestamp.return_value = "2026-01-01T00:00:00+00:00"
        mock_uptime.return_value = 321

        result = health_service._fallback_response(0)

        self.assertEqual(
            result["status"],
            "unhealthy",
        )

        self.assertEqual(
            result["environment"],
            "development",
        )

        self.assertEqual(
            result["api_version"],
            "1.0.0",
        )

        self.assertEqual(
            result["uptime_seconds"],
            321,
        )

        self.assertEqual(
            result["timestamp"],
            "2026-01-01T00:00:00+00:00",
        )

        self.assertEqual(
            result["version"],
            django.get_version(),
        )

        self.assertIn(
            "response_time_ms",
            result,
        )


class HelperFunctionTests(SimpleTestCase):
    """
    Tests for helper functions.
    """

    def test_get_environment_development(self):
        with self.settings(DEBUG=True):
            self.assertEqual(
                health_service._get_environment(),
                "development",
            )

    def test_get_environment_production(self):
        with self.settings(DEBUG=False):
            self.assertEqual(
                health_service._get_environment(),
                "production",
            )

    def test_get_api_version(self):
        with self.settings(
            SPECTACULAR_SETTINGS={
                "VERSION": "9.9.9",
            }
        ):
            self.assertEqual(
                health_service._get_api_version(),
                "9.9.9",
            )

    def test_get_api_version_default(self):
        with self.settings(
            SPECTACULAR_SETTINGS={}
        ):
            self.assertEqual(
                health_service._get_api_version(),
                "unknown",
            )

    def test_get_uptime_seconds_returns_integer(self):
        uptime = health_service._get_uptime_seconds()

        self.assertIsInstance(
            uptime,
            int,
        )

        self.assertGreaterEqual(
            uptime,
            0,
        )

    def test_utc_now_iso_returns_string(self):
        value = health_service._utc_now_iso()

        self.assertIsInstance(
            value,
            str,
        )

        self.assertIn(
            "T",
            value,
        )

        self.assertIn(
            "+00:00",
            value,
        )