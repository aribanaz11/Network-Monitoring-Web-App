import pytest
from apps.devices.models import Device, DeviceStatus, DeviceType, DeviceVendor, DeviceStateTransition
from apps.monitoring.state_machine import DeviceStateMachine

@pytest.mark.django_db
class TestDeviceStateMachine:
    """
    Test suite for 5-state lifecycle transitions:
    UNKNOWN -> UP -> DEGRADED -> DOWN -> RECOVERING -> UP
    """

    @pytest.fixture
    def sample_device(self):
        return Device.objects.create(
            hostname="core-router-01",
            ip_address="192.168.1.1",
            device_type=DeviceType.ROUTER,
            vendor=DeviceVendor.CISCO,
            status=DeviceStatus.UNKNOWN,
            failure_threshold=3,
            recovery_threshold=2
        )

    def test_initial_successful_probe_transitions_to_up(self, sample_device):
        """Scenario: Unknown device becomes reachable -> transitions to UP."""
        result = DeviceStateMachine.apply_probe_result(
            device=sample_device,
            is_reachable=True,
            latency_ms=12.5,
            packet_loss_percent=0.0
        )

        sample_device.refresh_from_db()
        assert result.new_status == DeviceStatus.UP
        assert sample_device.status == DeviceStatus.UP
        assert sample_device.consecutive_failures == 0
        assert sample_device.consecutive_successes == 1
        assert DeviceStateTransition.objects.filter(device=sample_device, to_status=DeviceStatus.UP).exists()

    def test_high_latency_transitions_to_degraded(self, sample_device):
        """Scenario: Device with latency > 150ms transitions to DEGRADED."""
        sample_device.status = DeviceStatus.UP
        sample_device.save()

        result = DeviceStateMachine.apply_probe_result(
            device=sample_device,
            is_reachable=True,
            latency_ms=250.0,
            packet_loss_percent=0.0
        )

        assert result.new_status == DeviceStatus.DEGRADED
        assert result.transitioned is True

    def test_consecutive_failures_threshold_triggers_down(self, sample_device):
        """Scenario: Single failure causes DEGRADED, reaching failure_threshold (3) causes DOWN."""
        sample_device.status = DeviceStatus.UP
        sample_device.save()

        # Failure 1: Under threshold -> DEGRADED
        res1 = DeviceStateMachine.apply_probe_result(sample_device, is_reachable=False)
        assert res1.new_status == DeviceStatus.DEGRADED
        assert res1.consecutive_failures == 1

        # Failure 2: Under threshold -> DEGRADED
        res2 = DeviceStateMachine.apply_probe_result(sample_device, is_reachable=False)
        assert res2.new_status == DeviceStatus.DEGRADED
        assert res2.consecutive_failures == 2

        # Failure 3: Reached threshold (3) -> DOWN
        res3 = DeviceStateMachine.apply_probe_result(sample_device, is_reachable=False)
        assert res3.new_status == DeviceStatus.DOWN
        assert res3.consecutive_failures == 3

    def test_recovery_lifecycle_from_down_to_recovering_to_up(self, sample_device):
        """Scenario: DOWN -> (1 success) -> RECOVERING -> (2 successes = threshold) -> UP."""
        sample_device.status = DeviceStatus.DOWN
        sample_device.consecutive_failures = 3
        sample_device.consecutive_successes = 0
        sample_device.save()

        # Probe 1 Success: Transitions from DOWN to RECOVERING
        res1 = DeviceStateMachine.apply_probe_result(sample_device, is_reachable=True, latency_ms=15.0)
        assert res1.new_status == DeviceStatus.RECOVERING
        assert res1.consecutive_successes == 1

        # Probe 2 Success: Reaches recovery_threshold (2) -> Transitions to UP
        res2 = DeviceStateMachine.apply_probe_result(sample_device, is_reachable=True, latency_ms=14.2)
        assert res2.new_status == DeviceStatus.UP
        assert res2.consecutive_successes == 2
