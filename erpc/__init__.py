"""erpc.py — Python subprocess manager for eRPC."""

from erpc.config import CacheConfig, ERPCConfig
from erpc.exceptions import (
    ERPCError,
    ERPCHealthCheckError,
    ERPCNotFound,
    ERPCNotRunning,
    ERPCStartupError,
)
from erpc.monitoring import HealthEvent, HealthMonitor, HealthStatus
from erpc.process import ERPCProcess

__all__ = [
    "CacheConfig",
    "ERPCConfig",
    "ERPCError",
    "ERPCHealthCheckError",
    "ERPCNotFound",
    "ERPCNotRunning",
    "ERPCProcess",
    "ERPCStartupError",
    "HealthEvent",
    "HealthMonitor",
    "HealthStatus",
]

__version__ = "0.1.0"
