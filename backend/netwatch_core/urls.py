from django.contrib import admin
from django.urls import path, include
from .health import HealthCheckView

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # System Health
    path('api/health/', HealthCheckView.as_view(), name='health_check'),

    # App Routes
    path('api/auth/', include('apps.accounts.urls')),
    path('api/devices/', include('apps.devices.urls')),
    path('api/monitoring/', include('apps.monitoring.urls')),
    path('api/alerts/', include('apps.alerts.urls')),
    path('api/automation/', include('apps.automation.urls')),
    path('api/audit/', include('apps.audit.urls')),
    path('api/', include('apps.metrics.urls')),
]
