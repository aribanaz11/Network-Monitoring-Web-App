from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.devices.models import Device, DeviceType, DeviceVendor, DeviceStatus, SNMPVersion, DeviceCredential
from apps.alerts.models import Alert, AlertSeverity, AlertStatus, Incident, IncidentStatus
from apps.monitoring.models import MonitoringCheck

User = get_user_model()

class Command(BaseCommand):
    help = 'Seeds initial enterprise demo users, network devices, and alerts for NetWatch'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("==> Seeding NetWatch Demo Users..."))

        users_data = [
            {'email': 'admin@netwatch.io', 'username': 'admin', 'name': 'Enterprise Admin', 'role': 'ADMIN', 'password': 'Admin@123456'},
            {'email': 'operator@netwatch.io', 'username': 'operator', 'name': 'NOC Operator', 'role': 'OPERATOR', 'password': 'Operator@123456'},
            {'email': 'viewer@netwatch.io', 'username': 'viewer', 'name': 'Audit Viewer', 'role': 'VIEWER', 'password': 'Viewer@123456'},
        ]

        for u in users_data:
            user, created = User.objects.get_or_create(
                email=u['email'],
                defaults={
                    'username': u['username'],
                    'first_name': u['name'].split()[0],
                    'last_name': u['name'].split()[1] if len(u['name'].split()) > 1 else '',
                    'role': u['role'],
                    'is_staff': u['role'] == 'ADMIN',
                    'is_superuser': u['role'] == 'ADMIN',
                }
            )
            if created:
                user.set_password(u['password'])
                user.save()
                self.stdout.write(self.style.SUCCESS(f"  + Created user: {u['email']} ({u['role']})"))
            else:
                self.stdout.write(f"  * User exists: {u['email']}")

        self.stdout.write(self.style.NOTICE("\n==> Seeding NetWatch Network Devices..."))

        devices_data = [
            {
                'hostname': 'core-router-01.dc1',
                'ip_address': '192.168.1.1',
                'device_type': DeviceType.ROUTER,
                'vendor': DeviceVendor.CISCO,
                'status': DeviceStatus.UP,
                'location': 'DataCenter 1 - Rack A1',
                'last_latency_ms': 12.4,
                'ssh_port': 22,
                'snmp_version': SNMPVersion.V2C,
                'ssh_username': 'cisco_admin',
                'ssh_password': 'CiscoAdminPass!2026',
                'snmp_community': 'public'
            },
            {
                'hostname': 'dist-switch-02.dc1',
                'ip_address': '192.168.1.2',
                'device_type': DeviceType.SWITCH,
                'vendor': DeviceVendor.CISCO,
                'status': DeviceStatus.UP,
                'location': 'DataCenter 1 - Rack A2',
                'last_latency_ms': 8.7,
                'ssh_port': 22,
                'snmp_version': SNMPVersion.V2C,
                'ssh_username': 'switch_op',
                'ssh_password': 'SwitchPass!2026',
                'snmp_community': 'public'
            },
            {
                'hostname': 'edge-firewall-01.hq',
                'ip_address': '10.0.0.1',
                'device_type': DeviceType.FIREWALL,
                'vendor': DeviceVendor.GENERIC,
                'status': DeviceStatus.UP,
                'location': 'Headquarters - DMZ',
                'last_latency_ms': 15.2,
                'ssh_port': 22,
                'snmp_version': SNMPVersion.V2C,
                'ssh_username': 'fw_sec',
                'ssh_password': 'FirewallPass!2026',
                'snmp_community': 'public'
            },
            {
                'hostname': 'core-router-02.dc2',
                'ip_address': '10.0.10.1',
                'device_type': DeviceType.ROUTER,
                'vendor': DeviceVendor.JUNIPER,
                'status': DeviceStatus.DEGRADED,
                'location': 'DataCenter 2 - Rack B3',
                'last_latency_ms': 185.0,
                'ssh_port': 22,
                'snmp_version': SNMPVersion.V2C,
                'ssh_username': 'junos_admin',
                'ssh_password': 'JunosPass!2026',
                'snmp_community': 'public'
            },
            {
                'hostname': 'backup-switch-01.dr',
                'ip_address': '10.0.20.1',
                'device_type': DeviceType.SWITCH,
                'vendor': DeviceVendor.ARISTA,
                'status': DeviceStatus.DOWN,
                'location': 'Disaster Recovery Site',
                'last_latency_ms': None,
                'ssh_port': 22,
                'snmp_version': SNMPVersion.V2C,
                'ssh_username': 'eos_admin',
                'ssh_password': 'EosPass!2026',
                'snmp_community': 'public'
            },
            {
                'hostname': 'db-server-node-01',
                'ip_address': '172.16.0.10',
                'device_type': DeviceType.SERVER,
                'vendor': DeviceVendor.LINUX,
                'status': DeviceStatus.UP,
                'location': 'Cluster Node 01',
                'last_latency_ms': 4.1,
                'ssh_port': 22,
                'snmp_version': SNMPVersion.V2C,
                'ssh_username': 'root',
                'ssh_password': 'RootServerPass!2026',
                'snmp_community': 'public'
            }
        ]

        created_devices = []
        for dev_info in devices_data:
            ssh_user = dev_info.pop('ssh_username', 'admin')
            ssh_pass = dev_info.pop('ssh_password', 'admin123')
            snmp_comm = dev_info.pop('snmp_community', 'public')

            device, created = Device.objects.get_or_create(
                hostname=dev_info['hostname'],
                defaults=dev_info
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"  + Created device: {device.hostname} ({device.ip_address}) - {device.status}"))
            else:
                self.stdout.write(f"  * Device exists: {device.hostname}")
            created_devices.append(device)

            # Ensure DeviceCredential exists with encrypted secrets
            cred, _ = DeviceCredential.objects.get_or_create(
                device=device,
                defaults={'ssh_username': ssh_user}
            )
            cred.ssh_username = ssh_user
            cred.set_ssh_password(ssh_pass)
            cred.set_snmp_community(snmp_comm)
            cred.save()

            # Ensure MonitoringCheck exists
            MonitoringCheck.objects.get_or_create(
                device=device,
                defaults={'check_type': 'ICMP', 'interval_seconds': 30, 'is_active': True}
            )

        self.stdout.write(self.style.NOTICE("\n==> Seeding Demo Alert & Incident..."))
        down_dev = next((d for d in created_devices if d.status == DeviceStatus.DOWN), None)
        if down_dev:
            inc, _ = Incident.objects.get_or_create(
                device=down_dev,
                status=IncidentStatus.OPEN,
                defaults={
                    'title': f'Node Outage: {down_dev.hostname}',
                    'severity': AlertSeverity.CRITICAL,
                    'occurrence_count': 4,
                    'timeline': [
                        {'event': 'INCIDENT_CREATED', 'timestamp': '2026-09-02T10:00:00Z', 'reason': 'Host unreachable (100% packet loss)'},
                        {'event': 'RECURRING_FAILURE', 'timestamp': '2026-09-02T10:05:00Z', 'reason': 'Failure probe 2'},
                        {'event': 'RECURRING_FAILURE', 'timestamp': '2026-09-02T10:10:00Z', 'reason': 'Failure probe 3'},
                        {'event': 'RECURRING_FAILURE', 'timestamp': '2026-09-02T10:15:00Z', 'reason': 'Failure probe 4'},
                    ]
                }
            )
            Alert.objects.get_or_create(
                device=down_dev,
                title=f'Host Unreachable: {down_dev.hostname}',
                defaults={
                    'message': 'Continuous ICMP timeout across 4 polling intervals.',
                    'severity': AlertSeverity.CRITICAL,
                    'status': AlertStatus.OPEN
                }
            )

            self.stdout.write(self.style.SUCCESS(f"  + Created Active Incident & Alert for {down_dev.hostname}"))

        self.stdout.write(self.style.SUCCESS("\n[SUCCESS] NetWatch Demo Environment Seeded Successfully!\n"))
