from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DeviceViewSet, DeviceInterfaceViewSet

router = DefaultRouter()
router.register(r'', DeviceViewSet, basename='device')
router.register(r'interfaces', DeviceInterfaceViewSet, basename='device-interface')

urlpatterns = [
    path('', include(router.urls)),
]
