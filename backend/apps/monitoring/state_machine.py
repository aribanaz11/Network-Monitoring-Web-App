"""
NetWatch Device State Machine (Pure Domain Service)
Implements deterministic 5-state lifecycle transitions:
UNKNOWN -> UP -> DEGRADED -> DOWN -> RECOVERING -> UP
"""

from dataclasses import dataclass
from typing import Optional, Tuple
from apps.devices.models import Device, DeviceStatus, DeviceStateTransition

@dataclass
class StateTransitionResult:
    old_status: str
    new_status: str
    transitioned: bool
    consecutive_failures: int
    consecutive_successes: int
    reason: str


class DeviceStateMachine:
    """
    Pure state transition engine. Decoupled from I/O and views for 100% unit testability.
    """

    @staticmethod
    def calculate_transition(
        current_status: str,
        consecutive_failures: int,
        consecutive_successes: int,
        failure_threshold: int,
        recovery_threshold: int,
        is_reachable: bool,
        latency_ms: Optional[float] = None,
        packet_loss_percent: float = 0.0
    ) -> StateTransitionResult:
        old_status = current_status
        new_status = current_status
        reason = ""

        if is_reachable:
            new_failures = 0
            new_successes = consecutive_successes + 1

            if current_status in (DeviceStatus.DOWN, DeviceStatus.OFFLINE):
                new_status = DeviceStatus.RECOVERING
                reason = "Received successful probe after outage. Entered RECOVERING state."
            elif current_status == DeviceStatus.RECOVERING:
                if new_successes >= recovery_threshold:
                    new_status = DeviceStatus.UP
                    reason = f"Met recovery threshold ({new_successes}/{recovery_threshold} successful probes). Transitioned to UP."
                else:
                    new_status = DeviceStatus.RECOVERING
                    reason = f"Stabilizing in RECOVERING state ({new_successes}/{recovery_threshold} successful probes)."
            elif current_status == DeviceStatus.DEGRADED:
                if packet_loss_percent == 0.0 and (latency_ms is None or latency_ms <= 150.0):
                    new_status = DeviceStatus.UP
                    reason = "Metrics normalized (0% loss, low latency). Transitioned from DEGRADED to UP."
                else:
                    new_status = DeviceStatus.DEGRADED
                    reason = f"Remains DEGRADED (Loss: {packet_loss_percent}%, Latency: {latency_ms}ms)."
            else:  # UP, ONLINE, UNKNOWN
                if packet_loss_percent > 0.0 or (latency_ms is not None and latency_ms > 150.0):
                    new_status = DeviceStatus.DEGRADED
                    reason = f"High latency or packet loss detected (Loss: {packet_loss_percent}%, Latency: {latency_ms}ms)."
                else:
                    new_status = DeviceStatus.UP
                    reason = "Host is healthy and fully reachable."

        else:
            new_failures = consecutive_failures + 1
            new_successes = 0

            if new_failures >= failure_threshold:
                new_status = DeviceStatus.DOWN
                reason = f"Exceeded consecutive failure threshold ({new_failures}/{failure_threshold} failed probes). Transitioned to DOWN."
            elif current_status in (DeviceStatus.UP, DeviceStatus.ONLINE):
                new_status = DeviceStatus.DEGRADED
                reason = f"Probe failed ({new_failures}/{failure_threshold} failed probes). Marked DEGRADED before declaring DOWN."
            else:
                new_status = current_status
                reason = f"Probe failed ({new_failures}/{failure_threshold} failed probes)."

        transitioned = (old_status != new_status)

        return StateTransitionResult(
            old_status=old_status,
            new_status=new_status,
            transitioned=transitioned,
            consecutive_failures=new_failures,
            consecutive_successes=new_successes,
            reason=reason
        )

    @classmethod
    def apply_probe_result(
        cls,
        device: Device,
        is_reachable: bool,
        latency_ms: Optional[float] = None,
        packet_loss_percent: float = 0.0,
        trigger: str = 'ICMP_PROBE'
    ) -> StateTransitionResult:
        """
        Applies a probe result to a device model instance, persisting state and audit transitions.
        """
        result = cls.calculate_transition(
            current_status=device.status,
            consecutive_failures=device.consecutive_failures,
            consecutive_successes=device.consecutive_successes,
            failure_threshold=device.failure_threshold,
            recovery_threshold=device.recovery_threshold,
            is_reachable=is_reachable,
            latency_ms=latency_ms,
            packet_loss_percent=packet_loss_percent
        )

        device.status = result.new_status
        device.consecutive_failures = result.consecutive_failures
        device.consecutive_successes = result.consecutive_successes
        if latency_ms is not None:
            device.last_latency_ms = latency_ms

        from django.utils import timezone
        if is_reachable:
            device.last_seen = timezone.now()

        device.save(update_fields=[
            'status', 'consecutive_failures', 'consecutive_successes',
            'last_latency_ms', 'last_seen', 'updated_at'
        ])

        if result.transitioned:
            DeviceStateTransition.objects.create(
                device=device,
                from_status=result.old_status,
                to_status=result.new_status,
                trigger=trigger,
                reason=result.reason
            )

        return result
