import pytest
from django.urls import reverse
from rest_framework import status
from apps.accounts.models import User, UserRole
from apps.devices.models import Device, DeviceType, DeviceVendor
from apps.automation.models import AutomationJob, JobType, JobStatus

@pytest.mark.django_db
class TestAutomationJobs:
    @pytest.fixture
    def operator_client(self, client):
        user = User.objects.create_user(email='auto_op@netwatch.io', password='Password123!', role=UserRole.OPERATOR)
        resp = client.post(reverse('token_obtain_pair'), {'email': 'auto_op@netwatch.io', 'password': 'Password123!'}, content_type='application/json')
        client.defaults['HTTP_AUTHORIZATION'] = f"Bearer {resp.data['access']}"
        return client

    @pytest.fixture
    def devices_cluster(self):
        d1 = Device.objects.create(hostname='rtr-01.test', ip_address='192.168.10.1', device_type=DeviceType.ROUTER, vendor=DeviceVendor.CISCO)
        d2 = Device.objects.create(hostname='sw-01.test', ip_address='192.168.10.2', device_type=DeviceType.SWITCH, vendor=DeviceVendor.CISCO)
        return [d1, d2]

    def test_create_and_run_config_backup_job(self, operator_client, devices_cluster):
        # 1. Create Job
        create_url = reverse('automation-job-list')
        data = {
            'name': 'Test Cluster Config Backup',
            'job_type': JobType.CONFIG_BACKUP,
            'target_device_ids': [str(d.id) for d in devices_cluster]
        }
        create_resp = operator_client.post(create_url, data, content_type='application/json')
        assert create_resp.status_code == status.HTTP_201_CREATED
        job_id = create_resp.data['id']
        assert create_resp.data['target_device_count'] == 2

        # 2. Run Job
        run_url = reverse('automation-job-run-job', kwargs={'pk': job_id})
        run_resp = operator_client.post(run_url)
        assert run_resp.status_code == status.HTTP_200_OK
        assert run_resp.data['status'] == JobStatus.SUCCESS
        assert run_resp.data['result_summary']['total_targets'] == 2
        assert run_resp.data['result_summary']['success_count'] == 2
        assert 'rtr-01.test' in run_resp.data['result_summary']['device_results']
        assert 'sw-01.test' in run_resp.data['result_summary']['device_results']
