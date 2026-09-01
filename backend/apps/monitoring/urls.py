from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    MonitoringCheckViewSet,
    MonitoringLogViewSet,
    DevicePingView,
    DeviceTCPCheckView,
    FleetPollingTriggerView,
    CeleryWorkerStatusView
)

router = DefaultRouter()
router.register(r'checks', MonitoringCheckViewSet, basename='monitoring-check')
router.register(r'logs', MonitoringLogViewSet, basename='monitoring-log')

urlpatterns = [
    path('devices/<uuid:device_id>/ping/', DevicePingView.as_view(), name='device_ping'),
    path('devices/<uuid:device_id>/tcp-check/', DeviceTCPCheckView.as_view(), name='device_tcp_check'),
    path('fleet/poll-now/', FleetPollingTriggerView.as_view(), name='fleet_poll_now'),
    path('tasks/status/', CeleryWorkerStatusView.as_view(), name='celery_tasks_status'),
    path('', include(router.urls)),
]
