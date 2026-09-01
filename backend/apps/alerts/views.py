from rest_framework import serializers, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Alert, AlertStatus, AlertSeverity
from apps.accounts.permissions import IsViewerRole, IsOperatorRole
from apps.audit.utils import log_audit_event

class AlertSerializer(serializers.ModelSerializer):
    device_hostname = serializers.CharField(source='device.hostname', read_only=True)
    device_ip = serializers.CharField(source='device.ip_address', read_only=True)
    acknowledged_by_email = serializers.CharField(source='acknowledged_by.email', read_only=True, default=None)

    class Meta:
        model = Alert
        fields = [
            'id', 'device', 'device_hostname', 'device_ip', 'severity', 'title', 'message',
            'status', 'triggered_at', 'acknowledged_at', 'resolved_at', 'acknowledged_by_email', 'notes'
        ]
        read_only_fields = ['id', 'triggered_at', 'acknowledged_at', 'resolved_at', 'acknowledged_by_email']

class AlertActionSerializer(serializers.Serializer):
    notes = serializers.CharField(required=False, allow_blank=True, default='')

class AlertViewSet(viewsets.ModelViewSet):
    """
    Alert management and incident resolution API.
    """
    queryset = Alert.objects.all().select_related('device', 'acknowledged_by')
    serializer_class = AlertSerializer
    permission_classes = [IsViewerRole]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['severity', 'status', 'device']

    def get_permissions(self):
        if self.action in ['acknowledge', 'resolve', 'create', 'update', 'destroy']:
            return [IsOperatorRole()]
        return [IsViewerRole()]

    @action(detail=True, methods=['post'])
    def acknowledge(self, request, pk=None):
        alert = self.get_object()
        alert.acknowledge(request.user)
        log_audit_event(
            user=request.user,
            action='ALERT_ACKNOWLEDGED',
            resource_type='Alert',
            resource_id=str(alert.id),
            details={'title': alert.title, 'device': alert.device.hostname}
        )
        return Response(AlertSerializer(alert).data)

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        alert = self.get_object()
        serializer = AlertActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        notes = serializer.validated_data.get('notes', '')
        alert.resolve(notes=notes)
        log_audit_event(
            user=request.user,
            action='ALERT_RESOLVED',
            resource_type='Alert',
            resource_id=str(alert.id),
            details={'title': alert.title, 'device': alert.device.hostname, 'notes': notes}
        )
        return Response(AlertSerializer(alert).data)
