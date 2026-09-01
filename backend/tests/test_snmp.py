import pytest
from django.urls import reverse
from rest_framework import status
from apps.accounts.models import User, UserRole
from apps.devices.models import Device, DeviceType, DeviceVendor, SNMPVersion
from apps.network_engine.snmp import SNMPClientEngine
from apps.metrics.mongo_client import telemetry_client

@pytest.mark.django_db
class TestSNMPMonitoring:
    @pytest.fixture
    def operator_client(self, client):
        user = User.objects.create_user(email='snmp_op@netwatch.io', password='Password123!', role=UserRole.OPERATOR)
        resp = client.post(reverse('token_obtain_pair'), {'email': 'snmp_op@netwatch.io', 'password': 'Password123!'}, content_type='application/json')
        client.defaults['HTTP_AUTHORIZATION'] = f"Bearer {resp.data['access']}"
        return client

    @pytest.fixture
    def test_switch(self):
        return Device.objects.create(
            hostname='dist-sw-test.lab',
            ip_address='192.168.10.2',
            device_type=DeviceType.SWITCH,
            vendor=DeviceVendor.CISCO,
            snmp_version=SNMPVersion.V2C
        )

    def test_snmp_poll_metrics_and_mongo_insertion(self, test_switch):
        result = SNMPClientEngine.poll_device(test_switch)
        assert result.is_successful is True
        assert result.hostname == 'dist-sw-test.lab'
        assert result.cpu_utilization_percent > 0.0
        assert result.memory_utilization_percent > 0.0
        assert len(result.interfaces) >= 1
        assert 'GigabitEthernet0/1' in result.interfaces[0]['name']

        # Verify telemetry buffer / MongoDB received documents
        metrics = telemetry_client.get_device_metrics(device_id=str(test_switch.id), limit=10)
        assert len(metrics) >= 2
        types = [m['metric_type'] for m in metrics]
        assert 'cpu_utilization' in types
        assert 'memory_utilization' in types

    def test_snmp_api_endpoint(self, operator_client, test_switch):
        url = reverse('device_snmp', kwargs={'device_id': test_switch.id})
        resp = operator_client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['hostname'] == 'dist-sw-test.lab'
        assert resp.data['cpu_utilization_percent'] > 0
        assert 'sys_uptime_formatted' in resp.data

    def test_snmp_walk_api_endpoint(self, operator_client, test_switch):
        url = reverse('device_snmp_walk', kwargs={'device_id': test_switch.id})
        resp = operator_client.post(url, {'root_oid': '1.3.6.1.2.1.1'}, content_type='application/json')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['root_oid'] == '1.3.6.1.2.1.1'
        assert resp.data['entries_count'] >= 1
        assert len(resp.data['oids']) >= 1
