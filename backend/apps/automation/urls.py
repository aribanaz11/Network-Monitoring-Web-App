from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AutomationJobViewSet

router = DefaultRouter()
router.register(r'jobs', AutomationJobViewSet, basename='automation-job')

urlpatterns = [
    path('', include(router.urls)),
]
