import os
import json
import logging
from typing import Any, Optional, Dict, List, Callable
from datetime import datetime, timezone
from collections import defaultdict
from django.conf import settings
from .schemas import EventTopic, StreamEvent

logger = logging.getLogger('netwatch.events.kafka')

class KafkaEventBus:
    """
    Enterprise Distributed Event Streaming Bus.
    - Publishes structured domain events to Kafka topics (device status, telemetry, alerts, automation).
    - Supports Consumer Group subscriptions and event handler callbacks.
    - Provides high-performance in-memory ring buffer (up to 1,000 recent events) for immediate
      dashboard streaming, search filtering, and graceful fallback when broker is disconnected.
    - Tracks real-time streaming metrics (event rates, topic distribution, throughput).
    """
    def __init__(self):
        self.bootstrap_servers = getattr(settings, 'KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
        self.enabled = getattr(settings, 'KAFKA_ENABLED', False)
        self.producer = None
        self._in_memory_event_log: List[Dict[str, Any]] = []
        self._handlers: Dict[str, List[Callable]] = defaultdict(list)
        self._stats: Dict[str, int] = defaultdict(int)
        self._start_time = datetime.now(timezone.utc)
        self._max_buffer_size = 1000

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
            logger.info(f"Connected to Kafka event streaming cluster at {self.bootstrap_servers}")
        except Exception as e:
            logger.warning(f"Kafka cluster unavailable at {self.bootstrap_servers} ({str(e)}). Operating in resilient local stream fallback mode.")

    def publish_event(self, topic: str, payload_or_key: Any, payload: Optional[dict] = None) -> Dict[str, Any]:
        """
        Publish a structured domain event to the streaming bus.
        Supports both signatures:
          - publish_event(topic, payload)
          - publish_event(topic, key, payload)
        """
        if payload is not None:
            key = str(payload_or_key)
            actual_payload = payload
        else:
            key = 'netwatch-core'
            actual_payload = payload_or_key if isinstance(payload_or_key, dict) else {'data': payload_or_key}

        now_iso = datetime.now(timezone.utc).isoformat()
        event_message = {
            'topic': topic,
            'key': key,
            'timestamp': now_iso,
            'payload': actual_payload,
            'partition': 0,
            'offset': self._stats['total_events']
        }

        # 1. Update Ingestion Metrics
        self._stats['total_events'] += 1
        self._stats[f"topic:{topic}"] += 1

        # 2. Publish to Kafka if connected
        if self.producer is not None:
            try:
                self.producer.send(topic, key=key, value=event_message)
            except Exception as e:
                logger.error(f"Failed to publish event to Kafka topic [{topic}]: {str(e)}")

        # 3. In-Memory Ring Buffer Retention
        self._in_memory_event_log.append(event_message)
        if len(self._in_memory_event_log) > self._max_buffer_size:
            self._in_memory_event_log.pop(0)

        logger.info(f"STREAM EVENT [{topic}]: Key={key} (Offset: {event_message['offset']})")

        # 4. Dispatch to registered in-process topic listeners / consumers
        self._dispatch_to_handlers(topic, event_message)

        return event_message

    def register_handler(self, topic: str, handler: Callable):
        """
        Register a subscriber callback for a specific event topic or wildcard '*'.
        """
        self._handlers[topic].append(handler)
        logger.debug(f"Registered event consumer handler for topic [{topic}]")

    def _dispatch_to_handlers(self, topic: str, event: Dict[str, Any]):
        """
        Invoke all registered subscribers for topic and wildcard subscriptions.
        """
        # Exact topic handlers
        for handler in self._handlers.get(topic, []):
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Error in stream event handler for [{topic}]: {str(e)}")

        # Wildcard handlers
        for handler in self._handlers.get('*', []):
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Error in wildcard stream event handler: {str(e)}")

    def get_recent_events(self, topic: Optional[str] = None, key: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Retrieve filtered recent streaming events from the memory buffer.
        """
        events = list(reversed(self._in_memory_event_log))
        if topic:
            events = [e for e in events if e['topic'] == topic or topic in e['topic']]
        if key:
            events = [e for e in events if e['key'] == key]
        return events[:limit]

    def get_stream_stats(self) -> Dict[str, Any]:
        """
        Calculates streaming throughput metrics.
        """
        uptime_sec = max(1, (datetime.now(timezone.utc) - self._start_time).total_seconds())
        total_events = self._stats['total_events']
        
        topic_breakdown = {}
        for k, v in self._stats.items():
            if k.startswith('topic:'):
                topic_name = k.replace('topic:', '')
                topic_breakdown[topic_name] = v

        return {
            'broker_status': 'CONNECTED' if self.producer is not None else 'LOCAL_FALLBACK_STREAM',
            'bootstrap_servers': self.bootstrap_servers,
            'is_kafka_enabled': self.enabled,
            'total_events_published': total_events,
            'throughput_eps': round(total_events / uptime_sec, 2),
            'buffered_events_count': len(self._in_memory_event_log),
            'topic_distribution': topic_breakdown,
            'active_subscribers': sum(len(h) for h in self._handlers.values()),
            'uptime_seconds': round(uptime_sec, 1)
        }

    def clear_buffer(self):
        """Reset stream log (useful for testing)"""
        self._in_memory_event_log.clear()
        self._stats.clear()

# Global Singleton Event Bus
event_bus = KafkaEventBus()
