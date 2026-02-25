"""Tests for erpc.monitoring module."""

from erpc.client import HealthStatus
from erpc.monitoring import HealthEvent, HealthMonitor


class TestHealthEvent:
    def test_values(self):
        assert HealthEvent.HEALTHY.value == "healthy"
        assert HealthEvent.DEGRADED.value == "degraded"
        assert HealthEvent.DOWN.value == "down"
        assert HealthEvent.RECOVERED.value == "recovered"


class TestHealthMonitor:
    def test_defaults(self):
        m = HealthMonitor()
        assert m.url == "http://127.0.0.1:4000"
        assert m.interval == 30.0
        assert m.history == []

    def test_latest_event_empty(self):
        m = HealthMonitor()
        assert m.latest_event() is None

    def test_latest_event_healthy(self):
        m = HealthMonitor(history=[HealthStatus(status="ok", uptime=1.0, version="0.1")])
        assert m.latest_event() == HealthEvent.HEALTHY

    def test_latest_event_down(self):
        m = HealthMonitor(history=[HealthStatus(status="error", uptime=0.0, version="0.1")])
        assert m.latest_event() == HealthEvent.DOWN
