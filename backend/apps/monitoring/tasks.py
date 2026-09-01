import time
import logging
from celery import shared_task
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from apps.devices.models import Device, DeviceStatus
from apps.monitoring.models import MonitoringCheck, MonitoringLog, CheckType, CheckStatus
from apps.alerts.models import Alert, AlertSeverity, AlertStatus
from apps.network_engine.icmp import ping_host
from apps.network_engine.snmp import SNMPClientEngine
from apps.network_engine.circuit_breaker import CircuitBreaker
from apps.events.kafka_bus import event_bus
from apps.events.schemas import EventTopic
from apps.metrics.mongo_client import telemetry_client

logger = logging.getLogger('netwatch.tasks')

@shared_task(
    bind=True,
    name='apps.monitoring.tasks.poll_device_icmp_task',
    queue='high_priority_icmp',
    max_retries=3,
    default_retry_delay=5,
    autoretry_for=(),
    retry_backoff=True,
    retry_jitter=True
)
def poll_device_icmp_task(self, device_id: str):
    """
    Distributed Celery Task: Async ICMP reachability probe with Circuit Breaker and Auto-Incident lifecycle.
    """
    try:
        device = Device.objects.get(id=device_id)
    except Device.DoesNotExist:
        logger.error(f"Device {device_id} not found for ICMP polling.")
        return {'status': 'ERROR', 'reason': 'Device not found'}

    cb = CircuitBreaker.get(key=f"icmp:{device.ip_address}", failure_threshold=3, recovery_timeout_sec=30.0)

    # 1. Circuit Breaker Protection
    if not cb.can_execute():
        logger.warning(f"Short-circuiting ICMP poll for {device.hostname} ({device.ip_address}) - Circuit is OPEN.")
        return {
            'device_id': str(device.id),
            'hostname': device.hostname,
            'status': 'CIRCUIT_OPEN',
            'is_reachable': False,
            'skipped': True
        }

    # 2. Execute Probe
    result = ping_host(device.ip_address, timeout_sec=2, count=3)

    # 3. Update Circuit Breaker State
    if result.is_reachable:
        cb.record_success()
    else:
        cb.record_failure()

    # 4. State Machine & Transition
    from apps.monitoring.state_machine import DeviceStateMachine
    from apps.alerts.deduplication import IncidentDeduplicator

    old_status = device.status
    transition_result = DeviceStateMachine.apply_probe_result(
        device=device,
        is_reachable=result.is_reachable,
        latency_ms=result.avg_latency_ms,
        packet_loss_percent=result.packet_loss_percent,
        trigger='CELERY_ICMP_PROBE'
    )
    new_status = transition_result.new_status

    # 5. Persist Check Log & Deduplicated Incidents
    with transaction.atomic():
        check, _ = MonitoringCheck.objects.get_or_create(
            device=device,
            check_type=CheckType.ICMP_PING,
            defaults={'interval_seconds': 30}
        )
        MonitoringLog.objects.create(
            monitoring_check=check,
            device=device,
            status=CheckStatus.SUCCESS if result.is_reachable else CheckStatus.FAILED,
            latency_ms=result.avg_latency_ms,
            packet_loss=result.packet_loss_percent,
            message=result.raw_output
        )

        # 6. Deduplicated Incident Lifecycle
        if new_status in (DeviceStatus.DOWN, DeviceStatus.OFFLINE):
            incident, created = IncidentDeduplicator.record_failure(
                device=device,
                title=f"Node Outage: {device.hostname} ({device.ip_address})",
                message=f"Device unreachable. Consecutive failures: {transition_result.consecutive_failures}/{device.failure_threshold}.",
                severity=AlertSeverity.CRITICAL
            )
            event_bus.publish_event(
                topic=EventTopic.ALERT_LIFECYCLE,
                payload_or_key=str(device.id),
                payload={
                    'device_id': str(device.id),
                    'hostname': device.hostname,
                    'severity': 'CRITICAL',
                    'event': 'INCIDENT_CREATED' if created else 'INCIDENT_UPDATED',
                    'incident_id': str(incident.id),
                    'occurrences': incident.occurrence_count
                }
            )

        elif new_status in (DeviceStatus.UP, DeviceStatus.ONLINE) and old_status in (DeviceStatus.DOWN, DeviceStatus.RECOVERING, DeviceStatus.OFFLINE):
            resolved_count = IncidentDeduplicator.record_recovery(
                device=device,
                resolution_note=f"Auto-resolved: Node restored reachability with latency {result.avg_latency_ms}ms."
            )
            if resolved_count > 0:
                event_bus.publish_event(
                    topic=EventTopic.ALERT_LIFECYCLE,
                    payload_or_key=str(device.id),
                    payload={
                        'device_id': str(device.id),
                        'hostname': device.hostname,
                        'event': 'INCIDENTS_RESOLVED',
                        'resolved_count': resolved_count
                    }
                )

        # Emit state change event if changed
        if transition_result.transitioned:
            event_bus.publish_event(
                topic=EventTopic.DEVICE_STATUS,
                payload_or_key=str(device.id),
                payload={
                    'device_id': str(device.id),
                    'hostname': device.hostname,
                    'old_status': old_status,
                    'new_status': new_status,
                    'latency_ms': result.avg_latency_ms,
                    'reason': transition_result.reason
                }
            )


    return {
        'device_id': str(device.id),
        'hostname': device.hostname,
        'status': new_status,
        'latency_ms': result.avg_latency_ms,
        'loss_percent': result.packet_loss_percent,
        'is_simulated': result.is_simulated
    }


