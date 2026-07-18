from django.urls import include, path
from rest_framework.routers import DefaultRouter

from alerts.views import AlertViewSet

router = DefaultRouter()


# Register the AlertViewSet with the router
router.register(r'', AlertViewSet, basename='alerts')


urlpatterns = [
    # Include the router-generated URLs
    path('', include(router.urls)),
]