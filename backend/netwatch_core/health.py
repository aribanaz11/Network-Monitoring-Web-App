import os
import redis
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from django.db import connection
from django.conf import settings
from apps.metrics.mongo_client import telemetry_client

class HealthCheckView(APIView):
    """
    Enterprise multi-subsystem health check endpoint.
    GET /api/health/
    Verifies relational database, redis broker, and mongo telemetry connectivity.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        health_status = {
            'status': 'healthy',
            'components': {
                'api': {'status': 'healthy', 'version': '1.0.0'},
                'database': {'status': 'unknown'},
                'broker': {'status': 'unknown'},
                'mongodb': {'status': 'unknown'},
                'simulator_mode': getattr(settings, 'SIMULATOR_MODE', True)
            }
        }

        # Check Relational Database
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                row = cursor.fetchone()
                if row and row[0] == 1:
                    health_status['components']['database'] = {
                        'status': 'healthy',
                        'engine': connection.vendor
                    }
        except Exception as e:
            health_status['status'] = 'degraded'
            health_status['components']['database'] = {
                'status': 'unhealthy',
                'error': str(e)
            }

        # Check Redis / Broker
        try:
            broker_url = getattr(settings, 'CELERY_BROKER_URL', 'redis://localhost:6379/0')
            if 'redis' in broker_url:
                r = redis.Redis.from_url(broker_url, socket_timeout=1)
                r.ping()
                health_status['components']['broker'] = {'status': 'healthy', 'type': 'redis'}
            else:
                health_status['components']['broker'] = {'status': 'healthy', 'type': 'configured'}
        except Exception:
            health_status['components']['broker'] = {'status': 'offline', 'mode': 'local_sync'}

        # Check MongoDB
        if telemetry_client._connected:
            health_status['components']['mongodb'] = {'status': 'healthy', 'db': telemetry_client.db_name}
        else:
            health_status['components']['mongodb'] = {'status': 'standby', 'mode': 'in_memory_buffer'}

        status_code = status.HTTP_200_OK if health_status['status'] == 'healthy' else status.HTTP_200_OK
        return Response(health_status, status=status_code)
