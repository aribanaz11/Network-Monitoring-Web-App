from rest_framework import serializers, viewsets, status
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import AutomationJob, JobStatus, JobType
from apps.devices.models import Device
from apps.accounts.permissions import IsViewerRole, IsOperatorRole
from apps.audit.utils import log_audit_event

class AutomationJobSerializer(serializers.ModelSerializer):
    triggered_by_email = serializers.CharField(source='triggered_by.email', read_only=True, default='Automated / Scheduled')
    target_device_count = serializers.IntegerField(source='target_devices.count', read_only=True)
    target_device_ids = serializers.PrimaryKeyRelatedField(
        queryset=Device.objects.all(),
        many=True,
        source='target_devices',
        write_only=True
    )

    class Meta:
        model = AutomationJob
        fields = [
            'id', 'name', 'job_type', 'status', 'target_device_ids', 'target_device_count',
            'command', 'result_summary', 'error_message', 'triggered_by_email',
            'created_at', 'started_at', 'completed_at'
        ]
        read_only_fields = ['id', 'status', 'result_summary', 'error_message', 'created_at', 'started_at', 'completed_at']

    def create(self, validated_data):
        devices = validated_data.pop('target_devices', [])
        validated_data['triggered_by'] = self.context['request'].user
        job = AutomationJob.objects.create(**validated_data)
        job.target_devices.set(devices)
        return job

class AutomationJobViewSet(viewsets.ModelViewSet):
    """
    CRUD and execution trigger for network automation jobs.
    """
    queryset = AutomationJob.objects.all().prefetch_related('target_devices')
    serializer_class = AutomationJobSerializer
    permission_classes = [IsViewerRole]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['job_type', 'status']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsOperatorRole()]
        return [IsViewerRole()]

    def perform_create(self, serializer):
        job = serializer.save()
        log_audit_event(
            user=self.request.user,
            action='AUTOMATION_JOB_CREATED',
            resource_type='AutomationJob',
            resource_id=str(job.id),
            details={'name': job.name, 'job_type': job.job_type}
        )
