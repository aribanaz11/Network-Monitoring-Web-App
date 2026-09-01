from rest_framework import serializers, generics, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import AuditLog
from apps.accounts.permissions import IsAdminRole

class AuditLogSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True, default='System / Automated')

    class Meta:
        model = AuditLog
        fields = ['id', 'user_email', 'action', 'resource_type', 'resource_id', 'ip_address', 'details', 'timestamp']
        read_only_fields = fields

class AuditLogListView(generics.ListAPIView):
    """
    Compliance audit trail log viewer for Administrators.
    """
    queryset = AuditLog.objects.all().select_related('user')
    serializer_class = AuditLogSerializer
    permission_classes = [IsAdminRole]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['action', 'resource_type']
    search_fields = ['action', 'resource_type', 'resource_id', 'details', 'ip_address', 'user__email']
    ordering_fields = ['timestamp', 'action', 'resource_type']
    ordering = ['-timestamp']
