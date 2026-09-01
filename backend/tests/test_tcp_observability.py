import pytest
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from apps.devices.models import Device, DeviceType, DeviceVendor
from apps.network_engine.tcp_checker import TCPService

User = get_user_model()

@pytest.mark.django_db
class TestTCPObservabilityAndErrors:
    """
    Test suite for TCP Port Checks, Health Probes, and RFC 7807 Error Standard.
    """

    @pytest.fixture
    def client(self):
        return APIClient()

    @pytest.fixture
    def operator_user(self):
        return User.objects.create_user(
            email="operator_test@netwatch.io",
            username="operator_test",
            password="StrongPassword123!",
            role="OPERATOR"
        )

    def test_tcp_service_port_scan(self):
        """Test TCPService single port check and multi-port scan."""
        res = TCPService.check_port("127.0.0.1", port=65534, timeout_sec=0.1)
        assert res.port == 65534
        assert res.is_open is False

        scan = TCPService.scan_device_ports("127.0.0.1", ports=[65533, 65534], timeout_sec=0.1)
        assert scan.ports_scanned == 2
        assert scan.ports_closed == 2

    def test_liveness_probe_endpoint(self, client):
        """GET /api/health/live/ returns 200 OK fast."""
        response = client.get('/api/health/live/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'alive'

    def test_readiness_probe_endpoint(self, client):
        """GET /api/health/ready/ verifies database and dependencies."""
        response = client.get('/api/health/ready/')
        assert response.status_code == status.HTTP_200_OK
        assert 'dependencies' in response.data
        assert 'relational_db' in response.data['dependencies']
        assert response.data['dependencies']['relational_db']['status'] == 'HEALTHY'

    def test_rfc_7807_error_formatting(self, client):
        """Test unauthenticated access returns RFC 7807 Problem Details structure."""
        response = client.get('/api/devices/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert 'type' in response.data
        assert 'title' in response.data
        assert 'status' in response.data
        assert 'detail' in response.data
        assert 'instance' in response.data
        assert response.data['status'] == 401
