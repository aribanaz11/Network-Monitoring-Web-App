import uuid
from django.db import models
from django.utils import timezone
from apps.devices.models import Device

class CheckType(models.TextChoices):
    ICMP_PING = 'ICMP_PING', 'ICMP Ping / Reachability'
    TCP_PORT = 'TCP_PORT', 'TCP Port Check'
    SNMP_POLL = 'SNMP_POLL', 'SNMP Telemetry Poll'
    SSH_HEALTH = 'SSH_HEALTH', 'SSH Health Check'

class CheckStatus(models.TextChoices):
    SUCCESS = 'SUCCESS', 'Check Succeeded'
    FAILED = 'FAILED', 'Check Failed'
    TIMEOUT = 'TIMEOUT', 'Check Timed Out'
    UNKNOWN = 'UNKNOWN', 'Not Yet Checked'

class MonitoringCheck(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='monitoring_checks')
    check_type = models.CharField(max_length=32, choices=CheckType.choices, default=CheckType.ICMP_PING)
    port = models.PositiveIntegerField(null=True, blank=True, help_text="Target port for TCP/SSH/SNMP checks")
    interval_seconds = models.PositiveIntegerField(default=30)
    timeout_seconds = models.PositiveIntegerField(default=5)
    is_active = models.BooleanField(default=True)
    
    last_status = models.CharField(max_length=16, choices=CheckStatus.choices, default=CheckStatus.UNKNOWN)
    last_latency_ms = models.FloatField(null=True, blank=True)
    last_checked_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'netwatch_monitoring_checks'
        unique_together = ('device', 'check_type', 'port')
        ordering = ['device__hostname', 'check_type']

    def __str__(self):
        return f"{self.device.hostname} - {self.check_type} ({self.last_status})"


class MonitoringLog(models.Model):
    """
    Relational historical snapshot of periodic monitoring check results.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    monitoring_check = models.ForeignKey(MonitoringCheck, on_delete=models.CASCADE, related_name='logs')
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='monitoring_logs')
    status = models.CharField(max_length=16, choices=CheckStatus.choices)
    latency_ms = models.FloatField(null=True, blank=True)
    packet_loss = models.FloatField(default=0.0)
    message = models.TextField(blank=True, default='')
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = 'netwatch_monitoring_logs'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['device', 'timestamp'], name='idx_monlog_dev_time'),
        ]
