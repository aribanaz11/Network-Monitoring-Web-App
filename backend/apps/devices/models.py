import uuid
from django.db import models
from django.utils import timezone
from cryptography.fernet import Fernet
from django.conf import settings

class DeviceType(models.TextChoices):
    ROUTER = 'ROUTER', 'Core / Edge Router'
    SWITCH = 'SWITCH', 'Layer 2 / Layer 3 Switch'
    FIREWALL = 'FIREWALL', 'Next-Gen Firewall'
    SERVER = 'SERVER', 'Linux / Windows Server'
    ACCESS_POINT = 'ACCESS_POINT', 'Wireless Access Point'

class DeviceVendor(models.TextChoices):
    CISCO = 'CISCO', 'Cisco Systems'
    JUNIPER = 'JUNIPER', 'Juniper Networks'
    ARISTA = 'ARISTA', 'Arista Networks'
    LINUX = 'LINUX', 'Generic Linux'
    GENERIC = 'GENERIC', 'Generic SNMP Device'

class DeviceStatus(models.TextChoices):
    ONLINE = 'ONLINE', 'Online / Reachable'
    OFFLINE = 'OFFLINE', 'Offline / Unreachable'
    DEGRADED = 'DEGRADED', 'Degraded / High Latency'
    UNKNOWN = 'UNKNOWN', 'Unknown / Unchecked'

class SNMPVersion(models.TextChoices):
    V2C = 'v2c', 'SNMP v2c'
    V3 = 'v3', 'SNMP v3 (USM)'

class Device(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hostname = models.CharField(max_length=128, unique=True, db_index=True)
    ip_address = models.GenericIPAddressField(protocol='both', unpack_ipv4=True, db_index=True)
    device_type = models.CharField(
        max_length=32,
        choices=DeviceType.choices,
        default=DeviceType.ROUTER,
        db_index=True
    )
    vendor = models.CharField(
        max_length=32,
        choices=DeviceVendor.choices,
        default=DeviceVendor.CISCO
    )
    model = models.CharField(max_length=64, blank=True, default='')
    os_version = models.CharField(max_length=64, blank=True, default='')
    location = models.CharField(max_length=128, blank=True, default='Datacenter 1')
    
    # Network Ports & Protocols
    ssh_port = models.PositiveIntegerField(default=22)
    snmp_version = models.CharField(
        max_length=8,
        choices=SNMPVersion.choices,
        default=SNMPVersion.V2C
    )
    snmp_port = models.PositiveIntegerField(default=161)
    
    # Monitoring Configuration & State
    monitoring_interval = models.PositiveIntegerField(
        default=30,
        help_text="Polling interval in seconds"
    )
    status = models.CharField(
        max_length=16,
        choices=DeviceStatus.choices,
        default=DeviceStatus.UNKNOWN,
        db_index=True
    )
    consecutive_failures = models.PositiveIntegerField(default=0)
    last_seen = models.DateTimeField(null=True, blank=True)
    last_latency_ms = models.FloatField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'netwatch_devices'
        verbose_name = 'Network Device'
        verbose_name_plural = 'Network Devices'
        ordering = ['hostname']
        indexes = [
            models.Index(fields=['status', 'last_seen'], name='idx_device_status_lastseen'),
            models.Index(fields=['ip_address'], name='idx_device_ip'),
        ]

    def __str__(self):
        return f"{self.hostname} ({self.ip_address}) - {self.status}"

    def mark_online(self, latency_ms=None):
        self.status = DeviceStatus.ONLINE
        self.consecutive_failures = 0
        self.last_seen = timezone.now()
        if latency_ms is not None:
            self.last_latency_ms = latency_ms
        self.save(update_fields=['status', 'consecutive_failures', 'last_seen', 'last_latency_ms', 'updated_at'])

    def mark_offline(self):
        self.consecutive_failures += 1
        self.status = DeviceStatus.OFFLINE
        self.save(update_fields=['status', 'consecutive_failures', 'updated_at'])


class DeviceCredential(models.Model):
    """
    Stores encrypted SSH / SNMP credentials using symmetric Fernet encryption at rest.
    Secrets are never exposed in plaintext in logs or API read responses.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device = models.OneToOneField(Device, on_delete=models.CASCADE, related_name='credential')
    
    # SSH Credentials
    ssh_username = models.CharField(max_length=64, blank=True, default='admin')
    _encrypted_ssh_password = models.TextField(blank=True, default='', db_column='ssh_password')
    _encrypted_ssh_key = models.TextField(blank=True, default='', db_column='ssh_private_key')
    
    # SNMP v2c Credentials
    _encrypted_snmp_community = models.TextField(blank=True, default='', db_column='snmp_community')
    
    # SNMP v3 USM Credentials
    snmp_v3_user = models.CharField(max_length=64, blank=True, default='')
    snmp_v3_auth_proto = models.CharField(max_length=16, blank=True, default='SHA') # SHA, MD5, SHA256
    _encrypted_snmp_v3_auth_key = models.TextField(blank=True, default='', db_column='snmp_v3_auth_key')
    snmp_v3_priv_proto = models.CharField(max_length=16, blank=True, default='AES128') # AES128, DES
    _encrypted_snmp_v3_priv_key = models.TextField(blank=True, default='', db_column='snmp_v3_priv_key')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'netwatch_device_credentials'

    def _get_fernet(self):
        key = getattr(settings, 'FERNET_KEY', 'W3sO-LqP7b_dG5vUv-0L2Y1t9kLpM_xZ7sQ2dF4jK8M=')
        if isinstance(key, str):
            key = key.encode()
        return Fernet(key)

    def set_ssh_password(self, raw_password: str):
        if raw_password:
            f = self._get_fernet()
            self._encrypted_ssh_password = f.encrypt(raw_password.encode()).decode()
        else:
            self._encrypted_ssh_password = ''

    def get_ssh_password(self) -> str:
        if not self._encrypted_ssh_password:
            return ''
        try:
            f = self._get_fernet()
            return f.decrypt(self._encrypted_ssh_password.encode()).decode()
        except Exception:
            return ''

    def set_snmp_community(self, raw_community: str):
        if raw_community:
            f = self._get_fernet()
            self._encrypted_snmp_community = f.encrypt(raw_community.encode()).decode()
        else:
            self._encrypted_snmp_community = ''

    def get_snmp_community(self) -> str:
        if not self._encrypted_snmp_community:
            return 'public'
        try:
            f = self._get_fernet()
            return f.decrypt(self._encrypted_snmp_community.encode()).decode()
        except Exception:
            return 'public'


class DeviceInterface(models.Model):
    """
    Physical and logical network interfaces attached to the device.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='interfaces')
    name = models.CharField(max_length=64, help_text="e.g. GigabitEthernet0/1 or eth0")
    description = models.CharField(max_length=255, blank=True, default='')
    mac_address = models.CharField(max_length=32, blank=True, default='')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    subnet_mask = models.CharField(max_length=32, blank=True, default='255.255.255.0')
    oper_status = models.CharField(max_length=16, default='UP') # UP, DOWN
    admin_status = models.CharField(max_length=16, default='UP')
    speed_mbps = models.BigIntegerField(default=1000) # 1 Gbps
    in_octets = models.BigIntegerField(default=0)
    out_octets = models.BigIntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'netwatch_device_interfaces'
        unique_together = ('device', 'name')
        ordering = ['name']

    def __str__(self):
        return f"{self.device.hostname} - {self.name} ({self.oper_status})"
