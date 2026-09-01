from django.urls import path
from .views import DashboardStatsView, DeviceTelemetryView

urlpatterns = [
    path('dashboard/stats/', DashboardStatsView.as_view(), name='dashboard_stats'),
    path('devices/<uuid:device_id>/telemetry/', DeviceTelemetryView.as_view(), name='device_telemetry'),
]
