from rest_framework import viewsets, filters, status
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Device, DeviceInterface, DeviceCredential
from .serializers import (
    DeviceSerializer,
    DeviceCreateUpdateSerializer,
    DeviceInterfaceSerializer,
    DeviceCredentialSerializer
)
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
            ip_address=self.request.META.get('REMOTE_ADDR', '127.0.0.1'),
            details={'hostname': device.hostname, 'ip_address': device.ip_address, 'type': device.device_type}
        )

    def perform_update(self, serializer):
        device = serializer.save()
        log_audit_event(
            user=self.request.user,
            action='DEVICE_UPDATED',
            resource_type='Device',
            resource_id=str(device.id),
            ip_address=self.request.META.get('REMOTE_ADDR', '127.0.0.1'),
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
            ip_address=self.request.META.get('REMOTE_ADDR', '127.0.0.1'),
            details={'hostname': hostname}
        )


class DeviceInterfaceViewSet(viewsets.ModelViewSet):
    """
    CRUD API for Device Interfaces.
    """
    queryset = DeviceInterface.objects.all()
    serializer_class = DeviceInterfaceSerializer
    permission_classes = [IsOperatorRole]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['device', 'oper_status', 'admin_status']
