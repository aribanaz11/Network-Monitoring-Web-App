import os
from django.conf import settings
from django.contrib import admin
from django.http import FileResponse, HttpResponse
from django.urls import path, include, re_path
from django.views.static import serve
from .health import HealthCheckView

def serve_frontend_index(request):
    frontend_index = settings.BASE_DIR.parent / 'frontend' / 'index.html'
    if os.path.exists(frontend_index):
        return FileResponse(open(frontend_index, 'rb'), content_type='text/html')
    return HttpResponse("<h1>NetWatch API is online.</h1><p>Visit <a href='/api/health/'>/api/health/</a></p>")

urlpatterns = [
    # Frontend Root SPA & Assets
    path('', serve_frontend_index, name='frontend_index'),
    re_path(r'^src/(?P<path>.*)$', serve, {'document_root': settings.BASE_DIR.parent / 'frontend' / 'src'}),

    # Django Admin
    path('admin/', admin.site.urls),

    # System Health
    path('api/health/', HealthCheckView.as_view(), name='health_check'),

    # App Routes
    path('api/auth/', include('apps.accounts.urls')),
    path('api/devices/', include('apps.devices.urls')),
    path('api/monitoring/', include('apps.monitoring.urls')),
    path('api/alerts/', include('apps.alerts.urls')),
    path('api/automation/', include('apps.automation.urls')),
    path('api/events/', include('apps.events.urls')),
    path('api/audit/', include('apps.audit.urls')),
    path('api/', include('apps.metrics.urls')),
]
