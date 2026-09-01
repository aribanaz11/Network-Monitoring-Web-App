from rest_framework import viewsets, views, filters, status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from .models import Device, DeviceInterface, DeviceCredential
from .serializers import (
    DeviceSerializer,
    DeviceCreateUpdateSerializer,
    DeviceInterfaceSerializer,
    DeviceCredentialSerializer
)
from apps.network_engine.ssh import SSHAutomationEngine
from apps.network_engine.snmp import SNMPClientEngine
from apps.accounts.permissions import IsViewerRole, IsOperatorRole, IsAdminRole
from apps.audit.utils import log_audit_event

class DeviceViewSet(viewsets.ModelViewSet):
    """
    CRUD API ViewSet for Network Devices.
    - List/Retrieve: Accessible by Viewer, Operator, Admin
    - Create/Update: Accessible by Operator, Admin
    - Delete: Accessible by Admin only
    """
    queryset = Device.objects.all().prefetch_related('interfaces').select_related('credential')
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['device_type', 'vendor', 'status', 'snmp_version', 'location']
    search_fields = ['hostname', 'ip_address', 'model', 'location']
    ordering_fields = ['hostname', 'status', 'last_seen', 'last_latency_ms', 'created_at']
    ordering = ['hostname']

    def get_permissions(self):
        if self.action in ['destroy']:
            return [IsAdminRole()]
        elif self.action in ['create', 'update', 'partial_update']:
            return [IsOperatorRole()]
        return [IsViewerRole()]

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return DeviceCreateUpdateSerializer
        return DeviceSerializer

    def perform_create(self, serializer):
        device = serializer.save()
        log_audit_event(
            user=self.request.user,
            action='DEVICE_CREATED',
            resource_type='Device',
            resource_id=str(device.id),
            ip_address=getattr(self.request, 'client_ip', '127.0.0.1'),
            details={'hostname': device.hostname, 'ip_address': device.ip_address, 'type': device.device_type}
        )

    def perform_update(self, serializer):
        device = serializer.save()
        log_audit_event(
            user=self.request.user,
            action='DEVICE_UPDATED',
            resource_type='Device',
            resource_id=str(device.id),
            ip_address=getattr(self.request, 'client_ip', '127.0.0.1'),
            details={'hostname': device.hostname, 'status': device.status}
        )

    def perform_destroy(self, instance):
        device_id = str(instance.id)
        hostname = instance.hostname
        instance.delete()
        log_audit_event(
            user=self.request.user,
            action='DEVICE_DELETED',
            resource_type='Device',
            resource_id=device_id,
            ip_address=getattr(self.request, 'client_ip', '127.0.0.1'),
            details={'hostname': hostname}
        )


class DeviceSSHCommandView(views.APIView):
    """
    Execute whitelisted operational commands on network devices via SSH.
    POST /api/devices/{id}/ssh/
    """
    permission_classes = [IsOperatorRole]

    def post(self, request, device_id):
        device = get_object_or_404(Device, id=device_id)
        command = request.data.get('command', '').strip()
        timeout = int(request.data.get('timeout', 10))

        if not command:
            return Response({'detail': 'Command string is required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Execute command through validation engine
        result = SSHAutomationEngine.execute_command(device, command, timeout_sec=timeout)

        # Audit log the execution
        log_audit_event(
            user=request.user,
            action='SSH_COMMAND_EXECUTED',
            resource_type='Device',
            resource_id=str(device.id),
            ip_address=getattr(request, 'client_ip', '127.0.0.1'),
            details={
                'hostname': device.hostname,
                'command': command,
                'is_successful': result.is_successful,
                'exit_status': result.exit_status,
                'duration_ms': result.execution_duration_ms
            }
        )

        resp_status = status.HTTP_200_OK if result.is_successful else (
            status.HTTP_403_FORBIDDEN if result.exit_status == 403 else status.HTTP_400_BAD_REQUEST
        )

        return Response({
            'device_id': str(device.id),
            'hostname': device.hostname,
            'ip_address': device.ip_address,
            'command': result.command,
            'is_successful': result.is_successful,
            'exit_status': result.exit_status,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'execution_duration_ms': result.execution_duration_ms,
            'is_simulated': result.is_simulated,
            'timestamp': result.timestamp
        }, status=resp_status)


class DeviceSNMPPollView(views.APIView):
    """
    Poll live SNMP MIB metrics (v2c / v3) from a device.
    GET /api/devices/{id}/snmp/
    """
    permission_classes = [IsViewerRole]

    def get(self, request, device_id):
        device = get_object_or_404(Device, id=device_id)
        result = SNMPClientEngine.poll_device(device)

        log_audit_event(
            user=request.user,
            action='SNMP_METRICS_POLLED',
            resource_type='Device',
            resource_id=str(device.id),
            ip_address=getattr(request, 'client_ip', '127.0.0.1'),
            details={'hostname': device.hostname, 'snmp_version': device.snmp_version}
        )

        return Response({
            'device_id': result.device_id,
            'hostname': result.hostname,
            'ip_address': result.ip_address,
            'snmp_version': result.snmp_version,
            'is_successful': result.is_successful,
            'sys_descr': result.sys_descr,
            'sys_uptime_ticks': result.sys_uptime_ticks,
            'sys_uptime_formatted': result.sys_uptime_formatted,
            'cpu_utilization_percent': result.cpu_utilization_percent,
            'memory_utilization_percent': result.memory_utilization_percent,
            'interfaces': result.interfaces,
            'raw_oids': result.raw_oids,
            'is_simulated': result.is_simulated,
            'timestamp': result.timestamp
        })


class DeviceSNMPWalkView(views.APIView):
    """
    Execute SNMP Walk across a specified MIB OID subtree.
    POST /api/devices/{id}/snmp/walk/
    """
    permission_classes = [IsOperatorRole]

    def post(self, request, device_id):
        device = get_object_or_404(Device, id=device_id)
        root_oid = request.data.get('root_oid', '1.3.6.1.2.1.1').strip()
        result = SNMPClientEngine.walk_oid_subtree(device, root_oid=root_oid)
        return Response(result)


class DeviceInterfaceViewSet(viewsets.ModelViewSet):
    """
    CRUD API for Device Interfaces.
    """
    queryset = DeviceInterface.objects.all()
    serializer_class = DeviceInterfaceSerializer
    permission_classes = [IsOperatorRole]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['device', 'oper_status', 'admin_status']
