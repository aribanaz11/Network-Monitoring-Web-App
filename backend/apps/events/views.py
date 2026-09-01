"""
NetWatch Event Stream REST API Views.
Exposes live Kafka streaming events, stream throughput analytics, and event replay capabilities.
"""
from rest_framework import views, status
from rest_framework.response import Response
from apps.accounts.permissions import IsViewerRole, IsOperatorRole, IsAdminRole
from apps.events.kafka_bus import event_bus
from apps.events.consumer import stream_processor
from apps.events.schemas import EventTopic
from apps.audit.utils import log_audit_event

class LiveEventStreamView(views.APIView):
    """
    Retrieve real-time event streaming entries from the event bus buffer.
    GET /api/events/live/?topic=...&key=...&limit=...
    """
    permission_classes = [IsViewerRole]

    def get(self, request):
        topic = request.query_params.get('topic')
        key = request.query_params.get('key')
        limit = int(request.query_params.get('limit', 50))
        limit = max(1, min(limit, 200))

        events = event_bus.get_recent_events(topic=topic, key=key, limit=limit)
        stats = event_bus.get_stream_stats()

        return Response({
            'count': len(events),
            'limit': limit,
            'topic_filter': topic,
            'broker_status': stats['broker_status'],
            'results': events
        }, status=status.HTTP_200_OK)


class EventStreamStatsView(views.APIView):
    """
    Retrieve real-time Kafka event streaming health, throughput (EPS), topic distribution, and consumer anomalies.
    GET /api/events/stats/
    """
    permission_classes = [IsViewerRole]

    def get(self, request):
        bus_stats = event_bus.get_stream_stats()
        consumer_stats = stream_processor.get_consumer_status()

        return Response({
            'stream_metrics': bus_stats,
            'consumer_group_metrics': consumer_stats,
            'available_topics': EventTopic.ALL_TOPICS
        }, status=status.HTTP_200_OK)


class EventReplayTriggerView(views.APIView):
    """
    Trigger a simulated event stream publication for integration testing, incident simulation, and audit pipelines.
    POST /api/events/replay/
    """
    permission_classes = [IsOperatorRole]

    def post(self, request):
        topic = request.data.get('topic', EventTopic.DEVICE_STATUS)
        key = request.data.get('key', 'test-stream-node')
        payload = request.data.get('payload', {
            'hostname': 'core-rtr-01.sim',
            'old_status': 'ONLINE',
            'new_status': 'DEGRADED',
            'latency_ms': 185.4,
            'reason': 'Synthetic stream injection for verification'
        })

        if topic not in EventTopic.ALL_TOPICS and not topic.startswith('netwatch.'):
            return Response(
                {'error': f"Invalid topic. Allowed topics: {EventTopic.ALL_TOPICS}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        event = event_bus.publish_event(topic=topic, payload_or_key=key, payload=payload)

        log_audit_event(
            user=request.user,
            action='STREAM_EVENT_EMITTED',
            resource_type='EventStream',
            resource_id=topic,
            ip_address=getattr(request, 'client_ip', '127.0.0.1'),
            details={'key': key, 'topic': topic}
        )

        return Response({
            'status': 'PUBLISHED',
            'message': f"Event published to topic [{topic}]",
            'event': event
        }, status=status.HTTP_201_CREATED)
