import pytest
from apps.network_engine.icmp import ping_host, PingResult

class TestICMPEngine:
    def test_localhost_real_ping(self):
        result = ping_host('127.0.0.1', timeout_sec=2, count=2, force_real=True)
        assert isinstance(result, PingResult)
        assert result.host == '127.0.0.1'
        assert result.is_reachable is True
        assert result.packet_loss_percent == 0.0
        assert result.avg_latency_ms is not None
        assert result.avg_latency_ms >= 0.0

    def test_simulator_ping_responsive_host(self):
        result = ping_host('192.168.10.1', timeout_sec=2, count=3)
        assert isinstance(result, PingResult)
        assert result.host == '192.168.10.1'
        assert result.is_reachable is True
        assert result.packets_sent == 3
        assert result.packets_received == 3
        assert result.avg_latency_ms > 0.0
        assert result.jitter_ms is not None

    def test_simulator_ping_unreachable_host(self):
        # In simulator mode, IPs ending in 9 simulate offline devices
        result = ping_host('192.168.40.9', timeout_sec=2, count=3)
        assert isinstance(result, PingResult)
        assert result.is_reachable is False
        assert result.packet_loss_percent == 100.0
        assert result.packets_received == 0
