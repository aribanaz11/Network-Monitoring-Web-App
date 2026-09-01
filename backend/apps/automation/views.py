from rest_framework import serializers, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from .models import AutomationJob, JobStatus, JobType
from .serializers import AutomationJobSerializer
from apps.network_engine.ssh import SSHAutomationEngine
from apps.network_engine.icmp import ping_host
from apps.accounts.permissions import IsViewerRole, IsOperatorRole
from apps.audit.utils import log_audit_event
from apps.events.kafka_bus import event_bus
from apps.events.schemas import EventTopic



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
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'run_job']:
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

    @action(detail=True, methods=['post'], url_path='run')
    def run_job(self, request, pk=None):
        """
        Execute the automation job across all target devices.
        """
        job = self.get_object()
        job.status = JobStatus.RUNNING
        job.started_at = timezone.now()
        job.save(update_fields=['status', 'started_at'])

        targets = list(job.target_devices.all())
        results = {}
        success_count = 0
        failure_count = 0

        for device in targets:
            try:
                if job.job_type == JobType.CONFIG_BACKUP:
                    res = SSHAutomationEngine.execute_command(device, 'show running-config', timeout_sec=10)
                    results[device.hostname] = {
                        'device_id': str(device.id),
                        'ip': device.ip_address,
                        'status': 'SUCCESS' if res.is_successful else 'FAILED',
                        'config_length_bytes': len(res.stdout),
                        'preview': res.stdout[:200] + '...' if len(res.stdout) > 200 else res.stdout,
                        'duration_ms': res.execution_duration_ms
                    }
                    if res.is_successful: success_count += 1
                    else: failure_count += 1

                elif job.job_type == JobType.EXECUTE_COMMAND:
                    res = SSHAutomationEngine.execute_command(device, job.command or 'show version', timeout_sec=10)
                    results[device.hostname] = {
                        'device_id': str(device.id),
                        'ip': device.ip_address,
                        'status': 'SUCCESS' if res.is_successful else 'FAILED',
                        'stdout': res.stdout,
                        'stderr': res.stderr,
                        'duration_ms': res.execution_duration_ms
                    }
                    if res.is_successful: success_count += 1
                    else: failure_count += 1

                elif job.job_type == JobType.PING_SWEEP:
                    ping_res = ping_host(device.ip_address, timeout_sec=2, count=2)
                    results[device.hostname] = {
                        'device_id': str(device.id),
                        'ip': device.ip_address,
                        'status': 'ONLINE' if ping_res.is_reachable else 'OFFLINE',
                        'latency_ms': ping_res.avg_latency_ms,
                        'loss_percent': ping_res.packet_loss_percent
                    }
                    if ping_res.is_reachable: success_count += 1
                    else: failure_count += 1

            except Exception as e:
                results[device.hostname] = {'status': 'ERROR', 'error': str(e)}
                failure_count += 1

        job.status = JobStatus.SUCCESS if failure_count == 0 else (JobStatus.SUCCESS if success_count > 0 else JobStatus.FAILED)
        job.completed_at = timezone.now()
        job.result_summary = {
            'total_targets': len(targets),
            'success_count': success_count,
            'failure_count': failure_count,
            'device_results': results
        }
        job.save()

        # Emit to streaming bus
        event_bus.publish_event(
            topic=EventTopic.AUTOMATION_JOB,
            payload_or_key=str(job.id),
            payload={
                'job_id': str(job.id),
                'name': job.name,
                'job_type': job.job_type,
                'status': job.status,
                'total_targets': len(targets),
                'success_count': success_count,
                'failure_count': failure_count
            }
        )

        log_audit_event(
            user=request.user,
            action='AUTOMATION_JOB_EXECUTED',
            resource_type='AutomationJob',
            resource_id=str(job.id),
            details={'name': job.name, 'success_count': success_count, 'failure_count': failure_count}
        )

        return Response(AutomationJobSerializer(job).data)

