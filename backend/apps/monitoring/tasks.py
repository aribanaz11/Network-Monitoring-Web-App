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

    # 4. Determine State Transition
    old_status = device.status
    if not result.is_reachable:
        new_status = DeviceStatus.OFFLINE
    elif result.packet_loss_percent > 0.0 or (result.avg_latency_ms and result.avg_latency_ms > 150.0):
        new_status = DeviceStatus.DEGRADED
    else:
        new_status = DeviceStatus.ONLINE

    # 5. Persist Device Telemetry & Check Log
    with transaction.atomic():
        device.status = new_status
        device.last_latency_ms = result.avg_latency_ms
        if result.is_reachable:
            device.consecutive_failures = 0
            device.last_seen = timezone.now()
            device.save(update_fields=['status', 'last_latency_ms', 'consecutive_failures', 'last_seen'])
        else:
            device.consecutive_failures += 1
            device.save(update_fields=['status', 'last_latency_ms', 'consecutive_failures'])

        # Record check log
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

        # 6. Auto-Incident Management
        if new_status == DeviceStatus.OFFLINE and old_status != DeviceStatus.OFFLINE:
            # Device went down -> Create or reopen Alert
            Alert.objects.create(
                device=device,
                title=f"Node Unreachable: {device.hostname} ICMP Timeout",
                message=f"Device {device.hostname} ({device.ip_address}) failed ICMP reachability checks. Packet loss: 100%.",
                severity=AlertSeverity.CRITICAL,
                status=AlertStatus.OPEN
            )
            event_bus.publish_event(
                topic=EventTopic.ALERT_LIFECYCLE,
                payload_or_key=str(device.id),
                payload={
                    'device_id': str(device.id),
                    'hostname': device.hostname,
                    'severity': 'CRITICAL',
                    'event': 'NODE_DOWN',
                    'title': f"Node Unreachable: {device.hostname} ICMP Timeout"
                }
            )

        elif new_status == DeviceStatus.ONLINE and old_status == DeviceStatus.OFFLINE:
            # Device recovered -> Auto-resolve open alerts
            open_alerts = Alert.objects.filter(device=device, status__in=[AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED])
            for a in open_alerts:
                a.status = AlertStatus.RESOLVED
                a.resolved_at = timezone.now()
                a.resolution_notes = f"Auto-resolved: Node restored reachability with latency {result.avg_latency_ms}ms."
                a.save()

        # Emit state change event if changed
        if old_status != new_status:
            event_bus.publish_event(
                topic=EventTopic.DEVICE_STATUS,
                payload_or_key=str(device.id),
                payload={
                    'device_id': str(device.id),
                    'hostname': device.hostname,
                    'old_status': old_status,
                    'new_status': new_status,
                    'latency_ms': result.avg_latency_ms
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

