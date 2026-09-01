import os
import time
import re
import logging
from dataclasses import dataclass
from typing import Optional, List, Tuple
import paramiko
from apps.devices.models import Device, DeviceVendor

logger = logging.getLogger('netwatch.ssh')

@dataclass
class SSHExecutionResult:
    command: str
    is_successful: bool
    exit_status: int
    stdout: str
    stderr: str
    execution_duration_ms: float
    is_simulated: bool
    timestamp: float

# Safe whitelisted command prefixes for network devices & servers
WHITELISTED_COMMANDS = [
    'show ip interface brief',
    'show ip route',
    'show version',
    'show running-config',
    'show startup-config',
    'show interfaces',
    'show vlan',
    'show arp',
    'show inventory',
    'show environment',
    'show processes cpu',
    'show memory',
    'uname -a',
    'df -h',
    'uptime',
    'free -m',
    'ip a',
    'ip route',
    'netstat -tulpn',
    'cat /etc/os-release',
    'ps aux',
]

# Strict blacklist of destructive or dangerous commands
BLACKLISTED_PATTERNS = [
    r'rm\s+-rf',
    r'format\s+',
    r'erase\s+',
    r'reboot',
    r'shutdown',
    r'reload',
    r'init\s+0',
    r'init\s+6',
    r'drop\s+database',
    r'truncate\s+',
    r':\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:', # Fork bomb
    r'mkfs',
    r'dd\s+if='
]

