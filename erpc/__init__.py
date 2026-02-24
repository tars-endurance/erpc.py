"""erpc.py — Python subprocess manager for eRPC."""

from erpc.auth import AuthConfig, JWTAuth, NetworkAuth, SecretAuth, SIWEAuth
from erpc.config import CacheConfig, ERPCConfig
from erpc.server import CORSConfig, MetricsConfig, ServerConfig
from erpc.exceptions import (
    ERPCError,
    ERPCHealthCheckError,
    ERPCNotFound,
    ERPCNotRunning,
    ERPCStartupError,
)
from erpc.process import ERPCProcess

__all__ = [
    "AuthConfig",
    "CORSConfig",
    "CacheConfig",
    "ERPCConfig",
    "JWTAuth",
    "MetricsConfig",
    "NetworkAuth",
    "SecretAuth",
    "SIWEAuth",
    "ServerConfig",
    "ERPCError",
    "ERPCHealthCheckError",
    "ERPCNotFound",
    "ERPCNotRunning",
    "ERPCProcess",
    "ERPCStartupError",
]

__version__ = "0.1.0"
