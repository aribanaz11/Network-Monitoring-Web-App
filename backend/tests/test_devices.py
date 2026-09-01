import pytest
from django.urls import reverse
from rest_framework import status
from apps.accounts.models import User, UserRole
from apps.devices.models import Device, DeviceCredential, DeviceType, DeviceVendor, DeviceStatus

@pytest.mark.django_db
class TestDeviceManagement:
    @pytest.fixture
    def operator_client(self, client):
        user = User.objects.create_user(email='op@netwatch.io', password='Pass123!Password', role=UserRole.OPERATOR)
        resp = client.post(reverse('token_obtain_pair'), {'email': 'op@netwatch.io', 'password': 'Pass123!Password'}, content_type='application/json')
        client.defaults['HTTP_AUTHORIZATION'] = f"Bearer {resp.data['access']}"
        return client

    def test_create_device_with_encrypted_credentials(self, operator_client):
        url = reverse('device-list')
        data = {
            'hostname': 'core-sw-test.lab',
            'ip_address': '192.168.100.5',
            'device_type': DeviceType.SWITCH,
            'vendor': DeviceVendor.CISCO,
            'model': 'Nexus 9300',
            'location': 'Lab Rack 1',
            'ssh_username': 'lab_admin',
            'ssh_password': 'SuperSecretPassword!2026',
            'snmp_community': 'private_lab'
        }
        response = operator_client.post(url, data, content_type='application/json')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['hostname'] == 'core-sw-test.lab'

        device = Device.objects.get(hostname='core-sw-test.lab')
        assert device.credential is not None
        assert device.credential.ssh_username == 'lab_admin'
        
        # Verify encryption: raw database column must not equal plaintext secret
        assert device.credential._encrypted_ssh_password != 'SuperSecretPassword!2026'
        # Decrypted method must recover the exact secret
        assert device.credential.get_ssh_password() == 'SuperSecretPassword!2026'
        assert device.credential.get_snmp_community() == 'private_lab'

    def test_list_devices_and_credential_masking(self, operator_client):
        device = Device.objects.create(
            hostname='rtr-edge.prod',
            ip_address='10.50.1.1',
            device_type=DeviceType.ROUTER,
            vendor=DeviceVendor.CISCO
        )
        cred = DeviceCredential.objects.create(device=device, ssh_username='sec_admin')
        cred.set_ssh_password('TopSecret!')
        cred.save()

        url = reverse('device-list')
        response = operator_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        results = response.data['results'] if 'results' in response.data else response.data
        assert len(results) >= 1
        
        item = [d for d in results if d['hostname'] == 'rtr-edge.prod'][0]
        # Sensitive credentials must never appear in cleartext
        assert 'TopSecret!' not in str(response.content)
        assert item['credential_summary']['has_ssh_password'] is True
        assert item['credential_summary']['ssh_username'] == 'sec_admin'
