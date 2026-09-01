"""
Incident and Alert Deduplication Engine
Prevents alert storms by correlating repetitive device failure events
into a single lifecycle-managed incident.
"""

from typing import Tuple, List
from django.utils import timezone
from django.db import transaction
from apps.devices.models import Device
from apps.alerts.models import Alert, AlertSeverity, AlertStatus, Incident, IncidentStatus


class IncidentDeduplicator:
    """
    Central operational incident deduplicator for monitoring tasks and Kafka event streams.
    """

    @classmethod
    def record_failure(
        cls,
        device: Device,
        title: str,
        message: str,
        severity: str = AlertSeverity.CRITICAL
    ) -> Tuple[Incident, bool]:
        """
        Records a failure for a device. If an active (OPEN or ACKNOWLEDGED) incident already exists,
        it increments the occurrence counter and appends to the timeline instead of flooding new alerts.
        """
        now = timezone.now()
        iso_now = now.isoformat()

        with transaction.atomic():
            # Check for existing active incident
            existing_incident = Incident.objects.filter(
                device=device,
                status__in=[IncidentStatus.OPEN, IncidentStatus.ACKNOWLEDGED]
            ).order_by('-last_seen_at').first()

            if existing_incident:
                existing_incident.occurrence_count += 1
                existing_incident.last_seen_at = now
                
                # Append timeline update
                timeline_entry = {
                    'timestamp': iso_now,
                    'event': 'RECURRING_FAILURE',
                    'message': f"Failure occurred again ({existing_incident.occurrence_count} total occurrences): {message}",
                    'severity': severity
                }
                timeline = list(existing_incident.timeline or [])
                timeline.append(timeline_entry)
                existing_incident.timeline = timeline
                
                existing_incident.save(update_fields=['occurrence_count', 'last_seen_at', 'timeline'])
                return existing_incident, False

            # Create new incident
            new_timeline = [{
                'timestamp': iso_now,
                'event': 'INCIDENT_CREATED',
                'message': f"Initial failure detected: {message}",
                'severity': severity
            }]

            incident = Incident.objects.create(
                device=device,
                title=title,
                description=message,
                severity=severity,
                status=IncidentStatus.OPEN,
                occurrence_count=1,
                first_seen_at=now,
                last_seen_at=now,
                timeline=new_timeline
            )

            # Create initial Alert linked to this incident creation
            Alert.objects.create(
                device=device,
                severity=severity,
                title=title,
                message=message,
                status=AlertStatus.OPEN,
                triggered_at=now
            )

            return incident, True

    @classmethod
    def record_recovery(
        cls,
        device: Device,
        resolution_note: str = "Device reachability restored and verified healthy."
    ) -> int:
        """
        Auto-resolves all active incidents and alerts for a device upon confirmed recovery.
        """
        now = timezone.now()
        iso_now = now.isoformat()
        resolved_count = 0

        with transaction.atomic():
            active_incidents = Incident.objects.filter(
                device=device,
                status__in=[IncidentStatus.OPEN, IncidentStatus.ACKNOWLEDGED]
            )

            for incident in active_incidents:
                incident.status = IncidentStatus.RESOLVED
                incident.resolved_at = now
                
                timeline = list(incident.timeline or [])
                timeline.append({
                    'timestamp': iso_now,
                    'event': 'INCIDENT_RESOLVED',
                    'message': resolution_note
                })
                incident.timeline = timeline
                incident.save(update_fields=['status', 'resolved_at', 'timeline'])
                resolved_count += 1

            # Resolve associated open alerts
            Alert.objects.filter(
                device=device,
                status__in=[AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED]
            ).update(
                status=AlertStatus.RESOLVED,
                resolved_at=now,
                notes=resolution_note
            )

        return resolved_count
