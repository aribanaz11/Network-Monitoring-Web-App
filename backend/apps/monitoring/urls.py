from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    MonitoringCheckViewSet,
    DevicePingView,
    DeviceTCPCheckView,
    MonitoringLogListView
)

router = DefaultRouter()
router.register(r'checks', MonitoringCheckViewSet, basename='monitoring-check')

urlpatterns = [
    path('devices/<uuid:device_id>/ping/', DevicePingView.as_view(), name='device_ping'),
    path('devices/<uuid:device_id>/tcp-check/', DeviceTCPCheckView.as_view(), name='device_tcp_check'),
    path('devices/<uuid:device_id>/logs/', MonitoringLogListView.as_view(), name='device_monitoring_logs'),
    path('', include(router.urls)),
]
