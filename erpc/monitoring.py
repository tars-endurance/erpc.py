"""Health monitoring for eRPC upstream endpoints."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field

from erpc.client import HealthStatus


class HealthEvent(enum.Enum):
    """Events emitted by the health monitor."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"
    RECOVERED = "recovered"


@dataclass
class HealthMonitor:
    """Monitors health of eRPC upstream endpoints.

    Attributes:
        url: Base URL of the eRPC instance to monitor.
        interval: Polling interval in seconds.
        history: Recent health check results.

    """

    url: str = "http://127.0.0.1:4000"
    interval: float = 30.0
    history: list[HealthStatus] = field(default_factory=list)

    def latest_event(self) -> HealthEvent | None:
        """Return the latest health event based on history, or ``None``."""
        if not self.history:
            return None
        last = self.history[-1]
        if last.status == "ok":
            return HealthEvent.HEALTHY
        return HealthEvent.DOWN


__all__ = ["HealthEvent", "HealthMonitor", "HealthStatus"]
