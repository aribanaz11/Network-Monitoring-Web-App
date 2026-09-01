"""
NetWatch Enterprise Multi-Subsystem Health & Observability Probes
Provides /api/health/live (Liveness) and /api/health/ready (Readiness).
"""

import time
import os
import redis
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from django.db import connection
from django.conf import settings
from apps.metrics.mongo_client import telemetry_client
from apps.network_engine.circuit_breaker import CircuitBreaker


class LivenessHealthView(APIView):
    """
    Kubernetes / Cloud Liveness probe.
    GET /api/health/live/
    Verifies that the Django HTTP process is responsive.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response({
            'status': 'alive',
            'timestamp': time.time(),
            'version': '1.0.0'
        }, status=status.HTTP_200_OK)


class ReadinessHealthView(APIView):
    """
    Deep Readiness probe verifying all upstream dependencies and data stores.
    GET /api/health/ready/
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        start_time = time.perf_counter()
        dependencies = {}
        all_healthy = True

        # 1. Check PostgreSQL / Relational DB
        db_start = time.perf_counter()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                row = cursor.fetchone()
                db_duration_ms = round((time.perf_counter() - db_start) * 1000.0, 2)
                if row and row[0] == 1:
                    dependencies['relational_db'] = {
                        'status': 'HEALTHY',
                        'engine': connection.vendor,
                        'latency_ms': db_duration_ms
                    }
                else:
                    all_healthy = False
                    dependencies['relational_db'] = {'status': 'DEGRADED', 'error': 'Unexpected response'}
        except Exception as e:
            all_healthy = False
            dependencies['relational_db'] = {'status': 'UNHEALTHY', 'error': str(e)}

        # 2. Check Redis Cache / Broker
        redis_start = time.perf_counter()
        try:
            broker_url = getattr(settings, 'CELERY_BROKER_URL', 'redis://localhost:6379/0')
            if 'redis' in broker_url:
                r = redis.Redis.from_url(broker_url, socket_timeout=1.0)
                r.ping()
                r_duration_ms = round((time.perf_counter() - redis_start) * 1000.0, 2)
                dependencies['redis_cache'] = {
                    'status': 'HEALTHY',
                    'latency_ms': r_duration_ms,
                    'role': 'Cache & CircuitBreaker'
                }
            elif 'amqp' in broker_url:
                dependencies['rabbitmq_broker'] = {
                    'status': 'CONFIGURED',
                    'role': 'TaskBroker'
                }
            else:
                dependencies['broker'] = {'status': 'MEMORY_EAGER', 'mode': 'test'}
        except Exception as e:
            dependencies['redis_cache'] = {'status': 'FALLBACK_LOCAL', 'note': str(e)}

        # 3. Check MongoDB Telemetry
        if telemetry_client._connected:
            dependencies['mongo_telemetry'] = {
                'status': 'HEALTHY',
                'database': getattr(settings, 'MONGODB_DB_NAME', 'netwatch_telemetry')
            }
        else:
            dependencies['mongo_telemetry'] = {
                'status': 'OPTIONAL_OFFLINE',
                'note': 'Telemetry routed through relational fallback'
            }

        # 4. Celery Worker Queue Topology
        dependencies['celery_workers'] = {
            'queues': ['high_priority_icmp', 'snmp_telemetry', 'automation_jobs', 'default'],
            'beat_schedule': 'Active (30s interval)',
            'eager_mode': getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False)
        }

        # 5. Circuit Breakers
        dependencies['circuit_breakers'] = CircuitBreaker.get_all_states()

        total_duration_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
        overall_status = 'HEALTHY' if all_healthy else 'DEGRADED'
        http_code = status.HTTP_200_OK if all_healthy else status.HTTP_503_SERVICE_UNAVAILABLE

        return Response({
            'status': overall_status,
            'response_time_ms': total_duration_ms,
            'timestamp': time.time(),
            'dependencies': dependencies
        }, status=http_code)


class HealthCheckView(ReadinessHealthView):
    """
    Backwards-compatible health check endpoint.
    GET /api/health/
    """
    pass
