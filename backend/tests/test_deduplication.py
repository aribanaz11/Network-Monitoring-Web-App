import pytest
from apps.devices.models import Device, DeviceType, DeviceVendor, DeviceStatus
from apps.alerts.models import Alert, AlertStatus, Incident, IncidentStatus
from apps.alerts.deduplication import IncidentDeduplicator

@pytest.mark.django_db
class TestIncidentDeduplication:
    """
    Test suite for Alert Storm Prevention and Deduplicated Incident Lifecycle.
    """

    @pytest.fixture
    def sample_device(self):
        return Device.objects.create(
            hostname="edge-switch-02",
            ip_address="10.0.0.5",
            device_type=DeviceType.SWITCH,
            vendor=DeviceVendor.CISCO,
            status=DeviceStatus.UP
        )

    def test_sustained_outage_deduplicates_into_single_incident(self, sample_device):
        """Scenario: 10 repeated failure events across 30 mins generate 1 Incident with occurrence_count=10."""
        # 1. First Failure -> Creates new Incident & Alert
        inc1, created1 = IncidentDeduplicator.record_failure(
            device=sample_device,
            title=f"Node Outage: {sample_device.hostname}",
            message="Host unreachable (100% loss)"
        )
        assert created1 is True
        assert inc1.occurrence_count == 1
        assert inc1.status == IncidentStatus.OPEN
        assert Incident.objects.filter(device=sample_device).count() == 1
        assert Alert.objects.filter(device=sample_device).count() == 1

        # 2. Subsequent 9 Failures -> Updates existing incident without creating duplicates
        for i in range(2, 11):
            inc, created = IncidentDeduplicator.record_failure(
                device=sample_device,
                title=f"Node Outage: {sample_device.hostname}",
                message=f"Consecutive failure #{i}"
            )
            assert created is False
            assert inc.id == inc1.id

        inc1.refresh_from_db()
        assert inc1.occurrence_count == 10
        assert len(inc1.timeline) == 10
        # Alert count should remain 1 (no storm)
        assert Alert.objects.filter(device=sample_device).count() == 1

    def test_auto_resolution_upon_device_recovery(self, sample_device):
        """Scenario: When device recovers, Incident and Alert are auto-resolved."""
        # Create incident
        inc, _ = IncidentDeduplicator.record_failure(
            device=sample_device,
            title=f"Node Outage: {sample_device.hostname}",
            message="Host unreachable"
        )
        assert inc.status == IncidentStatus.OPEN

        # Record recovery
        resolved_count = IncidentDeduplicator.record_recovery(
            device=sample_device,
            resolution_note="Ping restored, latency 12ms."
        )

        assert resolved_count == 1
        inc.refresh_from_db()
        assert inc.status == IncidentStatus.RESOLVED
        assert inc.resolved_at is not None
        assert any(e['event'] == 'INCIDENT_RESOLVED' for e in inc.timeline)

        # Alerts should also be resolved
        assert Alert.objects.filter(device=sample_device, status=AlertStatus.RESOLVED).exists()
