from drf_spectacular.utils import (
    extend_schema,
    OpenApiExample,
    OpenApiResponse,
)


health_check_schema = extend_schema(
    tags=['Health'],

    summary='Application health check',
    description=(
        'Lightweight health-check endpoint for orchestrators, '
        'load balancers, and monitoring dashboards. '
        'Returns the status of all critical subsystems including '
        'the application, database, Redis, Celery, and Celery Beat. '
        'This endpoint is unauthenticated.'
    ),

    responses={
        200: OpenApiResponse(
            description='All critical subsystems are healthy.',
        ),
        503: OpenApiResponse(
            description='One or more subsystems are unhealthy.',
        ),
    },

    examples=[
        OpenApiExample(
            'Healthy Response',
            description='All systems operational.',
            value={
                'status': 'healthy',
                'application': {
                    'status': 'healthy',
                },
                'database': {
                    'status': 'healthy',
                    'backend': 'postgresql',
                },
                'redis': {
                    'status': 'healthy',
                },
                'celery': {
                    'status': 'healthy',
                    'broker': 'healthy',
                    'workers': 2,
                },
                'celery_beat': {
                    'status': 'unknown',
                    'info': 'Direct verification not yet implemented.',
                },
                'environment': 'production',
                'api_version': '1.0.0',
                'version': '6.0.3',
                'hostname': 'ai-ops-web-01',
                'timestamp': '2026-07-22T06:30:00+00:00',
                'uptime_seconds': 86421,
                'response_time_ms': 12.34,
            },
            response_only=True,
            status_codes=['200'],
        ),

        OpenApiExample(
            'Unhealthy Response',
            description='Database is unreachable.',
            value={
                'status': 'unhealthy',
                'application': {
                    'status': 'healthy',
                },
                'database': {
                    'status': 'unhealthy',
                    'error': 'connection to server at "localhost" (127.0.0.1), '
                             'port 5432 failed: Connection refused',
                },
                'redis': {
                    'status': 'healthy',
                },
                'celery': {
                    'status': 'healthy',
                    'broker': 'healthy',
                    'workers': 1,
                },
                'celery_beat': {
                    'status': 'unknown',
                    'info': 'Direct verification not yet implemented.',
                },
                'environment': 'production',
                'api_version': '1.0.0',
                'version': '6.0.3',
                'hostname': 'ai-ops-web-01',
                'timestamp': '2026-07-22T06:30:00+00:00',
                'uptime_seconds': 86421,
                'response_time_ms': 3015.72,
            },
            response_only=True,
            status_codes=['503'],
        ),
    ],
)
