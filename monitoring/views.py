from django_filters.rest_framework import DjangoFilterBackend

# pyrefly: ignore [missing-import]
from rest_framework import mixins, viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response
from rest_framework.views import APIView

# from rest_framework.permissions import AllowAny

from monitoring.pagination import LogCursorPagination
from monitoring.filters import LogFilter

from monitoring.models import Log
from monitoring.serializers.log_serializer import (
    LogWriteSerializer,
    LogReadSerializer
)


from monitoring.schemas.log_schema import (
    list_logs_schema,
    create_log_schema,
    retrieve_log_schema,
)

from monitoring.schemas.health_schema import health_check_schema

from monitoring.tasks import process_log_for_alerts_task

from monitoring.services.health_service import get_health_status

from django.db import transaction



class HealthCheckAPIView(APIView):
    """
    Lightweight health-check endpoint for orchestrators.

    Unauthenticated so Docker HEALTHCHECK, Kubernetes liveness
    probes, and load balancer health checks can reach it without
    credentials.

    All logic lives in the health service — this view only
    delegates and returns the response.
    """

    authentication_classes = []
    permission_classes = []

    @health_check_schema
    def get(self, request):
        """
        GET /health/

        Returns application health status.
        """

        health = get_health_status()

        http_status = (
            status.HTTP_200_OK
            if health.get("status") == "healthy"
            else status.HTTP_503_SERVICE_UNAVAILABLE
        )

        response = Response(health, status=http_status)
        response["Cache-Control"] = "no-store"

        return response





class LogViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet
):
    """
    Allowed:
    - create
    - list
    - retrieve

    Blocked:
    - update
    - partial_update
    - delete
    """

    http_method_names = ['get', 'post']

    permission_classes = [IsAuthenticated]  

    # Query optimization
    queryset = (
        Log.objects
        .select_related('service', 'service__created_by')
        .order_by('-created_at')
    )

    # Filtering
    filter_backends = [DjangoFilterBackend, OrderingFilter]

    filterset_class = LogFilter

    ordering_fields = [
        'created_at',
        'response_time_ms',
    ]

    # Ordering
    ordering = ['-created_at']  # default

    #cursor pagination
    pagination_class = LogCursorPagination


    def get_serializer_class(self):
        """
        Serializer switching:
        - create -> write serializer
        - list/retrieve -> read serializer
        """

        if self.action == 'create':
            return LogWriteSerializer

        return LogReadSerializer

    def get_queryset(self):
        """
        Future-safe queryset hook.

        Add:
        - user scoping
        - tenant filtering
        - RBAC
        - soft delete filtering

        later here.
        """

        queryset = super().get_queryset()

        # Optional future filtering examples:
        # queryset = queryset.filter(service__owner=self.request.user)

        return queryset

    def perform_create(self, serializer):
        """
        Central place for:
        - audit logging
        - async tasks
        - metrics
        - alert triggering

        later.
        """

        log = serializer.save()

        # Used to trigger alerts based on log content. Can be extended to send to Celery for async processing if needed.
        # process_log_for_alerts(log)


        transaction.on_commit(lambda: process_log_for_alerts_task.delay(log.id))
        # Why
        # Imagine:

        # Save Log
        # ↓
        # Queue Celery Task
        # ↓
        # Worker Starts
        # ↓
        # Database transaction hasn't committed yet
        # ↓
        # Log.objects.get(id)
        # ↓
        # DoesNotExist
        # This is a real production race condition.
        # transaction.on_commit() completely eliminates it.





    @list_logs_schema
    def list(self, request, *args, **kwargs):
        """
        GET /logs/

        Returns paginated logs with:
        - filtering
        - ordering
        - cursor pagination
        """

        return super().list(request, *args, **kwargs)





    @create_log_schema
    def create(self, request, *args, **kwargs):
        """
        POST /logs/

        Creates monitoring log entry.
        """

        return super().create(request, *args, **kwargs)




    @retrieve_log_schema  
    def retrieve(self, request, *args, **kwargs):
        """
        GET /logs/{id}/

        Returns single log entry.
        """

        return super().retrieve(request, *args, **kwargs)