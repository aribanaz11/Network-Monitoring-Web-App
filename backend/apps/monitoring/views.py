from rest_framework import viewsets, views, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from .models import MonitoringCheck, MonitoringLog, CheckStatus, CheckType
from .serializers import (
    MonitoringCheckSerializer,
    MonitoringLogSerializer,
    PingRequestSerializer,
    TCPCheckRequestSerializer
)
from apps.devices.models import Device, DeviceStatus
from apps.network_engine.icmp import ping_host
from apps.network_engine.tcp import check_tcp_port
from apps.accounts.permissions import IsOperatorRole, IsViewerRole
from apps.audit.utils import log_audit_event

class MonitoringCheckViewSet(viewsets.ModelViewSet):
    """
    Manage periodic monitoring checks for devices.
    """
    queryset = MonitoringCheck.objects.all().select_related('device')
    serializer_class = MonitoringCheckSerializer
    permission_classes = [IsViewerRole]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['device', 'check_type', 'is_active', 'last_status']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'run_check']:
            return [IsOperatorRole()]
        return [IsViewerRole()]

    @action(detail=True, methods=['post'], url_path='run')
    def run_check(self, request, pk=None):
        """
        Manually trigger an immediate check execution.
        """
        check = self.get_object()
        device = check.device

        if check.check_type == CheckType.ICMP_PING:
            result = ping_host(device.ip_address, timeout_sec=check.timeout_seconds, count=3)
            status_val = CheckStatus.SUCCESS if result.is_reachable else CheckStatus.FAILED
            check.last_status = status_val
            check.last_latency_ms = result.avg_latency_ms
            check.last_checked_at = timezone.now()
            check.save()

            if result.is_reachable:
                device.mark_online(result.avg_latency_ms)
            else:
                device.mark_offline()

            # Record log
            log = MonitoringLog.objects.create(
                monitoring_check=check,
                device=device,
                status=status_val,
                latency_ms=result.avg_latency_ms,
                packet_loss=result.packet_loss_percent,
                message=result.raw_output
            )
            return Response(MonitoringLogSerializer(log).data)

        elif check.check_type == CheckType.TCP_PORT:
            target_port = check.port or 80
            res = check_tcp_port(device.ip_address, target_port, timeout_sec=check.timeout_seconds)
            status_val = CheckStatus.SUCCESS if res.is_open else CheckStatus.FAILED
            check.last_status = status_val
            check.last_latency_ms = res.latency_ms
            check.last_checked_at = timezone.now()
            check.save()

            log = MonitoringLog.objects.create(
                monitoring_check=check,
                device=device,
                status=status_val,
                latency_ms=res.latency_ms,
                packet_loss=0.0 if res.is_open else 100.0,
                message=f"TCP Port {target_port}: {'OPEN' if res.is_open else 'CLOSED'} (Banner: {res.banner or 'None'})"
            )
            return Response(MonitoringLogSerializer(log).data)

        return Response({"detail": f"Check type {check.check_type} execution not implemented here."}, status=status.HTTP_400_BAD_REQUEST)


class DevicePingView(views.APIView):
    """
    On-demand ICMP ping check against a specific registered network device.
    POST /api/devices/{id}/ping/
    """
    permission_classes = [IsOperatorRole]

    def post(self, request, device_id):
        device = get_object_or_404(Device, id=device_id)
        serializer = PingRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        count = serializer.validated_data.get('count', 3)
        timeout = serializer.validated_data.get('timeout', 2)

        # Execute ping
        result = ping_host(device.ip_address, timeout_sec=timeout, count=count)

        # Update device health state
        if result.is_reachable:
            device.mark_online(result.avg_latency_ms)
        else:
            device.mark_offline()

        # Audit event
        log_audit_event(
            user=request.user,
            action='DEVICE_PING_EXECUTED',
            resource_type='Device',
            resource_id=str(device.id),
            ip_address=getattr(request, 'client_ip', '127.0.0.1'),
            details={
                'hostname': device.hostname,
                'ip': device.ip_address,
                'reachable': result.is_reachable,
                'avg_latency_ms': result.avg_latency_ms,
                'packet_loss': result.packet_loss_percent
            }
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


class DeviceTCPCheckView(views.APIView):
    """
    On-demand TCP Port diagnostic check against a network device.
    POST /api/devices/{id}/tcp-check/
    """
    permission_classes = [IsOperatorRole]

    def post(self, request, device_id):
        device = get_object_or_404(Device, id=device_id)
        serializer = TCPCheckRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        port = serializer.validated_data['port']
        timeout = serializer.validated_data.get('timeout', 3.0)

        result = check_tcp_port(device.ip_address, port, timeout_sec=timeout)

        log_audit_event(
            user=request.user,
            action='TCP_PORT_CHECK',
            resource_type='Device',
            resource_id=str(device.id),
            ip_address=getattr(request, 'client_ip', '127.0.0.1'),
            details={
                'hostname': device.hostname,
                'port': port,
                'is_open': result.is_open,
                'latency_ms': result.latency_ms
            }
        )

        return Response({
            'device_id': str(device.id),
            'hostname': device.hostname,
            'ip_address': device.ip_address,
            'port': port,
            'is_open': result.is_open,
            'latency_ms': result.latency_ms,
            'banner': result.banner,
            'error_message': result.error_message,
            'timestamp': result.timestamp
        })


class MonitoringLogListView(views.APIView):
    """
    Query historical monitoring check logs for a specific device.
    GET /api/devices/{id}/logs/
    """
    permission_classes = [IsViewerRole]

    def get(self, request, device_id):
        device = get_object_or_404(Device, id=device_id)
        logs = MonitoringLog.objects.filter(device=device).order_by('-timestamp')[:50]
        serializer = MonitoringLogSerializer(logs, many=True)
        return Response(serializer.data)
