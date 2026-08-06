from django.test import TestCase

from rest_framework.pagination import CursorPagination
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from alerts.pagination import AlertCursorPagination

from tests.factories import AlertFactory


# ============================================================
# Helper View
# ============================================================


class DummyView:
    """
    Minimal DRF view for pagination tests.
    """

    pass


# ============================================================
# AlertCursorPagination Configuration Tests
# ============================================================


class AlertCursorPaginationConfigurationTests(TestCase):
    """
    Unit tests for AlertCursorPagination configuration.
    """

    def setUp(
        self,
    ):
        self.pagination = AlertCursorPagination()

    def test_default_page_size(
        self,
    ):
        self.assertEqual(
            self.pagination.page_size,
            20,
        )

    def test_page_size_query_param(
        self,
    ):
        self.assertEqual(
            self.pagination.page_size_query_param,
            "page_size",
        )

    def test_max_page_size(
        self,
    ):
        self.assertEqual(
            self.pagination.max_page_size,
            100,
        )

    def test_default_ordering(
        self,
    ):
        self.assertEqual(
            self.pagination.ordering,
            "-created_at",
        )

    def test_inherits_cursor_pagination(
        self,
    ):
        self.assertIsInstance(
            self.pagination,
            CursorPagination,
        )

    def test_pagination_instance_created(
        self,
    ):
        self.assertIsNotNone(
            self.pagination,
        )


# ============================================================
# AlertCursorPagination Functional Tests
# ============================================================


class AlertCursorPaginationFunctionalTests(TestCase):
    """
    Functional tests for AlertCursorPagination.
    """

    def setUp(
        self,
    ):
        self.factory = APIRequestFactory()

        self.pagination = AlertCursorPagination()

        self.view = DummyView()

    def test_returns_first_page(
        self,
    ):
        AlertFactory.create_batch(
            25,
        )

        request = Request(
            self.factory.get(
                "/api/v1/alerts/",
            )
        )

        queryset = AlertFactory._meta.model.objects.all()

        page = self.pagination.paginate_queryset(
            queryset,
            request,
            view=self.view,
        )

        self.assertEqual(
            len(page),
            20,
        )

    def test_respects_custom_page_size(
        self,
    ):
        AlertFactory.create_batch(
            25,
        )

        request = Request(
            self.factory.get(
                "/api/v1/alerts/?page_size=5",
            )
        )

        queryset = AlertFactory._meta.model.objects.all()

        page = self.pagination.paginate_queryset(
            queryset,
            request,
            view=self.view,
        )

        self.assertEqual(
            len(page),
            5,
        )

    def test_caps_page_size_at_max(
        self,
    ):
        AlertFactory.create_batch(
            110,
        )

        request = Request(
            self.factory.get(
                "/api/v1/alerts/?page_size=500",
            )
        )

        queryset = AlertFactory._meta.model.objects.all()

        page = self.pagination.paginate_queryset(
            queryset,
            request,
            view=self.view,
        )

        self.assertEqual(
            len(page),
            100,
        )

    def test_returns_all_results_when_less_than_page_size(
        self,
    ):
        AlertFactory.create_batch(
            8,
        )

        request = Request(
            self.factory.get(
                "/api/v1/alerts/",
            )
        )

        queryset = AlertFactory._meta.model.objects.all()

        page = self.pagination.paginate_queryset(
            queryset,
            request,
            view=self.view,
        )

        self.assertEqual(
            len(page),
            8,
        )

    def test_results_ordered_by_created_at_desc(
        self,
    ):
        older = AlertFactory()

        newer = AlertFactory()

        request = Request(
            self.factory.get(
                "/api/v1/alerts/",
            )
        )

        queryset = AlertFactory._meta.model.objects.all()

        page = self.pagination.paginate_queryset(
            queryset,
            request,
            view=self.view,
        )

        self.assertEqual(
            page[0],
            newer,
        )

    def test_next_link_generated(
        self,
    ):
        AlertFactory.create_batch(
            30,
        )

        request = Request(
            self.factory.get(
                "/api/v1/alerts/",
            )
        )

        queryset = AlertFactory._meta.model.objects.all()

        self.pagination.paginate_queryset(
            queryset,
            request,
            view=self.view,
        )

        response = self.pagination.get_paginated_response(
            [],
        )

        self.assertIsNotNone(
            response.data["next"],
        )