@shared_task(
    bind=True,
    name='apps.monitoring.tasks.poll_device_snmp_task',
    queue='snmp_telemetry',
    max_retries=2,
    default_retry_delay=10
)
def poll_device_snmp_task(self, device_id: str):
    """
    Distributed Celery Task: Async SNMP MIB polling with CPU/Memory threshold evaluation and MongoDB storage.
    """
    try:
        device = Device.objects.get(id=device_id)
    except Device.DoesNotExist:
        return {'status': 'ERROR', 'reason': 'Device not found'}

    # Execute SNMP poll
    res = SNMPClientEngine.poll_device(device)

    # Publish telemetry to streaming bus
    if res.is_successful:
        event_bus.publish_event(
            topic=EventTopic.TELEMETRY_SNMP,
            payload_or_key=str(device.id),
            payload={
                'device_id': str(device.id),
                'hostname': device.hostname,
                'cpu': res.cpu_utilization_percent,
                'memory': res.memory_utilization_percent,
                'uptime': res.sys_uptime_formatted,
                'interfaces_count': len(res.interfaces)
            }
        )

        if res.cpu_utilization_percent >= 85.0:
            Alert.objects.get_or_create(
                device=device,
                title=f"High CPU Load on {device.hostname} ({res.cpu_utilization_percent}%)",
                status=AlertStatus.OPEN,
                defaults={
                    'message': f"SNMP hrProcessorLoad exceeded threshold: {res.cpu_utilization_percent}%.",
                    'severity': AlertSeverity.WARNING
                }
            )


    return {
        'device_id': str(device.id),
        'hostname': device.hostname,
        'cpu': res.cpu_utilization_percent,
        'memory': res.memory_utilization_percent,
        'uptime': res.sys_uptime_formatted,
        'is_successful': res.is_successful
    }


@shared_task(name='apps.monitoring.tasks.run_periodic_fleet_polling_task', queue='default')
def run_periodic_fleet_polling_task():
    """
    Celery Beat Scheduled Coordinator:
    Runs every 30 seconds to fan out asynchronous polling tasks across the Celery worker fleet.
    """
    devices = list(Device.objects.all())
    logger.info(f"Celery Beat: Scheduling distributed polling tasks for {len(devices)} fleet devices...")

    dispatched_icmp = 0
    dispatched_snmp = 0

    for device in devices:
        if getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False):
            poll_device_icmp_task(str(device.id))
            poll_device_snmp_task(str(device.id))
        else:
            try:
                poll_device_icmp_task.apply_async(args=[str(device.id)], queue='high_priority_icmp')
            except Exception:
                poll_device_icmp_task(str(device.id))
            try:
                poll_device_snmp_task.apply_async(args=[str(device.id)], queue='snmp_telemetry')
            except Exception:
                poll_device_snmp_task(str(device.id))

        dispatched_icmp += 1
        dispatched_snmp += 1

    return {
        'scheduled_at': time.time(),
        'total_devices': len(devices),
        'icmp_tasks_dispatched': dispatched_icmp,
        'snmp_tasks_dispatched': dispatched_snmp
    }

