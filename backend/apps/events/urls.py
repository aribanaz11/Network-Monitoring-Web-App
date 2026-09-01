from django.urls import path
from .views import LiveEventStreamView, EventStreamStatsView, EventReplayTriggerView

urlpatterns = [
    path('live/', LiveEventStreamView.as_view(), name='live_event_stream'),
    path('stats/', EventStreamStatsView.as_view(), name='event_stream_stats'),
    path('replay/', EventReplayTriggerView.as_view(), name='event_stream_replay'),
]
