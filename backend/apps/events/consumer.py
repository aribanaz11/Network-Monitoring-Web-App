"""
NetWatch Kafka Stream Consumer & Event Processor.
Handles event stream ingestion, anomaly detection, and consumer group processing.
"""
import json
import logging
import threading
import time
from typing import Dict, Any, List
from datetime import datetime, timezone
from django.conf import settings
from .schemas import EventTopic
from .kafka_bus import event_bus

logger = logging.getLogger('netwatch.events.consumer')

class EventStreamProcessor:
    """
    Stream Event Consumer & Real-time Analytics Processor.
    """
    def __init__(self, consumer_group: str = 'netwatch-telemetry-consumer-group'):
        self.consumer_group = consumer_group
        self.running = False
        self.processed_count = 0
        self.recent_processed_events: List[Dict[str, Any]] = []
        self.detected_anomalies: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

        # Register internal event listeners
        self._register_subscribers()

    def _register_subscribers(self):
        """Register topic handlers on the event bus"""
        event_bus.register_handler(EventTopic.DEVICE_STATUS, self.handle_device_status_event)
        event_bus.register_handler(EventTopic.ALERT_LIFECYCLE, self.handle_alert_event)
        event_bus.register_handler(EventTopic.TELEMETRY_SNMP, self.handle_telemetry_event)
        event_bus.register_handler(EventTopic.AUTOMATION_JOB, self.handle_automation_event)
        logger.info("EventStreamProcessor: Registered stream handlers for all NetWatch topics.")

    def handle_device_status_event(self, event: Dict[str, Any]):
        """Process device state transitions and detect cascading outages"""
        payload = event.get('payload', {})
        hostname = payload.get('hostname', 'unknown')
        old_status = payload.get('old_status')
        new_status = payload.get('new_status')

        with self._lock:
            self.processed_count += 1
            self.recent_processed_events.append({
                'processor': 'DeviceStatusStreamHandler',
                'topic': event.get('topic'),
                'key': event.get('key'),
                'summary': f"Device {hostname} transitioned from {old_status} -> {new_status}",
                'timestamp': event.get('timestamp')
            })
            if len(self.recent_processed_events) > 200:
                self.recent_processed_events.pop(0)

            # Anomaly check: Multiple OFFLINE transitions within short window
            if new_status == 'OFFLINE':
                offline_recent = [e for e in self.recent_processed_events[-10:] if '-> OFFLINE' in e.get('summary', '')]
                if len(offline_recent) >= 3:
                    anomaly = {
                        'type': 'CASCADING_OUTAGE_DETECTED',
                        'description': f"Rapid multi-device outage detected ({len(offline_recent)} nodes failed in succession). Potential core switch or power domain fault.",
                        'timestamp': datetime.now(timezone.utc).isoformat(),
                        'affected_nodes': [e['key'] for e in offline_recent]
                    }
                    self.detected_anomalies.append(anomaly)
                    if len(self.detected_anomalies) > 50:
                        self.detected_anomalies.pop(0)
                    logger.warning(f"STREAM ANOMALY DETECTED: {anomaly['description']}")

    def handle_alert_event(self, event: Dict[str, Any]):
        """Process incident events"""
        payload = event.get('payload', {})
        severity = payload.get('severity', 'INFO')
        with self._lock:
            self.processed_count += 1
            self.recent_processed_events.append({
                'processor': 'AlertStreamHandler',
                'topic': event.get('topic'),
                'key': event.get('key'),
                'summary': f"Alert [{severity}]: {payload.get('title', 'Incident event')}",
                'timestamp': event.get('timestamp')
            })
            if len(self.recent_processed_events) > 200:
                self.recent_processed_events.pop(0)

    def handle_telemetry_event(self, event: Dict[str, Any]):
        """Process SNMP telemetry stream"""
        payload = event.get('payload', {})
        cpu = payload.get('cpu', 0.0)
        memory = payload.get('memory', 0.0)
        hostname = payload.get('hostname', 'unknown')

        with self._lock:
            self.processed_count += 1
            # Telemetry anomaly: CPU spike > 90%
            if cpu >= 90.0:
                self.detected_anomalies.append({
                    'type': 'CRITICAL_CPU_SPIKE',
                    'description': f"Extreme CPU utilization ({cpu}%) observed on {hostname} via stream telemetry.",
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'hostname': hostname
                })

    def handle_automation_event(self, event: Dict[str, Any]):
        """Process automation completion stream"""
        with self._lock:
            self.processed_count += 1

    def get_consumer_status(self) -> Dict[str, Any]:
        """Return real-time stream consumer diagnostics"""
        with self._lock:
            return {
                'consumer_group': self.consumer_group,
                'status': 'HEALTHY',
                'total_events_processed': self.processed_count,
                'recent_activity_count': len(self.recent_processed_events),
                'active_anomalies_detected': len(self.detected_anomalies),
                'latest_anomalies': list(reversed(self.detected_anomalies))[:5],
                'latest_processed_events': list(reversed(self.recent_processed_events))[:10]
            }

# Global processor instance
stream_processor = EventStreamProcessor()
