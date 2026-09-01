import uuid
from django.db import models
from django.utils import timezone
from django.conf import settings
from apps.devices.models import Device

class AlertSeverity(models.TextChoices):
    CRITICAL = 'CRITICAL', 'Critical (Service Down)'
    WARNING = 'WARNING', 'Warning (Degraded / High Threshold)'
    INFO = 'INFO', 'Informational'

class AlertStatus(models.TextChoices):
    OPEN = 'OPEN', 'Open'
    ACKNOWLEDGED = 'ACKNOWLEDGED', 'Acknowledged'
    RESOLVED = 'RESOLVED', 'Resolved'

class Alert(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='alerts')
    severity = models.CharField(max_length=16, choices=AlertSeverity.choices, default=AlertSeverity.CRITICAL, db_index=True)
    title = models.CharField(max_length=255)
    message = models.TextField()
    status = models.CharField(max_length=16, choices=AlertStatus.choices, default=AlertStatus.OPEN, db_index=True)
    
    triggered_at = models.DateTimeField(default=timezone.now, db_index=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    acknowledged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='acknowledged_alerts'
    )
    notes = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'netwatch_alerts'
        ordering = ['-triggered_at']
        indexes = [
            models.Index(fields=['status', 'severity', 'triggered_at'], name='idx_alert_stat_sev_time'),
            models.Index(fields=['device', 'status'], name='idx_alert_device_stat'),
        ]

    def __str__(self):
        return f"[{self.severity}] {self.device.hostname} - {self.title} ({self.status})"

    def acknowledge(self, user):
        self.status = AlertStatus.ACKNOWLEDGED
        self.acknowledged_at = timezone.now()
        self.acknowledged_by = user
        self.save(update_fields=['status', 'acknowledged_at', 'acknowledged_by'])

    def resolve(self, notes=''):
        self.status = AlertStatus.RESOLVED
        self.resolved_at = timezone.now()
        if notes:
            self.notes = f"{self.notes}\nResolved: {notes}".strip()
        self.save(update_fields=['status', 'resolved_at', 'notes'])


class IncidentStatus(models.TextChoices):
    OPEN = 'OPEN', 'Open'
    ACKNOWLEDGED = 'ACKNOWLEDGED', 'Acknowledged'
    RESOLVED = 'RESOLVED', 'Resolved'
    CLOSED = 'CLOSED', 'Closed'


class Incident(models.Model):
    """
    Deduplicated Operational Incident entity.
    Aggregates recurring failures for a device into a single lifecycle record to prevent alert storms.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='incidents')
    title = models.CharField(max_length=255)
    description = models.TextField()
    severity = models.CharField(
        max_length=16,
        choices=AlertSeverity.choices,
        default=AlertSeverity.CRITICAL,
        db_index=True
    )
    status = models.CharField(
        max_length=16,
        choices=IncidentStatus.choices,
        default=IncidentStatus.OPEN,
        db_index=True
    )
    occurrence_count = models.PositiveIntegerField(
        default=1,
        help_text="Number of deduplicated failure occurrences during this active outage window"
    )
    first_seen_at = models.DateTimeField(default=timezone.now, db_index=True)
    last_seen_at = models.DateTimeField(default=timezone.now, db_index=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_incidents'
    )
    acknowledged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='acknowledged_incidents'
    )
    timeline = models.JSONField(
        default=list,
        blank=True,
        help_text="Chronological event log of transitions, acknowledgments, and probe attempts"
    )

    class Meta:
        db_table = 'netwatch_incidents'
        ordering = ['-last_seen_at']
        indexes = [
            models.Index(fields=['device', 'status'], name='idx_inc_dev_status'),
            models.Index(fields=['status', 'severity', 'last_seen_at'], name='idx_inc_stat_sev_time'),
        ]

    def __str__(self):
        return f"INC-{str(self.id)[:8]}: [{self.severity}] {self.device.hostname} - {self.status} ({self.occurrence_count} occurrences)"