class SSHAutomationEngine:
    """
    Enterprise SSH Automation Engine for Network Devices & Linux Servers.
    - Uses Paramiko for secure SSHv2 sessions.
    - Enforces strict command whitelisting and security sanitization.
    - Measures execution latency with millisecond precision.
    - Provides a built-in virtual device simulator for lab/demo environments.
    """

    @staticmethod
    def validate_command(command: str) -> Tuple[bool, Optional[str]]:
        """
        Validates if a command is safe to execute.
        Returns (is_valid, error_message).
        """
        clean_cmd = command.strip().lower()

        # Check blacklist
        for pattern in BLACKLISTED_PATTERNS:
            if re.search(pattern, clean_cmd):
                return False, f"Command rejected: matches destructive pattern '{pattern}'."

        # Verify command starts with approved whitelist prefix or standard operational prefix
        is_safe = False
        if clean_cmd.startswith('show ') or clean_cmd.startswith('display ') or clean_cmd in WHITELISTED_COMMANDS:
            is_safe = True
        elif any(clean_cmd.startswith(prefix) for prefix in ['cat ', 'uname', 'df ', 'uptime', 'free', 'ip ', 'netstat', 'ps ']):
            is_safe = True

        if not is_safe:
            return False, f"Command '{command}' is not in the approved operational whitelist."

        return True, None

    @classmethod
    def execute_command(cls, device: Device, command: str, timeout_sec: int = 10, force_real: bool = False) -> SSHExecutionResult:
        start_time = time.time()
        
        # 1. Security validation
        is_valid, err_msg = cls.validate_command(command)
        if not is_valid:
            duration = (time.time() - start_time) * 1000.0
            return SSHExecutionResult(
                command=command,
                is_successful=False,
                exit_status=403,
                stdout='',
                stderr=err_msg or 'Security validation failed.',
                execution_duration_ms=round(duration, 2),
                is_simulated=False,
                timestamp=start_time
            )

        # 2. Extract credentials safely
        ssh_user = 'admin'
        ssh_pass = ''
        if hasattr(device, 'credential') and device.credential:
            ssh_user = device.credential.ssh_username or 'admin'
            ssh_pass = device.credential.get_ssh_password()

        is_sim_mode = os.environ.get('SIMULATOR_MODE', 'True').lower() in ('true', '1', 't')

        # 3. Real SSH Execution via Paramiko
        if not is_sim_mode or force_real:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            try:
                client.connect(
                    hostname=device.ip_address,
                    port=device.ssh_port or 22,
                    username=ssh_user,
                    password=ssh_pass,
                    timeout=timeout_sec,
                    allow_agent=False,
                    look_for_keys=False
                )

                stdin, stdout, stderr = client.exec_command(command, timeout=timeout_sec)
                out = stdout.read().decode(errors='ignore')
                err = stderr.read().decode(errors='ignore')
                exit_code = stdout.channel.recv_exit_status()
                client.close()

                duration = (time.time() - start_time) * 1000.0
                return SSHExecutionResult(
                    command=command,
                    is_successful=(exit_code == 0),
                    exit_status=exit_code,
                    stdout=out,
                    stderr=err,
                    execution_duration_ms=round(duration, 2),
                    is_simulated=False,
                    timestamp=start_time
                )
            except Exception as e:
                logger.warning(f"Real SSH connection to {device.ip_address} failed: {str(e)}")
                if force_real or not is_sim_mode:
                    duration = (time.time() - start_time) * 1000.0
                    return SSHExecutionResult(
                        command=command,
                        is_successful=False,
                        exit_status=500,
                        stdout='',
                        stderr=f"SSH Connection Error: {str(e)}",
                        execution_duration_ms=round(duration, 2),
                        is_simulated=False,
                        timestamp=start_time
                    )

        # 4. Realistic Virtual SSH Device Simulator
        sim_out = cls._simulate_device_output(device, command)
        duration = (time.time() - start_time) * 1000.0 + 45.0 # realistic simulated processing time
        return SSHExecutionResult(
            command=command,
            is_successful=True,
            exit_status=0,
            stdout=sim_out,
            stderr='',
            execution_duration_ms=round(duration, 2),
            is_simulated=True,
            timestamp=start_time
        )

    @classmethod
    def _simulate_device_output(cls, device: Device, command: str) -> str:
        cmd = command.strip().lower()
        hostname = device.hostname
        ip = device.ip_address

        if 'show ip interface brief' in cmd:
            return f"""{hostname}# show ip interface brief
Interface                  IP-Address      OK? Method Status                Protocol
TenGigE0/0/0/0             {ip}    YES manual up                    up      
GigabitEthernet0/0/0/1     10.0.1.1        YES manual up                    up      
Loopback0                  192.168.254.1   YES manual up                    up      
Management0                10.254.1.10     YES manual up                    up      
"""
        elif 'show version' in cmd:
            return f"""{hostname}# show version
Cisco IOS-XR Software, Version 7.3.2[Default]
Copyright (c) 2026 by Cisco Systems, Inc.
System image file is "bootflash:packages.conf"
cisco ASR9K Series (Intel(R) Xeon(R) CPU E5-2600 v4 @ 2.40GHz) with 33554432K bytes of memory.
Uptime is 42 weeks, 3 days, 14 hours, 28 minutes
Configuration register is 0x2102
"""
        elif 'show running-config' in cmd:
            return f"""{hostname}# show running-config
! Building configuration...
! Current configuration : 2480 bytes
version 7.3.2
service timestamps debug datetime msec
service timestamps log datetime msec
no service password-encryption
!
hostname {hostname}
!
interface TenGigE0/0/0/0
 description Primary Uplink to Core DC
 ipv4 address {ip} 255.255.255.0
 no shutdown
!
interface GigabitEthernet0/0/0/1
 description Internal Distribution Trunk
 ipv4 address 10.0.1.1 255.255.255.0
 no shutdown
!
router bgp 65000
 bgp router-id {ip}
 neighbor 10.0.1.2 remote-as 65001
!
snmp-server community netwatch_ro RO
snmp-server enable traps
!
end
"""
        elif 'uname -a' in cmd or 'cat /etc/os-release' in cmd:
            return f"""Linux {hostname} 6.8.0-45-generic #45-Ubuntu SMP PREEMPT_DYNAMIC x86_64 x86_64 x86_64 GNU/Linux
PRETTY_NAME="Ubuntu 24.04 LTS"
NAME="Ubuntu"
VERSION_ID="24.04"
VERSION="24.04 LTS (Noble Numbat)"
"""
        elif 'df -h' in cmd:
            return f"""Filesystem      Size  Used Avail Use% Mounted on
/dev/sda1        98G   24G   70G  26% /
tmpfs           7.8G     0  7.8G   0% /dev/shm
/dev/sda2       450M   85M  335M  21% /boot
"""
        elif 'uptime' in cmd:
            return f""" 09:30:15 up 85 days, 14:22,  2 users,  load average: 0.14, 0.22, 0.18"""
        else:
            return f"""{hostname}# {command}\nCommand executed successfully on {hostname} [{device.vendor} / {device.os_version}].\n"""
