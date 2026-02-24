"""erpc.py — Python subprocess manager for eRPC."""

from erpc.config import CacheConfig, ERPCConfig
from erpc.docker import DockerERPCProcess
from erpc.exceptions import (
    ERPCError,
    ERPCHealthCheckError,
    ERPCNotFound,
    ERPCNotRunning,
    ERPCStartupError,
)
from erpc.process import ERPCProcess

__all__ = [
    "CacheConfig",
    "DockerERPCProcess",
    "ERPCConfig",
    "ERPCError",
    "ERPCHealthCheckError",
    "ERPCNotFound",
    "ERPCNotRunning",
    "ERPCProcess",
    "ERPCStartupError",
]

__version__ = "0.1.0"
