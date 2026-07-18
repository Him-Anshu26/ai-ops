from drf_spectacular.utils import (
    extend_schema,
    OpenApiExample,
    OpenApiParameter,
)

from monitoring.serializers.log_serializer import LogReadSerializer, LogWriteSerializer




list_logs_schema = extend_schema(
    tags=['Logs'],

    summary='List monitoring logs',
    description=(
        'Retrieve paginated monitoring logs with '
        'filtering and ordering support.'
    ),

    parameters=[
        OpenApiParameter(
            name='service',
            description='Filter logs by service ID.',
            required=False,
            type=int,
        ),

        OpenApiParameter(
            name='status',
            description='Filter logs by status.',
            required=False,
            type=str,
        ),

        OpenApiParameter(
            name='status_code',
            description='Filter logs by HTTP status code.',
            required=False,
            type=int,
        ),

        OpenApiParameter(
            name='created_after',
            description='Return logs created after this datetime.',
            required=False,
            type=str,
        ),

        OpenApiParameter(
            name='created_before',
            description='Return logs created before this datetime.',
            required=False,
            type=str,
        ),

        OpenApiParameter(
            name='min_response_time',
            description='Minimum response time in milliseconds.',
            required=False,
            type=int,
        ),

        OpenApiParameter(
            name='max_response_time',
            description='Maximum response time in milliseconds.',
            required=False,
            type=int,
        ),

        OpenApiParameter(
            name='ordering',
            description=(
                'Order results by created_at or response_time_ms. '
                'Use "-" for descending order.'
            ),
            required=False,
            type=str,
        ),
    ],

    examples=[
        OpenApiExample(
            'Filter By Status',
            description='Retrieve only error logs.',
            value={
                'url': '/api/v1/monitoring/logs/?status=error'
            },
            request_only=True,
        ),

        OpenApiExample(
            'Filter By Service',
            description='Retrieve logs for a specific service.',
            value={
                'url': '/api/v1/monitoring/logs/?service=1'
            },
            request_only=True,
        ),

        OpenApiExample(
            'Ordering Example',
            description='Order logs by response time.',
            value={
                'url': '/api/v1/monitoring/logs/?ordering=-response_time_ms'
            },
            request_only=True,
        ),
    ]
    )




create_log_schema = extend_schema(

    tags=['Logs'],

    summary='Create monitoring log',
    description=(
        'Create a new monitoring log entry. '
        'Used by monitored services and internal systems.'
    ),

    request=LogWriteSerializer,
    responses={
        201: LogReadSerializer,
    },

    examples=[
        OpenApiExample(
            'Success Log Example',
            description='Successful request log.',
            value={
                'service': 1,
                'status': 'success',
                'status_code': 200,
                'response_time_ms': 120,
                'message': 'Request completed successfully'
            },
            request_only=True,
        ),

        OpenApiExample(
            'Error Log Example',
            description='Internal server error log.',
            value={
                'service': 1,
                'status': 'error',
                'status_code': 500,
                'response_time_ms': 3200,
                'message': 'Database connection failed'
            },
            request_only=True,
        ),

        OpenApiExample(
            'Validation Error Example',
            description='Invalid response time.',
            value={
                'response_time_ms': [
                    'Response time cannot be negative.'
                ]
            },
            response_only=True,
            status_codes=['400'],
        ),
    ]
    )






retrieve_log_schema = extend_schema(
    tags=['Logs'],

    summary='Retrieve single log',
    description=(
        'Retrieve a single monitoring log by ID.'
    ),

    responses={
        200: LogReadSerializer,
    },

    examples=[
        OpenApiExample(
            'Single Log Response',
            description='Example single log response.',
            value={
                'id': 1,
                'service': 1,
                'service_name': 'Auth Service',
                'status': 'success',
                'status_code': 200,
                'response_time_ms': 150,
                'message': 'Login successful',
                'created_at': '2026-05-15T10:30:00Z'
            },
            response_only=True,
        ),
    ]
    )
