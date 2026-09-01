from rest_framework import serializers
from .models import AutomationJob, JobStatus, JobType
from apps.devices.models import Device

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
        user = self.context['request'].user if ('request' in self.context and self.context['request'].user.is_authenticated) else None
        validated_data['triggered_by'] = user
        job = AutomationJob.objects.create(**validated_data)
        job.target_devices.set(devices)
        return job
