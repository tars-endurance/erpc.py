"""eRPC configuration generation and loading."""

from __future__ import annotations

import tempfile
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

from erpc.exceptions import ERPCConfigError

if TYPE_CHECKING:
    from erpc.auth import AuthConfig
    from erpc.networks import NetworkConfig
    from erpc.providers import Provider
    from erpc.server import MetricsConfig, ServerConfig
    from erpc.upstreams import UpstreamConfig

from erpc.database import CachePolicy, DatabaseConfig, MemoryConnector


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
        upstream_defaults: Default configuration applied to all upstreams.
        rich_upstreams: List of fully-configured UpstreamConfig objects.

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
    providers: list[Provider] = field(default_factory=list)
    server: ServerConfig | None = None
    metrics: MetricsConfig | None = None
    auth: AuthConfig | None = None
    database: DatabaseConfig | None = None  # explicit database config overrides auto-generation
    networks: list[NetworkConfig] = field(default_factory=list)
    network_defaults: NetworkConfig | None = None
    upstream_defaults: UpstreamConfig | None = None
    rich_upstreams: list[UpstreamConfig] = field(default_factory=list)

    @classmethod
    def from_yaml(cls, path: str | Path) -> ERPCConfig:
        """Load an ERPCConfig from an existing erpc.yaml file.

        Args:
            path: Path to the YAML configuration file.

        Returns:
            Parsed configuration object.

        Raises:
            FileNotFoundError: If the file does not exist.
            ERPCConfigError: If the YAML is malformed or missing required keys.

        Examples:
            >>> config = ERPCConfig.from_yaml("erpc.yaml")
            >>> config.project_id
            'my-project'

        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        try:
            data = yaml.safe_load(path.read_text())
        except yaml.YAMLError as exc:
            raise ERPCConfigError(f"Invalid YAML in {path}: {exc}") from exc
        if not isinstance(data, dict):
            raise ERPCConfigError(f"Expected YAML mapping, got {type(data).__name__}")
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ERPCConfig:
        """Construct an ERPCConfig from a plain dictionary.

        Args:
            data: Dictionary matching the eRPC YAML schema.

        Returns:
            Parsed configuration object.

        Raises:
            ERPCConfigError: If the dictionary is missing required keys.

        Examples:
            >>> config = ERPCConfig.from_dict({"projects": [{"id": "x", "networks": []}]})
            >>> config.project_id
            'x'

        """
        if "projects" not in data or not data["projects"]:
            raise ERPCConfigError("Config must contain a non-empty 'projects' list")

        project = data["projects"][0]
        server = data.get("server", {})
        metrics = data.get("metrics", {})

        # Parse upstreams from project-level upstreams list
        upstreams: dict[int, list[str]] = {}
        for upstream in project.get("upstreams", []):
            evm = upstream.get("evm", {})
            chain_id = evm.get("chainId")
            if chain_id is not None:
                upstreams.setdefault(chain_id, []).append(upstream["endpoint"])

        # Fallback: parse upstreams from networks (legacy format)
        if not upstreams:
            for network in project.get("networks", []):
                evm = network.get("evm", {})
                chain_id = evm.get("chainId")
                if chain_id is not None:
                    endpoints = [u["endpoint"] for u in network.get("upstreams", [])]
                    upstreams[chain_id] = endpoints

        # Parse cache config
        cache_config = CacheConfig()
        cache_data = project.get("cacheConfig", {})
        connectors = cache_data.get("connectors", [])
        if connectors:
            memory = connectors[0].get("memory", {})
            max_items = memory.get("maxItems", 10_000)
            cache_config = CacheConfig(max_items=max_items)

        return cls(
            project_id=project.get("id", "py-erpc"),
            upstreams=upstreams,
            server_host=server.get("httpHostV4", server.get("httpHost", "127.0.0.1")),
            server_port=server.get("httpPort", 4000),
            metrics_host=metrics.get("hostV4", metrics.get("host", "127.0.0.1")),
            metrics_port=metrics.get("port", 4001),
            log_level=data.get("logLevel", "warn"),
            cache=cache_config,
        )

    def validate(self) -> None:
        """Validate this configuration, raising on errors and warning on issues.

        Raises:
            ERPCConfigError: If the configuration is invalid.

        Examples:
            >>> config = ERPCConfig(upstreams={1: ["https://rpc.example.com"]})
            >>> config.validate()  # no error

        """
        if not self.upstreams:
            warnings.warn(
                "No upstreams configured — eRPC will have no RPC endpoints to proxy",
                UserWarning,
                stacklevel=2,
            )

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
                "httpHostV4": self.server_host,
                "httpPort": self.server_port,
                "maxTimeout": "60s",
            }

        if self.metrics is not None:
            metrics_dict = self.metrics.to_dict()
        else:
            metrics_dict = {
                "enabled": True,
                "hostV4": self.metrics_host,
                "port": self.metrics_port,
            }

        doc: dict[str, Any] = {
            "logLevel": self.log_level,
            "server": server_dict,
            "metrics": metrics_dict,
            "projects": [self._build_project()],
        }

        db_config = self._resolve_database()
        if db_config is not None:
            doc["database"] = {"evmJsonRpcCache": db_config.to_dict()}

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
        # Index explicit NetworkConfig objects by chain_id
        net_configs: dict[int, NetworkConfig] = {n.chain_id: n for n in self.networks}

        networks: list[dict[str, Any]] = []
        all_upstreams: list[dict[str, Any]] = []

        for chain_id, endpoints in self.upstreams.items():
            for i, url in enumerate(endpoints):
                all_upstreams.append(
                    {
                        "endpoint": url,
                        "id": f"upstream-{chain_id}-{i}",
                        "evm": {"chainId": chain_id},
                    }
                )

            # Use explicit NetworkConfig if provided, otherwise minimal
            if chain_id in net_configs:
                network: dict[str, Any] = net_configs[chain_id].to_dict()
            else:
                network = {
                    "architecture": "evm",
                    "evm": {"chainId": chain_id},
                }

            networks.append(network)

        project: dict[str, Any] = {
            "id": self.project_id,
            "networks": networks,
            "upstreams": all_upstreams,
        }

        if self.upstream_defaults is not None:
            project["upstreamDefaults"] = self.upstream_defaults.to_dict()

        if self.rich_upstreams:
            project["upstreams"].extend(ru.to_dict() for ru in self.rich_upstreams)

        if self.network_defaults is not None:
            project["networkDefaults"] = self.network_defaults.to_defaults_dict()

        if self.providers:
            project["providers"] = [p.to_dict() for p in self.providers]

        if self.auth is not None:
            project["auth"] = self.auth.to_dict()

        return project

    def _resolve_database(self) -> DatabaseConfig | None:
        """Resolve the effective database config.

        Returns the explicit ``database`` if set, otherwise auto-generates
        one from ``CacheConfig.method_ttls``.
        """
        if self.database is not None:
            return self.database

        if not self.cache.method_ttls:
            return None

        connector = MemoryConnector(id="memory-cache", max_items=self.cache.max_items)

        # Default policies: finalized=0 (no cache), unfinalized=5s
        policies: list[CachePolicy] = [
            CachePolicy(
                connector="memory-cache",
                ttl="0",
                network="*",
                method="*",
                finality="finalized",
            ),
            CachePolicy(
                connector="memory-cache",
                ttl="5s",
                network="*",
                method="*",
                finality="unfinalized",
            ),
        ]

        # Per-method overrides
        for method, ttl in self.cache.method_ttls.items():
            policies.append(
                CachePolicy(
                    connector="memory-cache",
                    ttl=f"{ttl}s",
                    network="*",
                    method=method,
                    finality="unfinalized",
                )
            )

        return DatabaseConfig(connectors=[connector], policies=policies)
