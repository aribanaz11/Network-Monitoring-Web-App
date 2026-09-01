import uuid
from django.db import models
from django.utils import timezone
from django.conf import settings
from apps.devices.models import Device

class JobType(models.TextChoices):
    CONFIG_BACKUP = 'CONFIG_BACKUP', 'Configuration Backup'
    EXECUTE_COMMAND = 'EXECUTE_COMMAND', 'Execute Whitelisted CLI Command'
    PING_SWEEP = 'PING_SWEEP', 'Subnet / Group Reachability Sweep'
    INTERFACE_BOUNCE = 'INTERFACE_BOUNCE', 'Interface State Restart'

class JobStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending in Queue'
    RUNNING = 'RUNNING', 'Running Execution'
    SUCCESS = 'SUCCESS', 'Completed Successfully'
    FAILED = 'FAILED', 'Execution Failed'

class AutomationJob(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=128)
    job_type = models.CharField(max_length=32, choices=JobType.choices, default=JobType.EXECUTE_COMMAND)
    status = models.CharField(max_length=16, choices=JobStatus.choices, default=JobStatus.PENDING, db_index=True)
    
    target_devices = models.ManyToManyField(Device, related_name='automation_jobs')
    command = models.TextField(blank=True, default='', help_text="Command string if job_type is EXECUTE_COMMAND")
    result_summary = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True, default='')
    
    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='triggered_jobs'
    )
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'netwatch_automation_jobs'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.job_type}) - {self.status}"
