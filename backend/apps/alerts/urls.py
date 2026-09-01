from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AlertViewSet, IncidentViewSet

router = DefaultRouter()
router.register(r'incidents', IncidentViewSet, basename='incident')
router.register(r'', AlertViewSet, basename='alert')

urlpatterns = [
    path('', include(router.urls)),
]
