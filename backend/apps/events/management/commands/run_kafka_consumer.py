import time
import json
import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from apps.events.schemas import EventTopic
from apps.events.consumer import stream_processor

logger = logging.getLogger('netwatch.events.consumer')

class Command(BaseCommand):
    help = 'Starts the NetWatch Kafka Event Consumer daemon to process streaming telemetry and alerts.'

    def add_arguments(self, parser):
        parser.add_argument('--group', type=str, default='netwatch-consumer-group', help='Kafka Consumer Group ID')
        parser.add_argument('--topics', nargs='+', default=EventTopic.ALL_TOPICS, help='List of Kafka topics to subscribe to')

    def handle(self, *args, **options):
        group = options['group']
        topics = options['topics']
        self.stdout.write(self.style.SUCCESS(f"Starting NetWatch Kafka Consumer Daemon (Group: {group})..."))
        self.stdout.write(f"Subscribed Topics: {', '.join(topics)}")

        try:
            from kafka import KafkaConsumer
            bootstrap = getattr(settings, 'KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
            consumer = KafkaConsumer(
                *topics,
                bootstrap_servers=bootstrap,
                group_id=group,
                auto_offset_reset='latest',
                value_deserializer=lambda m: json.loads(m.decode('utf-8'))
            )
            self.stdout.write(self.style.SUCCESS(f"Connected to Kafka broker at {bootstrap}. Listening for stream events..."))

            for message in consumer:
                event_data = message.value
                topic = message.topic
                self.stdout.write(f"Consumed event from [{topic}]: Key={message.key}")
                if topic == EventTopic.DEVICE_STATUS:
                    stream_processor.handle_device_status_event(event_data)
                elif topic == EventTopic.ALERT_LIFECYCLE:
                    stream_processor.handle_alert_event(event_data)
                elif topic == EventTopic.TELEMETRY_SNMP:
                    stream_processor.handle_telemetry_event(event_data)
                elif topic == EventTopic.AUTOMATION_JOB:
                    stream_processor.handle_automation_event(event_data)

        except ImportError:
            self.stdout.write(self.style.WARNING("kafka-python package not found or Kafka broker offline. Consumer operating in in-process stream mode."))
            while True:
                time.sleep(1)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Consumer terminated: {str(e)}"))
