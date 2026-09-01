import pytest
from django.urls import reverse
from rest_framework import status
from apps.accounts.models import User, UserRole
from apps.devices.models import Device, DeviceType, DeviceVendor, DeviceStatus
from apps.audit.models import AuditLog

@pytest.mark.django_db
class TestApiIntegration:
    @pytest.fixture
    def auth_client(self, client):
        user = User.objects.create_user(email='noc@netwatch.io', password='NocPassword123!', role=UserRole.OPERATOR)
        resp = client.post(reverse('token_obtain_pair'), {'email': 'noc@netwatch.io', 'password': 'NocPassword123!'}, content_type='application/json')
        client.defaults['HTTP_AUTHORIZATION'] = f"Bearer {resp.data['access']}"
        return client

    def test_full_device_lifecycle_and_ping_flow(self, auth_client):
        # 1. Create Device
        create_resp = auth_client.post(reverse('device-list'), {
            'hostname': 'border-rtr-01.corp',
            'ip_address': '192.168.10.1',
            'device_type': DeviceType.ROUTER,
            'vendor': DeviceVendor.CISCO,
            'location': 'Corp Headquarter',
            'ssh_username': 'admin',
            'ssh_password': 'CiscoPassword!2026',
            'snmp_community': 'public'
        }, content_type='application/json')
        assert create_resp.status_code == status.HTTP_201_CREATED
        device_id = create_resp.data['id']

        # 2. Trigger on-demand ICMP ping check
        ping_url = reverse('device_ping', kwargs={'device_id': device_id})
        ping_resp = auth_client.post(ping_url, {'count': 3, 'timeout': 2}, content_type='application/json')
        assert ping_resp.status_code == status.HTTP_200_OK
        assert ping_resp.data['is_reachable'] is True
        assert ping_resp.data['status'] == DeviceStatus.ONLINE
        assert ping_resp.data['avg_latency_ms'] is not None

        # 3. Check health endpoint
        health_resp = auth_client.get(reverse('health_check'))
        assert health_resp.status_code == status.HTTP_200_OK
        assert health_resp.data['status'] == 'healthy'
        assert health_resp.data['components']['database']['status'] == 'healthy'

        # 4. Check dashboard stats
        stats_resp = auth_client.get(reverse('dashboard_stats'))
        assert stats_resp.status_code == status.HTTP_200_OK
        assert stats_resp.data['total_devices'] >= 1
        assert stats_resp.data['online_devices'] >= 1

        # 5. Verify Audit Trail entry was generated
        assert AuditLog.objects.filter(action='DEVICE_CREATED', resource_id=device_id).exists()
        assert AuditLog.objects.filter(action='DEVICE_PING_EXECUTED', resource_id=device_id).exists()
