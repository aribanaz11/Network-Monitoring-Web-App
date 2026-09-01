"""
NetWatch TCP Port Connectivity Engine
Performs non-blocking socket 3-way handshakes to verify service port availability,
measuring TCP connect latency and capturing connection diagnostics.
"""

import time
import socket
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime, timezone


@dataclass
class TCPPortResult:
    port: int
    is_open: bool
    response_time_ms: Optional[float]
    error_reason: str
    timestamp: str


@dataclass
class TCPDeviceScanResult:
    ip_address: str
    ports_scanned: int
    ports_open: int
    ports_closed: int
    results: List[TCPPortResult]
    scan_duration_ms: float


class TCPService:
    """
    Production-grade TCP Port connectivity diagnostic service.
    """

    COMMON_PORTS = [22, 80, 443, 161, 8080]

    @classmethod
    def check_port(cls, ip_address: str, port: int, timeout_sec: float = 2.0) -> TCPPortResult:
        """
        Tests TCP 3-way handshake on a specific host:port.
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout_sec)
        
        start_time = time.perf_counter()
        iso_timestamp = datetime.now(timezone.utc).isoformat()

        try:
            sock.connect((ip_address, port))
            latency_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
            sock.close()
            return TCPPortResult(
                port=port,
                is_open=True,
                response_time_ms=latency_ms,
                error_reason="",
                timestamp=iso_timestamp
            )
        except socket.timeout:
            return TCPPortResult(
                port=port,
                is_open=False,
                response_time_ms=None,
                error_reason="Connection timed out",
                timestamp=iso_timestamp
            )
        except ConnectionRefusedError:
            return TCPPortResult(
                port=port,
                is_open=False,
                response_time_ms=None,
                error_reason="Connection refused (port closed)",
                timestamp=iso_timestamp
            )
        except Exception as e:
            return TCPPortResult(
                port=port,
                is_open=False,
                response_time_ms=None,
                error_reason=str(e),
                timestamp=iso_timestamp
            )
        finally:
            try:
                sock.close()
            except Exception:
                pass

    @classmethod
    def scan_device_ports(
        cls,
        ip_address: str,
        ports: Optional[List[int]] = None,
        timeout_sec: float = 2.0
    ) -> TCPDeviceScanResult:
        """
        Scans multiple TCP ports on a target device IP.
        """
        target_ports = ports or cls.COMMON_PORTS
        results: List[TCPPortResult] = []
        scan_start = time.perf_counter()

        open_count = 0
        closed_count = 0

        for p in target_ports:
            res = cls.check_port(ip_address, p, timeout_sec=timeout_sec)
            results.append(res)
            if res.is_open:
                open_count += 1
            else:
                closed_count += 1

        duration_ms = round((time.perf_counter() - scan_start) * 1000.0, 2)

        return TCPDeviceScanResult(
            ip_address=ip_address,
            ports_scanned=len(target_ports),
            ports_open=open_count,
            ports_closed=closed_count,
            results=results,
            scan_duration_ms=duration_ms
        )
