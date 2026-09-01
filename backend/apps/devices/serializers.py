from rest_framework import serializers
from .models import Device, DeviceCredential, DeviceInterface, DeviceType, DeviceVendor, DeviceStatus, SNMPVersion

class DeviceInterfaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceInterface
        fields = ['id', 'name', 'description', 'mac_address', 'ip_address', 'subnet_mask', 'oper_status', 'admin_status', 'speed_mbps', 'in_octets', 'out_octets', 'last_updated']
        read_only_fields = ['id', 'last_updated']


class DeviceCredentialSerializer(serializers.ModelSerializer):
    ssh_password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    snmp_community = serializers.CharField(write_only=True, required=False, allow_blank=True)
    has_ssh_password = serializers.SerializerMethodField()
    has_snmp_community = serializers.SerializerMethodField()

    class Meta:
        model = DeviceCredential
        fields = [
            'id', 'ssh_username', 'ssh_password', 'has_ssh_password',
            'snmp_community', 'has_snmp_community', 'snmp_v3_user',
            'snmp_v3_auth_proto', 'snmp_v3_priv_proto', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'has_ssh_password', 'has_snmp_community']

    def get_has_ssh_password(self, obj):
        return bool(obj._encrypted_ssh_password)

    def get_has_snmp_community(self, obj):
        return bool(obj._encrypted_snmp_community)


class DeviceSerializer(serializers.ModelSerializer):
    interfaces = DeviceInterfaceSerializer(many=True, read_only=True)
    credential_summary = serializers.SerializerMethodField()

    class Meta:
        model = Device
        fields = [
            'id', 'hostname', 'ip_address', 'device_type', 'vendor', 'model', 'os_version',
            'location', 'ssh_port', 'snmp_version', 'snmp_port', 'monitoring_interval',
            'status', 'consecutive_failures', 'last_seen', 'last_latency_ms',
            'interfaces', 'credential_summary', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'consecutive_failures', 'last_seen', 'last_latency_ms', 'created_at', 'updated_at']

    def get_credential_summary(self, obj):
        if hasattr(obj, 'credential'):
            return {
                'ssh_username': obj.credential.ssh_username,
                'has_ssh_password': bool(obj.credential._encrypted_ssh_password),
                'snmp_version': obj.snmp_version,
                'has_snmp_community': bool(obj.credential._encrypted_snmp_community),
            }
        return None


class DeviceCreateUpdateSerializer(serializers.ModelSerializer):
    ssh_username = serializers.CharField(required=False, default='admin', write_only=True)
    ssh_password = serializers.CharField(required=False, allow_blank=True, write_only=True)
    snmp_community = serializers.CharField(required=False, allow_blank=True, default='public', write_only=True)

    class Meta:
        model = Device
        fields = [
            'id', 'hostname', 'ip_address', 'device_type', 'vendor', 'model', 'os_version',
            'location', 'ssh_port', 'snmp_version', 'snmp_port', 'monitoring_interval',
            'status', 'ssh_username', 'ssh_password', 'snmp_community'
        ]
        read_only_fields = ['id', 'status']

    def create(self, validated_data):
        ssh_user = validated_data.pop('ssh_username', 'admin')
        ssh_pass = validated_data.pop('ssh_password', '')
        snmp_comm = validated_data.pop('snmp_community', 'public')

        device = Device.objects.create(**validated_data)
        
        credential = DeviceCredential(device=device, ssh_username=ssh_user)
        if ssh_pass:
            credential.set_ssh_password(ssh_pass)
        if snmp_comm:
            credential.set_snmp_community(snmp_comm)
        credential.save()

        # Seed default interfaces
        DeviceInterface.objects.create(
            device=device,
            name='GigabitEthernet0/1',
            description='Uplink Interface',
            ip_address=device.ip_address,
            oper_status='UP',
            admin_status='UP',
            speed_mbps=1000
        )
        return device

    def update(self, instance, validated_data):
        ssh_user = validated_data.pop('ssh_username', None)
        ssh_pass = validated_data.pop('ssh_password', None)
        snmp_comm = validated_data.pop('snmp_community', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if hasattr(instance, 'credential'):
            credential = instance.credential
            if ssh_user is not None:
                credential.ssh_username = ssh_user
            if ssh_pass is not None and ssh_pass != '':
                credential.set_ssh_password(ssh_pass)
            if snmp_comm is not None and snmp_comm != '':
                credential.set_snmp_community(snmp_comm)
            credential.save()

        return instance
