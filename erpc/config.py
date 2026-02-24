"""eRPC configuration generation."""

from __future__ import annotations

import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from erpc.auth import AuthConfig
    from erpc.database import DatabaseConfig

from erpc.server import MetricsConfig, ServerConfig


@dataclass
class CacheConfig:
    """Memory cache configuration for eRPC.

    Attributes:
        max_items: Maximum number of items to store in memory cache.
        method_ttls: Per-method TTL overrides in seconds. Use ``0`` to disable caching.

    """

    max_items: int = 10_000
    method_ttls: dict[str, int] = field(default_factory=dict)


@dataclass
class ERPCConfig:
    """eRPC configuration builder.

    Generates an ``erpc.yaml`` config file from Python dataclasses.

    Args:
        project_id: Unique project identifier for eRPC routing.
        upstreams: Mapping of chain ID to list of RPC endpoint URLs.
        server_host: eRPC server bind address (legacy, use ``server`` instead).
        server_port: eRPC server listen port (legacy, use ``server`` instead).
        metrics_host: Metrics endpoint bind address (legacy, use ``metrics`` instead).
        metrics_port: Metrics endpoint listen port (legacy, use ``metrics`` instead).
        log_level: Logging verbosity (trace, debug, info, warn, error).
        cache: Memory cache configuration.
        server: Full server configuration. Takes precedence over ``server_host``/``server_port``.
        metrics: Full metrics configuration. Takes precedence over
            ``metrics_host``/``metrics_port``.

    Examples:
        >>> config = ERPCConfig(upstreams={1: ["https://eth.llamarpc.com"]})
        >>> config.endpoint_url(1)
        'http://127.0.0.1:4000/py-erpc/evm/1'

    """

    project_id: str = "py-erpc"
    upstreams: dict[int, list[str]] = field(default_factory=dict)
    server_host: str = "127.0.0.1"
    server_port: int = 4000
    metrics_host: str = "127.0.0.1"
    metrics_port: int = 4001
    log_level: str = "warn"
    cache: CacheConfig = field(default_factory=CacheConfig)
    server: ServerConfig | None = None
    metrics: MetricsConfig | None = None
    auth: AuthConfig | None = None
    database: DatabaseConfig | None = None

    @property
    def _effective_host(self) -> str:
        """Resolve the effective server host."""
        if self.server is not None:
            return self.server.http_host
        return self.server_host

    @property
    def _effective_port(self) -> int:
        """Resolve the effective server port."""
        if self.server is not None:
            return self.server.http_port
        return self.server_port

    @property
    def health_url(self) -> str:
        """HTTP URL for the eRPC health endpoint."""
        return f"http://{self._effective_host}:{self._effective_port}/"

    def endpoint_url(self, chain_id: int) -> str:
        """Get the proxied endpoint URL for a specific chain.

        Args:
            chain_id: EVM chain identifier.

        Returns:
            Full URL for the proxied RPC endpoint.

        """
        return (
            f"http://{self._effective_host}:{self._effective_port}"
            f"/{self.project_id}/evm/{chain_id}"
        )

    def to_yaml(self) -> str:
        """Generate eRPC YAML configuration string.

        Returns:
            YAML-formatted configuration document.

        """
        if self.server is not None:
            server_dict = self.server.to_dict()
        else:
            server_dict = {
                "httpHost": self.server_host,
                "httpPort": self.server_port,
                "maxTimeout": "60s",
            }

        if self.metrics is not None:
            metrics_dict = self.metrics.to_dict()
        else:
            metrics_dict = {
                "enabled": True,
                "host": self.metrics_host,
                "port": self.metrics_port,
            }

        doc: dict[str, Any] = {
            "logLevel": self.log_level,
            "server": server_dict,
            "metrics": metrics_dict,
            "projects": [self._build_project()],
        }
        return yaml.dump(doc, default_flow_style=False, sort_keys=False)

    def write(self, path: Path | None = None) -> Path:
        """Write config to a YAML file.

        Args:
            path: Destination file path. If ``None``, writes to a temporary file.

        Returns:
            Path to the written configuration file.

        """
        if path is None:
            fd = tempfile.NamedTemporaryFile(
                mode="w", suffix=".yaml", prefix="erpc-", delete=False
            )
            fd.write(self.to_yaml())
            fd.close()
            return Path(fd.name)
        else:
            path = Path(path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(self.to_yaml())
            return path

    def _build_project(self) -> dict[str, Any]:
        """Build a single eRPC project definition."""
        networks: list[dict[str, Any]] = []
        for chain_id, endpoints in self.upstreams.items():
            upstreams: list[dict[str, str]] = []
            for i, url in enumerate(endpoints):
                upstreams.append(
                    {
                        "endpoint": url,
                        "id": f"upstream-{chain_id}-{i}",
                    }
                )
            network: dict[str, Any] = {
                "architecture": "evm",
                "evm": {"chainId": chain_id},
                "upstreams": upstreams,
            }

            if self.cache.method_ttls:
                network["policies"] = self._build_cache_policies()

            networks.append(network)

        project: dict[str, Any] = {
            "id": self.project_id,
            "networks": networks,
        }

        if self.database is not None:
            project["database"] = self.database.to_dict()
        elif self.cache.max_items > 0:
            project["cacheConfig"] = {
                "connectors": [
                    {
                        "id": "memory-cache",
                        "driver": "memory",
                        "memory": {"maxItems": self.cache.max_items},
                    }
                ]
            }

        if self.auth is not None:
            project["auth"] = self.auth.to_dict()

        return project

    def _build_cache_policies(self) -> list[dict[str, Any]]:
        """Build cache policy rules from method TTL overrides."""
        policies: list[dict[str, Any]] = []
        for method, ttl in self.cache.method_ttls.items():
            if ttl == 0:
                policies.append(
                    {
                        "method": method,
                        "finality": "unfinalized",
                        "cache": {"empty": "skip", "ttl": "0s"},
                    }
                )
            else:
                policies.append(
                    {
                        "method": method,
                        "finality": "unfinalized",
                        "cache": {"ttl": f"{ttl}s"},
                    }
                )
        return policies
