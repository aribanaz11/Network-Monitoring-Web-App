from rest_framework import serializers, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from .models import Alert, AlertStatus, AlertSeverity, Incident, IncidentStatus
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


class IncidentSerializer(serializers.ModelSerializer):
    device_hostname = serializers.CharField(source='device.hostname', read_only=True)
    device_ip = serializers.CharField(source='device.ip_address', read_only=True)
    assigned_to_email = serializers.CharField(source='assigned_to.email', read_only=True, default=None)
    acknowledged_by_email = serializers.CharField(source='acknowledged_by.email', read_only=True, default=None)

    class Meta:
        model = Incident
        fields = [
            'id', 'device', 'device_hostname', 'device_ip', 'title', 'description',
            'severity', 'status', 'occurrence_count', 'first_seen_at', 'last_seen_at',
            'acknowledged_at', 'resolved_at', 'assigned_to_email', 'acknowledged_by_email', 'timeline'
        ]
        read_only_fields = [
            'id', 'occurrence_count', 'first_seen_at', 'last_seen_at',
            'acknowledged_at', 'resolved_at', 'timeline'
        ]


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


class IncidentViewSet(viewsets.ModelViewSet):
    """
    Deduplicated Incident Lifecycle API.
    """
    queryset = Incident.objects.all().select_related('device', 'assigned_to', 'acknowledged_by')
    serializer_class = IncidentSerializer
    permission_classes = [IsViewerRole]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['severity', 'status', 'device']

    def get_permissions(self):
        if self.action in ['acknowledge', 'resolve', 'create', 'update', 'destroy']:
            return [IsOperatorRole()]
        return [IsViewerRole()]

    @action(detail=True, methods=['post'])
    def acknowledge(self, request, pk=None):
        incident = self.get_object()
        incident.status = IncidentStatus.ACKNOWLEDGED
        incident.acknowledged_at = timezone.now()
        incident.acknowledged_by = request.user
        
        timeline = list(incident.timeline or [])
        timeline.append({
            'timestamp': timezone.now().isoformat(),
            'event': 'INCIDENT_ACKNOWLEDGED',
            'user': request.user.email
        })
        incident.timeline = timeline
        incident.save(update_fields=['status', 'acknowledged_at', 'acknowledged_by', 'timeline'])

        log_audit_event(
            user=request.user,
            action='INCIDENT_ACKNOWLEDGED',
            resource_type='Incident',
            resource_id=str(incident.id),
            details={'title': incident.title, 'device': incident.device.hostname}
        )
        return Response(IncidentSerializer(incident).data)

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        incident = self.get_object()
        notes = request.data.get('notes', 'Manual resolution by operator.')
        incident.status = IncidentStatus.RESOLVED
        incident.resolved_at = timezone.now()
        
        timeline = list(incident.timeline or [])
        timeline.append({
            'timestamp': timezone.now().isoformat(),
            'event': 'INCIDENT_RESOLVED',
            'user': request.user.email,
            'notes': notes
        })
        incident.timeline = timeline
        incident.save(update_fields=['status', 'resolved_at', 'timeline'])

        log_audit_event(
            user=request.user,
            action='INCIDENT_RESOLVED',
            resource_type='Incident',
            resource_id=str(incident.id),
            details={'title': incident.title, 'device': incident.device.hostname, 'notes': notes}
        )
        return Response(IncidentSerializer(incident).data)
