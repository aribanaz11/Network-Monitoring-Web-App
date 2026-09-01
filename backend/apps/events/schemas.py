"""
NetWatch Kafka Event Topic Definitions and Schema Validators.
"""
from dataclasses import dataclass
from typing import Dict, Any, Optional

class EventTopic:
    DEVICE_STATUS = 'netwatch.device.status'
    ALERT_LIFECYCLE = 'netwatch.alert.lifecycle'
    TELEMETRY_SNMP = 'netwatch.telemetry.snmp'
    AUTOMATION_JOB = 'netwatch.automation.jobs'
    SECURITY_AUDIT = 'netwatch.security.audit'

    ALL_TOPICS = [
        DEVICE_STATUS,
        ALERT_LIFECYCLE,
        TELEMETRY_SNMP,
        AUTOMATION_JOB,
        SECURITY_AUDIT,
    ]


@dataclass
class StreamEvent:
    topic: str
    key: str
    payload: Dict[str, Any]
    timestamp: str
    partition: Optional[int] = 0
    offset: Optional[int] = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'topic': self.topic,
            'key': self.key,
            'timestamp': self.timestamp,
            'payload': self.payload,
            'partition': self.partition,
            'offset': self.offset
        }
