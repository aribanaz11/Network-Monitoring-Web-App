import socket
import time
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger('netwatch.tcp')

@dataclass
class TCPCheckResult:
    host: str
    port: int
    is_open: bool
    latency_ms: Optional[float]
    banner: Optional[str]
    error_message: Optional[str]
    timestamp: float

def check_tcp_port(host: str, port: int, timeout_sec: float = 3.0) -> TCPCheckResult:
    """
    Performs a TCP 3-way handshake to verify if a remote port is open and accepting connections.
    Attempts to read banner string if available (e.g. SSH-2.0-OpenSSH...).
    """
    start_time = time.time()
    banner = None
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout_sec)

    try:
        sock.connect((host, int(port)))
        latency = (time.time() - start_time) * 1000.0

        # Try to capture banner if it emits greeting
        try:
            sock.settimeout(0.5)
            data = sock.recv(1024)
            if data:
                banner = data.decode(errors='ignore').strip()
        except Exception:
            pass

        sock.close()
        return TCPCheckResult(
            host=host,
            port=port,
            is_open=True,
            latency_ms=round(latency, 2),
            banner=banner,
            error_message=None,
            timestamp=start_time
        )
    except socket.timeout:
        return TCPCheckResult(
            host=host,
            port=port,
            is_open=False,
            latency_ms=None,
            banner=None,
            error_message=f"Connection timed out after {timeout_sec}s",
            timestamp=start_time
        )
    except ConnectionRefusedError:
        return TCPCheckResult(
            host=host,
            port=port,
            is_open=False,
            latency_ms=None,
            banner=None,
            error_message="Connection actively refused (Port closed)",
            timestamp=start_time
        )
    except Exception as e:
        return TCPCheckResult(
            host=host,
            port=port,
            is_open=False,
            latency_ms=None,
            banner=None,
            error_message=str(e),
            timestamp=start_time
        )
    finally:
        try:
            sock.close()
        except Exception:
            pass
