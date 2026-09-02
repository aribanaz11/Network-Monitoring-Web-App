import os
import sys
import django

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'netwatch_core.settings')
django.setup()

from django.utils import timezone
from apps.accounts.models import User, UserRole
from apps.devices.models import Device, DeviceCredential, DeviceInterface, DeviceType, DeviceVendor, DeviceStatus, SNMPVersion
from apps.monitoring.models import MonitoringCheck, CheckType, CheckStatus, MonitoringLog
from apps.alerts.models import Alert, AlertSeverity, AlertStatus
from apps.automation.models import AutomationJob, JobType, JobStatus
from apps.audit.models import AuditLog

def seed():
    print("Seeding NetWatch Database...")

    admin_pwd = os.environ.get('DEFAULT_ADMIN_PASSWORD', 'NetWatchDevAdminPass!2026')
    operator_pwd = os.environ.get('DEFAULT_OPERATOR_PASSWORD', 'NetWatchDevOperatorPass!2026')
    viewer_pwd = os.environ.get('DEFAULT_VIEWER_PASSWORD', 'NetWatchDevViewerPass!2026')

    # 1. Users
    admin_user, _ = User.objects.get_or_create(
        email='admin@netwatch.io',
        defaults={
            'full_name': 'Enterprise Admin',
            'role': UserRole.ADMIN,
            'is_staff': True,
            'is_superuser': True
        }
    )
    admin_user.set_password(admin_pwd)
    admin_user.save()

    operator_user, _ = User.objects.get_or_create(
        email='operator@netwatch.io',
        defaults={
            'full_name': 'NOC Operator',
            'role': UserRole.OPERATOR,
            'is_staff': False
        }
    )
    operator_user.set_password(operator_pwd)
    operator_user.save()

    viewer_user, _ = User.objects.get_or_create(
        email='viewer@netwatch.io',
        defaults={
            'full_name': 'Audit Viewer',
            'role': UserRole.VIEWER,
            'is_staff': False
        }
    )
    viewer_user.set_password(viewer_pwd)
    viewer_user.save()

    print("Created users: admin@netwatch.io, operator@netwatch.io, viewer@netwatch.io")

    # 2. Devices
    devices_data = [
        {
            'hostname': 'core-rtr-01.dc1',
            'ip_address': '192.168.10.1',
            'device_type': DeviceType.ROUTER,
            'vendor': DeviceVendor.CISCO,
            'model': 'Cisco ASR 9006',
            'os_version': 'IOS-XR 7.3.2',
            'location': 'Primary DC - Rack A01',
            'status': DeviceStatus.ONLINE,
            'last_latency_ms': 11.4,
            'snmp_version': SNMPVersion.V2C,
            'ssh_user': 'cisco_admin',
            'ssh_pass': 'CiscoSecret!2026',
            'snmp_comm': 'public_dc1',
            'interfaces': [
                {'name': 'TenGigE0/0/0/0', 'description': 'WAN Primary Backbone', 'ip': '192.168.10.1', 'speed': 10000},
                {'name': 'GigabitEthernet0/0/0/1', 'description': 'Core Switch Link 1', 'ip': '10.0.1.1', 'speed': 1000},
            ]
        },
        {
            'hostname': 'dist-sw-01.dc1',
            'ip_address': '192.168.10.2',
            'device_type': DeviceType.SWITCH,
            'vendor': DeviceVendor.CISCO,
            'model': 'Catalyst 9500-48Y4C',
            'os_version': 'Cisco IOS-XE 17.09.01',
            'location': 'Primary DC - Rack B02',
            'status': DeviceStatus.ONLINE,
            'last_latency_ms': 8.2,
            'snmp_version': SNMPVersion.V3,
            'ssh_user': 'noc_operator',
            'ssh_pass': 'SwPass@2026',
            'snmp_comm': 'netwatch_v3_sec',
            'interfaces': [
                {'name': 'TwentyFiveGigE1/0/1', 'description': 'Uplink to Core Router', 'ip': '192.168.10.2', 'speed': 25000},
                {'name': 'GigabitEthernet1/0/24', 'description': 'Access Switch Trunk', 'ip': '10.0.2.1', 'speed': 1000},
            ]
        },
        {
            'hostname': 'edge-fw-01.dc1',
            'ip_address': '192.168.10.3',
            'device_type': DeviceType.FIREWALL,
            'vendor': DeviceVendor.CISCO,
            'model': 'Firepower 2130 NGFW',
            'os_version': 'FTD 7.2.4',
            'location': 'DMZ Edge - Rack C01',
            'status': DeviceStatus.ONLINE,
            'last_latency_ms': 14.8,
            'snmp_version': SNMPVersion.V2C,
            'ssh_user': 'sec_admin',
            'ssh_pass': 'FwAdmin#2026',
            'snmp_comm': 'sec_monitor',
            'interfaces': [
                {'name': 'ethernet1/1', 'description': 'Internet Gateway Outside', 'ip': '192.168.10.3', 'speed': 10000},
                {'name': 'ethernet1/2', 'description': 'Internal Trust Interface', 'ip': '10.100.1.1', 'speed': 10000},
            ]
        },
        {
            'hostname': 'access-sw-02.branch',
            'ip_address': '192.168.20.10',
            'device_type': DeviceType.SWITCH,
            'vendor': DeviceVendor.ARISTA,
            'model': 'Arista 7050SX3-48YC8',
            'os_version': 'EOS 4.28.2F',
            'location': 'Branch Site - Bangalore East',
            'status': DeviceStatus.ONLINE,
            'last_latency_ms': 18.6,
            'snmp_version': SNMPVersion.V2C,
            'ssh_user': 'admin',
            'ssh_pass': 'AristaEos!2026',
            'snmp_comm': 'branch_comm',
            'interfaces': [
                {'name': 'Ethernet1', 'description': 'Branch Gateway Uplink', 'ip': '192.168.20.10', 'speed': 10000},
            ]
        },
        {
            'hostname': 'linux-srv-01.prod',
            'ip_address': '192.168.30.50',
            'device_type': DeviceType.SERVER,
            'vendor': DeviceVendor.LINUX,
            'model': 'Dell PowerEdge R750',
            'os_version': 'Ubuntu 24.04 LTS (Kernel 6.8)',
            'location': 'Compute Cluster - Rack D05',
            'status': DeviceStatus.ONLINE,
            'last_latency_ms': 6.1,
            'snmp_version': SNMPVersion.V2C,
            'ssh_user': 'root',
            'ssh_pass': 'ServerRoot!2026',
            'snmp_comm': 'srv_mon',
            'interfaces': [
                {'name': 'eth0', 'description': 'Primary Bond Interface', 'ip': '192.168.30.50', 'speed': 10000},
            ]
        },
        {
            'hostname': 'backup-rtr-02.dr',
            'ip_address': '192.168.40.9',
            'device_type': DeviceType.ROUTER,
            'vendor': DeviceVendor.JUNIPER,
            'model': 'Juniper MX480',
            'os_version': 'Junos OS 21.4R3',
            'location': 'DR Datacenter - Chennai',
            'status': DeviceStatus.OFFLINE,
            'last_latency_ms': None,
            'snmp_version': SNMPVersion.V2C,
            'ssh_user': 'admin',
            'ssh_pass': 'JunosSecret#2026',
            'snmp_comm': 'dr_community',
            'interfaces': [
                {'name': 'ge-0/0/0', 'description': 'DR Link Down', 'ip': '192.168.40.9', 'speed': 1000},
            ]
        }
    ]

    created_devices = []
    for ddata in devices_data:
        interfaces = ddata.pop('interfaces')
        ssh_user = ddata.pop('ssh_user')
        ssh_pass = ddata.pop('ssh_pass')
        snmp_comm = ddata.pop('snmp_comm')

        device, created = Device.objects.get_or_create(
            hostname=ddata['hostname'],
            defaults={
                **ddata,
                'last_seen': timezone.now() if ddata['status'] == DeviceStatus.ONLINE else None,
                'consecutive_failures': 0 if ddata['status'] == DeviceStatus.ONLINE else 3
            }
        )

        # Credentials
        cred, _ = DeviceCredential.objects.get_or_create(device=device)
        cred.ssh_username = ssh_user
        cred.set_ssh_password(ssh_pass)
        cred.set_snmp_community(snmp_comm)
        cred.save()

        # Interfaces
        for iface in interfaces:
            DeviceInterface.objects.get_or_create(
                device=device,
                name=iface['name'],
                defaults={
                    'description': iface['description'],
                    'ip_address': iface['ip'],
                    'speed_mbps': iface['speed'],
                    'oper_status': 'UP' if device.status == DeviceStatus.ONLINE else 'DOWN',
                    'admin_status': 'UP'
                }
            )

        # Monitoring checks
        check_ping, _ = MonitoringCheck.objects.get_or_create(
            device=device,
            check_type=CheckType.ICMP_PING,
            defaults={
                'interval_seconds': 30,
                'timeout_seconds': 2,
                'is_active': True,
                'last_status': CheckStatus.SUCCESS if device.status == DeviceStatus.ONLINE else CheckStatus.FAILED,
                'last_latency_ms': device.last_latency_ms,
                'last_checked_at': timezone.now()
            }
        )

        check_ssh, _ = MonitoringCheck.objects.get_or_create(
            device=device,
            check_type=CheckType.TCP_PORT,
            port=22,
            defaults={
                'interval_seconds': 60,
                'timeout_seconds': 3,
                'is_active': True,
                'last_status': CheckStatus.SUCCESS if device.status == DeviceStatus.ONLINE else CheckStatus.TIMEOUT,
                'last_latency_ms': device.last_latency_ms,
                'last_checked_at': timezone.now()
            }
        )

        created_devices.append(device)

    print(f"Seeded {len(created_devices)} Network Devices.")

    # 3. Alerts
    Alert.objects.get_or_create(
        title='DR Router Link Unreachable (ICMP Timeout)',
        device=created_devices[-1], # backup-rtr-02.dr
        defaults={
            'severity': AlertSeverity.CRITICAL,
            'message': 'Device backup-rtr-02.dr (192.168.40.9) failed 3 consecutive ICMP ping checks. Destination unreachable.',
            'status': AlertStatus.OPEN,
            'triggered_at': timezone.now()
        }
    )

    Alert.objects.get_or_create(
        title='High Latency Detected on Edge Firewall',
        device=created_devices[2], # edge-fw-01.dc1
        defaults={
            'severity': AlertSeverity.WARNING,
            'message': 'Latency spike observed on edge-fw-01.dc1: measured 14.8ms (threshold 12.0ms).',
            'status': AlertStatus.ACKNOWLEDGED,
            'acknowledged_by': operator_user,
            'acknowledged_at': timezone.now(),
            'notes': 'Investigating bandwidth contention on outside link.'
        }
    )

    # 4. Automation Jobs
    job, _ = AutomationJob.objects.get_or_create(
        name='Daily Core Network Configuration Backup',
        defaults={
            'job_type': JobType.CONFIG_BACKUP,
            'status': JobStatus.SUCCESS,
            'command': 'show running-config',
            'result_summary': {'backed_up_count': 5, 'failed_count': 0, 'archive_path': '/var/backups/configs/20260901.tar.gz'},
            'triggered_by': admin_user,
            'started_at': timezone.now(),
            'completed_at': timezone.now()
        }
    )
    job.target_devices.set(created_devices[:5])

    # 5. Audit Log Seed
    AuditLog.objects.create(
        user=admin_user,
        action='SYSTEM_INITIALIZED',
        resource_type='System',
        resource_id='netwatch-core',
        ip_address='127.0.0.1',
        details={'version': '1.0.0', 'environment': 'production_ready'}
    )

    print("Seeding completed successfully!")

if __name__ == '__main__':
    seed()
