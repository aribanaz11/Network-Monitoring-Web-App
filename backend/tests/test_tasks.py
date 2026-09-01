import time
import pytest
from django.urls import reverse
from rest_framework import status
from apps.accounts.models import User, UserRole
from apps.devices.models import Device, DeviceType, DeviceVendor, DeviceStatus
from apps.monitoring.models import MonitoringLog
from apps.alerts.models import Alert, AlertStatus, AlertSeverity
from apps.network_engine.circuit_breaker import CircuitBreaker, CircuitState
from apps.monitoring.tasks import (
    poll_device_icmp_task,
    poll_device_snmp_task,
    run_periodic_fleet_polling_task
)

@pytest.mark.django_db
class TestCeleryDistributedTasks:
    @pytest.fixture
    def operator_client(self, client):
        user = User.objects.create_user(email='tasks_op@netwatch.io', password='Password123!', role=UserRole.OPERATOR)
        resp = client.post(reverse('token_obtain_pair'), {'email': 'tasks_op@netwatch.io', 'password': 'Password123!'}, content_type='application/json')
        client.defaults['HTTP_AUTHORIZATION'] = f"Bearer {resp.data['access']}"
        return client

    @pytest.fixture
    def active_router(self):
        return Device.objects.create(
            hostname='core-rtr-01.prod',
            ip_address='192.168.10.1',
            device_type=DeviceType.ROUTER,
            vendor=DeviceVendor.CISCO,
            status=DeviceStatus.UNKNOWN
        )

    def test_async_icmp_polling_task(self, active_router):
        res = poll_device_icmp_task(str(active_router.id))
        active_router.refresh_from_db()

        assert res['status'] == DeviceStatus.ONLINE
        assert active_router.status == DeviceStatus.ONLINE
        assert active_router.last_latency_ms is not None
        assert active_router.last_seen is not None

        # Verify MonitoringLog was recorded
        logs = MonitoringLog.objects.filter(monitoring_check__device=active_router)
        assert logs.count() >= 1
        assert logs.first().latency_ms == active_router.last_latency_ms


    def test_circuit_breaker_transitions(self):
        cb = CircuitBreaker(key="test:10.0.0.99", failure_threshold=3, recovery_timeout_sec=0.2)
        assert cb.state == CircuitState.CLOSED
        assert cb.can_execute() is True

        # 1st failure
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED
        assert cb.consecutive_failures == 1

        # 2nd failure
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED

        # 3rd failure -> Tripped OPEN
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb.can_execute() is False

        # Wait for recovery cooldown
        time.sleep(0.25)
        # Should transition to HALF_OPEN
        assert cb.can_execute() is True
        assert cb.state == CircuitState.HALF_OPEN

        # Success in HALF_OPEN resets to CLOSED
        cb.record_success()
        assert cb.state == CircuitState.CLOSED
        assert cb.consecutive_failures == 0

    def test_circuit_breaker_short_circuit_in_task(self):
        # Force breaker open for a test device
        test_ip = '192.168.99.99'
        cb = CircuitBreaker.get(key=f"icmp:{test_ip}", failure_threshold=1, recovery_timeout_sec=10.0)
        cb.state = CircuitState.OPEN
        cb.last_state_change = time.time()

        dev = Device.objects.create(
            hostname='unreachable-node.lab',
            ip_address=test_ip,
            device_type=DeviceType.SWITCH,
            vendor=DeviceVendor.CISCO
        )

        res = poll_device_icmp_task(str(dev.id))
        assert res['status'] == 'CIRCUIT_OPEN'
        assert res['skipped'] is True

    def test_async_snmp_polling_task(self, active_router):
        res = poll_device_snmp_task(str(active_router.id))
        assert res['is_successful'] is True
        assert res['cpu'] > 0.0
        assert res['memory'] > 0.0
        assert res['hostname'] == active_router.hostname

    def test_run_periodic_fleet_polling_task(self, active_router):
        summary = run_periodic_fleet_polling_task()
        assert summary['total_devices'] >= 1
        assert summary['icmp_tasks_dispatched'] >= 1
        assert summary['snmp_tasks_dispatched'] >= 1

    def test_fleet_poll_api_endpoint(self, operator_client, active_router):
        url = reverse('fleet_poll_now')
        resp = operator_client.post(url)
        assert resp.status_code == status.HTTP_202_ACCEPTED
        assert resp.data['status'] == 'DISPATCHED'
        assert resp.data['details']['total_devices'] >= 1

    def test_celery_worker_status_api(self, operator_client):
        url = reverse('celery_tasks_status')
        resp = operator_client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        assert 'worker_cluster' in resp.data
        assert 'high_priority_icmp' in resp.data['worker_cluster']['queues']
        assert 'circuit_breakers' in resp.data
