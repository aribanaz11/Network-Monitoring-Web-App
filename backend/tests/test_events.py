import json
import pytest
from rest_framework import status
from django.urls import reverse
from apps.accounts.models import User, UserRole
from apps.events.kafka_bus import event_bus
from apps.events.schemas import EventTopic
from apps.events.consumer import stream_processor

@pytest.mark.django_db
class TestKafkaEventStreaming:
    @pytest.fixture(autouse=True)
    def setup_bus(self):
        event_bus.clear_buffer()

    @pytest.fixture
    def operator_client(self, client):
        user = User.objects.create_user(email='stream_op@netwatch.io', password='Password123!', role=UserRole.OPERATOR)
        resp = client.post(reverse('token_obtain_pair'), json.dumps({'email': 'stream_op@netwatch.io', 'password': 'Password123!'}), content_type='application/json')
        client.defaults['HTTP_AUTHORIZATION'] = f"Bearer {resp.data['access']}"
        return client

    @pytest.fixture
    def viewer_client(self, client):
        user = User.objects.create_user(email='stream_viewer@netwatch.io', password='Password123!', role=UserRole.VIEWER)
        resp = client.post(reverse('token_obtain_pair'), json.dumps({'email': 'stream_viewer@netwatch.io', 'password': 'Password123!'}), content_type='application/json')
        client.defaults['HTTP_AUTHORIZATION'] = f"Bearer {resp.data['access']}"
        return client

    def test_kafka_bus_publish_and_retention(self):
        event = event_bus.publish_event(
            topic=EventTopic.DEVICE_STATUS,
            payload_or_key='192.168.1.1',
            payload={
                'hostname': 'core-gw-01',
                'old_status': 'ONLINE',
                'new_status': 'OFFLINE',
                'latency_ms': None
            }
        )

        assert event['topic'] == EventTopic.DEVICE_STATUS
        assert event['key'] == '192.168.1.1'
        assert event['payload']['hostname'] == 'core-gw-01'
        assert 'timestamp' in event
        assert event['offset'] is not None

        events = event_bus.get_recent_events()
        assert len(events) == 1
        assert events[0]['key'] == '192.168.1.1'

    def test_kafka_bus_topic_filtering(self):
        event_bus.publish_event(EventTopic.DEVICE_STATUS, 'dev-1', {'status': 'ONLINE'})
        event_bus.publish_event(EventTopic.ALERT_LIFECYCLE, 'alert-1', {'severity': 'CRITICAL'})
        event_bus.publish_event(EventTopic.TELEMETRY_SNMP, 'dev-1', {'cpu': 45.2})

        status_events = event_bus.get_recent_events(topic=EventTopic.DEVICE_STATUS)
        alert_events = event_bus.get_recent_events(topic=EventTopic.ALERT_LIFECYCLE)

        assert len(status_events) == 1
        assert status_events[0]['topic'] == EventTopic.DEVICE_STATUS
        assert len(alert_events) == 1
        assert alert_events[0]['topic'] == EventTopic.ALERT_LIFECYCLE

    def test_stream_consumer_anomaly_detection(self):
        # Trigger 3 rapid OFFLINE events to trigger cascading outage anomaly
        event_bus.publish_event(EventTopic.DEVICE_STATUS, 'switch-01', {'hostname': 'switch-01', 'new_status': 'OFFLINE'})
        event_bus.publish_event(EventTopic.DEVICE_STATUS, 'switch-02', {'hostname': 'switch-02', 'new_status': 'OFFLINE'})
        event_bus.publish_event(EventTopic.DEVICE_STATUS, 'switch-03', {'hostname': 'switch-03', 'new_status': 'OFFLINE'})

        consumer_status = stream_processor.get_consumer_status()
        assert consumer_status['total_events_processed'] >= 3
        assert consumer_status['active_anomalies_detected'] >= 1
        assert any(a['type'] == 'CASCADING_OUTAGE_DETECTED' for a in consumer_status['latest_anomalies'])

    def test_live_event_stream_api_endpoint(self, viewer_client):
        event_bus.publish_event(EventTopic.DEVICE_STATUS, 'rtr-01', {'hostname': 'rtr-01', 'new_status': 'ONLINE'})

        url = reverse('live_event_stream')
        resp = viewer_client.get(url)

        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['count'] == 1
        assert resp.data['results'][0]['key'] == 'rtr-01'

    def test_event_stream_stats_api_endpoint(self, viewer_client):
        event_bus.publish_event(EventTopic.TELEMETRY_SNMP, 'sw-01', {'cpu': 33.1})

        url = reverse('event_stream_stats')
        resp = viewer_client.get(url)

        assert resp.status_code == status.HTTP_200_OK
        assert 'stream_metrics' in resp.data
        assert 'consumer_group_metrics' in resp.data
        assert resp.data['stream_metrics']['total_events_published'] >= 1
        assert EventTopic.TELEMETRY_SNMP in resp.data['available_topics']

    def test_event_replay_endpoint_viewer_forbidden(self, viewer_client):
        url = reverse('event_stream_replay')
        resp = viewer_client.post(
            url,
            json.dumps({'topic': EventTopic.DEVICE_STATUS, 'key': 'test-node'}),
            content_type='application/json'
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_event_replay_endpoint_operator_success(self, operator_client):
        url = reverse('event_stream_replay')
        resp = operator_client.post(
            url,
            json.dumps({
                'topic': EventTopic.DEVICE_STATUS,
                'key': 'simulated-core-switch',
                'payload': {'hostname': 'core-sw-01', 'new_status': 'ONLINE', 'latency_ms': 12.4}
            }),
            content_type='application/json'
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data['status'] == 'PUBLISHED'
        assert resp.data['event']['key'] == 'simulated-core-switch'

