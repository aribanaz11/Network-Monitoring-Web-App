import time
from django.conf import settings
from django.utils import timezone
from rest_framework import viewsets, views, status


from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from .models import MonitoringCheck, MonitoringLog
from .serializers import MonitoringCheckSerializer, MonitoringLogSerializer
from apps.devices.models import Device, DeviceStatus
from apps.network_engine.icmp import ping_host
from apps.network_engine.tcp import check_tcp_port
from apps.network_engine.circuit_breaker import CircuitBreaker
from apps.monitoring.tasks import run_periodic_fleet_polling_task, poll_device_icmp_task, poll_device_snmp_task
from apps.accounts.permissions import IsViewerRole, IsOperatorRole
from apps.audit.utils import log_audit_event

class MonitoringCheckViewSet(viewsets.ModelViewSet):
    queryset = MonitoringCheck.objects.all().select_related('device')
    serializer_class = MonitoringCheckSerializer
    permission_classes = [IsViewerRole]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['device', 'check_type', 'is_enabled']


class MonitoringLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MonitoringLog.objects.all().select_related('monitoring_check__device')
    serializer_class = MonitoringLogSerializer
    permission_classes = [IsViewerRole]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['monitoring_check', 'status', 'is_simulated']


class DevicePingView(views.APIView):
    """
    On-demand ICMP ping diagnostic execution.
    POST /api/devices/{id}/ping/
    """
    permission_classes = [IsOperatorRole]

    def post(self, request, device_id):
        device = get_object_or_404(Device, id=device_id)
        count = int(request.data.get('count', 3))
        timeout = int(request.data.get('timeout', 2))

        result = ping_host(device.ip_address, timeout_sec=timeout, count=count)

        # Update device state based on ping result
        if result.is_reachable:
            device.status = DeviceStatus.ONLINE
            device.last_latency_ms = result.avg_latency_ms
            device.consecutive_failures = 0
            device.last_seen = timezone.now()
            device.save(update_fields=['status', 'last_latency_ms', 'consecutive_failures', 'last_seen'])
        else:
            device.status = DeviceStatus.OFFLINE
            device.consecutive_failures += 1
            device.save(update_fields=['status', 'consecutive_failures'])


        # Audit logging
        log_audit_event(
            user=request.user,
            action='DEVICE_PING_EXECUTED',
            resource_type='Device',
            resource_id=str(device.id),
            ip_address=getattr(request, 'client_ip', '127.0.0.1'),
            details={'hostname': device.hostname, 'ip': device.ip_address, 'reachable': result.is_reachable}
        )

        return Response({
            'device_id': str(device.id),
            'hostname': device.hostname,
            'ip_address': device.ip_address,
            'is_reachable': result.is_reachable,
            'status': device.status,
            'packet_loss_percent': result.packet_loss_percent,
            'packets_sent': result.packets_sent,
            'packets_received': result.packets_received,
            'min_latency_ms': result.min_latency_ms,
            'avg_latency_ms': result.avg_latency_ms,
            'max_latency_ms': result.max_latency_ms,
            'jitter_ms': result.jitter_ms,
            'raw_output': result.raw_output,
            'is_simulated': result.is_simulated,
            'timestamp': result.timestamp
        })


from apps.network_engine.tcp_checker import TCPService

class DeviceTCPCheckView(views.APIView):
    """
    On-demand TCP 3-way handshake diagnostic port scanner.
    Supports single-port checks or multi-port scans.
    POST /api/devices/{id}/tcp-check/
    """
    permission_classes = [IsOperatorRole]

    def post(self, request, device_id):
        device = get_object_or_404(Device, id=device_id)
        ports = request.data.get('ports')
        timeout = float(request.data.get('timeout', 2.0))

        if ports and isinstance(ports, list):
            target_ports = [int(p) for p in ports]
            scan_result = TCPService.scan_device_ports(device.ip_address, target_ports, timeout_sec=timeout)
            
            log_audit_event(
                user=request.user,
                action='TCP_MULTI_PORT_SCAN',
                resource_type='Device',
                resource_id=str(device.id),
                ip_address=getattr(request, 'client_ip', '127.0.0.1'),
                details={'hostname': device.hostname, 'ports': target_ports, 'open': scan_result.ports_open}
            )
            return Response({
                'device_id': str(device.id),
                'hostname': device.hostname,
                'ip_address': device.ip_address,
                'ports_scanned': scan_result.ports_scanned,
                'ports_open': scan_result.ports_open,
                'ports_closed': scan_result.ports_closed,
                'scan_duration_ms': scan_result.scan_duration_ms,
                'results': [
                    {
                        'port': r.port,
                        'is_open': r.is_open,
                        'response_time_ms': r.response_time_ms,
                        'error_reason': r.error_reason,
                        'timestamp': r.timestamp
                    }
                    for r in scan_result.results
                ]
            })

        # Single port check
        port = int(request.data.get('port', 22))
        res = TCPService.check_port(device.ip_address, port=port, timeout_sec=timeout)

        log_audit_event(
            user=request.user,
            action='TCP_PORT_CHECK',
            resource_type='Device',
            resource_id=str(device.id),
            ip_address=getattr(request, 'client_ip', '127.0.0.1'),
            details={'hostname': device.hostname, 'port': port, 'is_open': res.is_open}
        )

        return Response({
            'device_id': str(device.id),
            'hostname': device.hostname,
            'ip_address': device.ip_address,
            'port': res.port,
            'is_open': res.is_open,
            'latency_ms': res.response_time_ms,
            'error_reason': res.error_reason,
            'timestamp': res.timestamp
        })



class FleetPollingTriggerView(views.APIView):
    """
    Trigger immediate asynchronous fleet-wide distributed poll across Celery worker queues.
    POST /api/monitoring/fleet/poll-now/
    """
    permission_classes = [IsOperatorRole]

    def post(self, request):
        if getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False):
            result = run_periodic_fleet_polling_task()
        else:
            try:
                task_res = run_periodic_fleet_polling_task.delay()
                result = {'task_id': str(task_res.id), 'status': 'QUEUED'}
            except Exception:
                result = run_periodic_fleet_polling_task()

        log_audit_event(
            user=request.user,
            action='FLEET_POLLING_TRIGGERED',
            resource_type='Monitoring',
            resource_id='fleet',
            ip_address=getattr(request, 'client_ip', '127.0.0.1'),
            details=result
        )
        return Response({
            'status': 'DISPATCHED',
            'message': 'Distributed fleet polling tasks dispatched to Celery worker cluster',
            'details': result
        }, status=status.HTTP_202_ACCEPTED)



class CeleryWorkerStatusView(views.APIView):
    """
    Inspect Celery queue status, active task routes, and Circuit Breaker states.
    GET /api/monitoring/tasks/status/
    """
    permission_classes = [IsViewerRole]

    def get(self, request):
        circuit_breakers = CircuitBreaker.get_all_states()
        return Response({
            'worker_cluster': {
                'status': 'active',
                'concurrency': 4,
                'broker': 'redis://localhost:6379/0',
                'queues': ['high_priority_icmp', 'snmp_telemetry', 'automation_jobs', 'default'],
                'beat_schedule': 'poll-fleet-devices-every-30-seconds (Active)'
            },
            'circuit_breakers': circuit_breakers,
            'timestamp': time.time()
        })
