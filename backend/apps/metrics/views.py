from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from django.db.models import Avg, Count, Q
from django.utils import timezone
from apps.devices.models import Device, DeviceStatus
from apps.alerts.models import Alert, AlertStatus, AlertSeverity
from apps.monitoring.models import MonitoringCheck
from .mongo_client import telemetry_client
from apps.accounts.permissions import IsViewerRole

class DashboardStatsView(APIView):
    """
    Executive Dashboard Overview KPIs.
    Returns:
    - Total Devices
    - Online / Offline / Degraded Counts
    - Average Latency (ms) across active devices
    - Active Alerts Count (Critical, Warning)
    - Device Type Distribution Breakdown
    """
    permission_classes = [IsViewerRole]

    def get(self, request):
        total_devices = Device.objects.count()
        online_devices = Device.objects.filter(status=DeviceStatus.ONLINE).count()
        offline_devices = Device.objects.filter(status=DeviceStatus.OFFLINE).count()
        degraded_devices = Device.objects.filter(status=DeviceStatus.DEGRADED).count()
        unknown_devices = Device.objects.filter(status=DeviceStatus.UNKNOWN).count()

        avg_lat = Device.objects.filter(status=DeviceStatus.ONLINE, last_latency_ms__isnull=False).aggregate(Avg('last_latency_ms'))['last_latency_ms__avg']
        avg_latency = round(avg_lat, 2) if avg_lat is not None else 0.0

        # Active Alerts
        active_alerts_total = Alert.objects.filter(status__in=[AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED]).count()
        critical_alerts = Alert.objects.filter(status=AlertStatus.OPEN, severity=AlertSeverity.CRITICAL).count()
        warning_alerts = Alert.objects.filter(status=AlertStatus.OPEN, severity=AlertSeverity.WARNING).count()

        # Breakdown by device type
        type_distribution = list(Device.objects.values('device_type').annotate(count=Count('id')).order_by('-count'))
        vendor_distribution = list(Device.objects.values('vendor').annotate(count=Count('id')).order_by('-count'))

        # Recent alerts for dashboard feed
        recent_alerts = list(Alert.objects.filter(status__in=[AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED]).select_related('device').values(
            'id', 'device__hostname', 'severity', 'title', 'status', 'triggered_at'
        )[:5])

        return Response({
            'total_devices': total_devices,
            'online_devices': online_devices,
            'offline_devices': offline_devices,
            'degraded_devices': degraded_devices,
            'unknown_devices': unknown_devices,
            'uptime_percentage': round((online_devices / total_devices * 100), 1) if total_devices > 0 else 100.0,
            'avg_latency_ms': avg_latency,
            'active_alerts_count': active_alerts_total,
            'critical_alerts_count': critical_alerts,
            'warning_alerts_count': warning_alerts,
            'type_distribution': type_distribution,
            'vendor_distribution': vendor_distribution,
            'recent_alerts': recent_alerts,
            'timestamp': timezone.now().isoformat()
        })


class DeviceTelemetryView(APIView):
    """
    Query time-series telemetry metrics for a device from MongoDB / In-memory store.
    """
    permission_classes = [IsViewerRole]

    def get(self, request, device_id):
        metric_type = request.query_params.get('metric_type')
        limit = int(request.query_params.get('limit', 50))
        metrics = telemetry_client.get_device_metrics(device_id=device_id, metric_type=metric_type, limit=limit)
        return Response({
            'device_id': str(device_id),
            'count': len(metrics),
            'metrics': metrics
        })
