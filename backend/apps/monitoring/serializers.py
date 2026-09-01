from rest_framework import serializers
from .models import MonitoringCheck, MonitoringLog

class MonitoringCheckSerializer(serializers.ModelSerializer):
    device_hostname = serializers.CharField(source='device.hostname', read_only=True)
    device_ip = serializers.CharField(source='device.ip_address', read_only=True)

    class Meta:
        model = MonitoringCheck
        fields = [
            'id', 'device', 'device_hostname', 'device_ip', 'check_type', 'port',
            'interval_seconds', 'timeout_seconds', 'is_active', 'last_status',
            'last_latency_ms', 'last_checked_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'last_status', 'last_latency_ms', 'last_checked_at', 'created_at', 'updated_at']

class MonitoringLogSerializer(serializers.ModelSerializer):
    device_hostname = serializers.CharField(source='device.hostname', read_only=True)

    class Meta:
        model = MonitoringLog
        fields = ['id', 'monitoring_check', 'device', 'device_hostname', 'status', 'latency_ms', 'packet_loss', 'message', 'timestamp']
        read_only_fields = fields

class PingRequestSerializer(serializers.Serializer):
    count = serializers.IntegerField(min_value=1, max_value=10, default=3, required=False)
    timeout = serializers.IntegerField(min_value=1, max_value=10, default=2, required=False)

class TCPCheckRequestSerializer(serializers.Serializer):
    port = serializers.IntegerField(min_value=1, max_value=65535, required=True)
    timeout = serializers.FloatField(min_value=0.5, max_value=10.0, default=3.0, required=False)
