"""eRPC server, metrics, and CORS configuration dataclasses.

Maps the eRPC server configuration surface to Python dataclasses,
matching the Go ``ServerConfig``, ``MetricsConfig``, and ``CORSConfig``
structs from ``erpc/common/config.go``.

Examples:
    >>> from erpc.server import ServerConfig, MetricsConfig, CORSConfig
    >>> server = ServerConfig(http_host="0.0.0.0", http_port=8080)
    >>> server.to_dict()
    {'httpHostV4': '0.0.0.0', 'httpPort': 8080, 'maxTimeout': '60s'}

"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CORSConfig:
    """Cross-Origin Resource Sharing configuration for the eRPC server.

    When all fields are at their defaults (empty lists, ``False``, ``0``),
    CORS is effectively disabled and ``to_dict()`` returns an empty dict
    so no ``cors`` key appears in the generated YAML.

    Attributes:
        allowed_origins: Origins permitted to make cross-origin requests.
        allowed_methods: HTTP methods allowed in cross-origin requests.
        allowed_headers: HTTP headers allowed in cross-origin requests.
        allow_credentials: Whether credentials (cookies, auth) are allowed.
        max_age: How long (seconds) browsers should cache preflight responses.

    Examples:
        >>> cors = CORSConfig(allowed_origins=["*"])
        >>> cors.to_dict()
        {'allowedOrigins': ['*']}

    """

    allowed_origins: list[str] = field(default_factory=list)
    allowed_methods: list[str] = field(default_factory=list)
    allowed_headers: list[str] = field(default_factory=list)
    allow_credentials: bool = False
    max_age: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to an eRPC-compatible dictionary.

        Returns:
            Dictionary with camelCase keys. Returns empty dict when all
            values are at their defaults (CORS disabled).

        """
        if not any(
            [
                self.allowed_origins,
                self.allowed_methods,
                self.allowed_headers,
                self.allow_credentials,
                self.max_age,
            ]
        ):
            return {}

        d: dict[str, Any] = {}
        if self.allowed_origins:
            d["allowedOrigins"] = self.allowed_origins
        if self.allowed_methods:
            d["allowedMethods"] = self.allowed_methods
        if self.allowed_headers:
            d["allowedHeaders"] = self.allowed_headers
        if self.allow_credentials:
            d["allowCredentials"] = self.allow_credentials
        if self.max_age:
            d["maxAge"] = self.max_age
        return d


@dataclass
class ServerConfig:
    """eRPC HTTP server configuration.

    Maps to the ``server`` section of the eRPC YAML config.

    Attributes:
        http_host: Bind address for the HTTP server.
        http_port: Listen port for the HTTP server.
        max_timeout: Maximum request timeout (e.g. ``"60s"``).
        enable_gzip: Enable gzip compression for responses.
        listen_v6: Enable IPv6 listening.
        cors: Cross-origin resource sharing configuration.

    Examples:
        >>> server = ServerConfig(http_host="0.0.0.0", http_port=8080)
        >>> server.to_dict()["httpHostV4"]
        '0.0.0.0'

    """

    http_host: str = "127.0.0.1"
    http_port: int = 4000
    max_timeout: str = "60s"
    enable_gzip: bool = False
    listen_v6: bool = False
    cors: CORSConfig = field(default_factory=CORSConfig)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to an eRPC-compatible dictionary.

        Returns:
            Dictionary with camelCase keys. Boolean fields that are
            ``False`` by default are omitted to keep the config minimal.

        """
        d: dict[str, Any] = {
            "httpHostV4": self.http_host,
            "httpPort": self.http_port,
            "maxTimeout": self.max_timeout,
        }
        if self.enable_gzip:
            d["enableGzip"] = self.enable_gzip
        if self.listen_v6:
            d["listenV6"] = self.listen_v6
        cors_dict = self.cors.to_dict()
        if cors_dict:
            d["cors"] = cors_dict
        return d


@dataclass
class MetricsConfig:
    """eRPC metrics / Prometheus endpoint configuration.

    Maps to the ``metrics`` section of the eRPC YAML config.

    Attributes:
        enabled: Whether the metrics endpoint is active.
        host: Bind address for the metrics HTTP server.
        port: Listen port for the metrics HTTP server.

    Examples:
        >>> metrics = MetricsConfig(enabled=True, host="0.0.0.0", port=9090)
        >>> metrics.to_dict()
        {'enabled': True, 'host': '0.0.0.0', 'port': 9090}

    """

    enabled: bool = True
    host: str = "127.0.0.1"
    port: int = 4001

    def to_dict(self) -> dict[str, Any]:
        """Serialize to an eRPC-compatible dictionary.

        Returns:
            Dictionary with metrics configuration. When disabled, only
            ``{"enabled": False}`` is returned.

        """
        if not self.enabled:
            return {"enabled": False}
        return {
            "enabled": self.enabled,
            "host": self.host,
            "port": self.port,
        }
