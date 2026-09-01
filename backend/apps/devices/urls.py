from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DeviceViewSet,
    DeviceInterfaceViewSet,
    DeviceSSHCommandView,
    DeviceSNMPPollView,
    DeviceSNMPWalkView
)

router = DefaultRouter()
router.register(r'', DeviceViewSet, basename='device')
router.register(r'interfaces', DeviceInterfaceViewSet, basename='device-interface')

urlpatterns = [
    path('<uuid:device_id>/ssh/', DeviceSSHCommandView.as_view(), name='device_ssh'),
    path('<uuid:device_id>/snmp/', DeviceSNMPPollView.as_view(), name='device_snmp'),
    path('<uuid:device_id>/snmp/walk/', DeviceSNMPWalkView.as_view(), name='device_snmp_walk'),
    path('', include(router.urls)),
]
