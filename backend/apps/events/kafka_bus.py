import os
import json
import logging
from typing import Any, Optional
from datetime import datetime, timezone
from django.conf import settings


logger = logging.getLogger('netwatch.events.kafka')

class KafkaEventBus:
    """
    Enterprise Event Streaming Broker.
    Publishes domain events (device.status.changed, alert.triggered) to Kafka topics.
    Provides graceful fallback to in-memory event stream if Kafka broker is offline.
    """
    def __init__(self):
        self.bootstrap_servers = getattr(settings, 'KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
        self.enabled = getattr(settings, 'KAFKA_ENABLED', False)
        self.producer = None
        self._in_memory_event_log = []

        if self.enabled:
            self._init_kafka()

    def _init_kafka(self):
        try:
            from kafka import KafkaProducer
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: str(k).encode('utf-8') if k else None,
                request_timeout_ms=3000
            )
            logger.info("Connected to Kafka event streaming cluster.")
        except Exception as e:
            logger.warning(f"Kafka unavailable ({str(e)}). Event bus operating in local fallback mode.")

    def publish_event(self, topic: str, payload_or_key: Any, payload: Optional[dict] = None):
        """
        Publish structured event to stream. Supports publish_event(topic, payload) and publish_event(topic, key, payload).
        """
        if payload is not None:
            key = str(payload_or_key)
            actual_payload = payload
        else:
            key = 'netwatch'
            actual_payload = payload_or_key if isinstance(payload_or_key, dict) else {'data': payload_or_key}

        event_message = {
            'topic': topic,
            'key': key,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'payload': actual_payload
        }


        if self.producer is not None:
            try:
                self.producer.send(topic, key=key, value=event_message)
                return True
            except Exception as e:
                logger.error(f"Failed to publish event to Kafka ({topic}): {str(e)}")

        # Store in in-memory event log
        self._in_memory_event_log.append(event_message)
        if len(self._in_memory_event_log) > 500:
            self._in_memory_event_log.pop(0)
        logger.info(f"EVENT BUS [{topic}]: Key={key} Payload={json.dumps(payload)}")
        return True

    def get_recent_events(self, limit: int = 50):
        return list(reversed(self._in_memory_event_log))[:limit]

# Singleton instance
event_bus = KafkaEventBus()
