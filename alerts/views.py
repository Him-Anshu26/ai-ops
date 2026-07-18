from django.utils import timezone

from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
# from rest_framework.permissions import AllowAny
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from alerts.filters import AlertFilter
from alerts.models import Alert, AlertStatus
from alerts.pagination import AlertCursorPagination

from alerts.serializers.alert_serializer import (
    AlertWriteSerializer,
    AlertReadSerializer,
    AlertResolveSerializer,
)



from alerts.schemas.alert_schema import (
    list_alerts_schema,
    create_alert_schema,
    retrieve_alert_schema,
    resolve_alert_schema,
)





class AlertViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    Production-grade Alert ViewSet.

    Allowed Operations:
    - create
    - list
    - retrieve
    - resolve (custom workflow action)

    Blocked Operations:
    - update
    - partial_update
    - delete

    Alerts are treated as immutable incident records.

    Generic update/delete operations are intentionally restricted.
    """

    # Explicitly allowed HTTP methods
    http_method_names = ['get', 'post']

    permission_classes = [IsAuthenticated]

    # Optimized queryset
    #
    # select_related prevents N+1 queries
    # when accessing related service data.
    queryset = (
        Alert.objects
        .select_related('service')
        .order_by('-created_at')
    )

    # Filtering backend configuration
    filter_backends = [
        DjangoFilterBackend,
        OrderingFilter,
    ]

    # Custom django-filter class
    filterset_class = AlertFilter

    # Cursor pagination for scalable alert retrieval
    pagination_class = AlertCursorPagination

    # Allowed ordering fields
    ordering_fields = [
        'created_at',
        'severity',
        'trigger_count',
        'last_triggered_at',
    ]

    # Default ordering
    ordering = ['-created_at']




    def get_serializer_class(self):
        """
        Dynamically switch serializers based on action.

        Purpose:
        - separate write validation
        - optimize read responses
        - isolate workflow validation
        """

        # Manual alert creation
        if self.action == 'create':
            return AlertWriteSerializer

        # Alert resolution workflow
        if self.action == 'resolve':
            return AlertResolveSerializer

        # Default read serializer
        return AlertReadSerializer




    def get_queryset(self):
        """
        Production-ready queryset hook.

        Current behavior:
        - return only open/unresolved alerts by default

        Future use cases:
        - RBAC filtering
        - tenant scoping
        - organization isolation
        - soft delete filtering
        """

        queryset = super().get_queryset()

        # Default dashboard behavior:
        # show unresolved alerts unless status filter is explicitly provided
        if not self.request.query_params.get('status'):

            queryset = queryset.filter(
                status__in=[
                    AlertStatus.OPEN,
                    AlertStatus.ACKNOWLEDGED,
                ]
            )

        return queryset




    def perform_create(self, serializer):
        """
        Centralized alert creation hook.

        Future responsibilities:
        - audit logging
        - metrics collection
        - websocket broadcasting
        - Slack/email notifications
        - Celery task triggering
        """

        serializer.save()




    def list(self, request, *args, **kwargs):
        """
        GET /alerts/

        Returns paginated alerts with:
        - filtering
        - ordering
        - cursor pagination
        """

        return super().list(request, *args, **kwargs)




    def create(self, request, *args, **kwargs):
        """
        POST /alerts/

        Temporary endpoint for:
        - manual testing
        - QA workflows
        - development purposes

        Future production flow:
        Logs
        -> Alert Engine
        -> Alert Creation
        """

        return super().create(request, *args, **kwargs)




    def retrieve(self, request, *args, **kwargs):
        """
        GET /alerts/{id}/

        Returns detailed alert information.
        """

        return super().retrieve(request, *args, **kwargs)




    @action(
        detail=True,
        methods=['post'],
        url_path='resolve',
    )
    def resolve(self, request, *args, **kwargs):
        """
        POST /alerts/{id}/resolve/

        Controlled workflow endpoint for resolving alerts.

        Why custom action instead of PATCH?

        Because resolving an alert is:
        - workflow-driven
        - audit-sensitive
        - state-transition logic

        NOT generic CRUD updating.
        """

        alert = self.get_object()

        serializer = self.get_serializer(
            alert,
            data=request.data,
            partial=True,
        )

        serializer.is_valid(raise_exception=True)

        # Mark alert as resolved
        serializer.save(
            resolved_at=timezone.now(),
        )

        # Return updated alert using read serializer
        response_serializer = AlertReadSerializer(alert)

        return Response(
            response_serializer.data,
            status=status.HTTP_200_OK,
        )
    



@list_alerts_schema
def list(self, request, *args, **kwargs):
    """
    GET /alerts/

    Returns paginated alerts with:
    - filtering
    - ordering
    - cursor pagination
    """

    return super().list(request, *args, **kwargs)




@create_alert_schema
def create(self, request, *args, **kwargs):
    """
    POST /alerts/

    Temporary endpoint for:
    - manual testing
    - QA workflows
    - development purposes

    Future production flow:

    Logs
        ↓
    Alert Engine
        ↓
    Alert Creation
    """

    return super().create(request, *args, **kwargs)




@retrieve_alert_schema
def retrieve(self, request, *args, **kwargs):
    """
    GET /alerts/{id}/

    Returns detailed alert information.
    """

    return super().retrieve(request, *args, **kwargs)




@resolve_alert_schema
@action(
    detail=True,
    methods=['post'],
    url_path='resolve',
)
def resolve(self, request, *args, **kwargs):
    """
    POST /alerts/{id}/resolve/

    Controlled workflow endpoint for resolving alerts.

    Why custom action instead of PATCH?

    Because resolving an alert is:
    - workflow-driven
    - audit-sensitive
    - state-transition logic

    NOT generic CRUD updating.
    """

    alert = self.get_object()

    serializer = self.get_serializer(
        alert,
        data=request.data,
        partial=True,
    )

    serializer.is_valid(raise_exception=True)

    serializer.save(
        resolved_at=timezone.now(),
    )

    response_serializer = AlertReadSerializer(alert)

    return Response(
        response_serializer.data,
        status=status.HTTP_200_OK,
    )