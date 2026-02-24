"""eRPC configuration generation and loading."""

from __future__ import annotations

import tempfile
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from erpc.exceptions import ERPCConfigError


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
        server_host: eRPC server bind address.
        server_port: eRPC server listen port.
        metrics_host: Metrics endpoint bind address.
        metrics_port: Metrics endpoint listen port.
        log_level: Logging verbosity (trace, debug, info, warn, error).
        cache: Memory cache configuration.

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

        # Parse upstreams from networks
        upstreams: dict[int, list[str]] = {}
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
            server_host=server.get("httpHost", "127.0.0.1"),
            server_port=server.get("httpPort", 4000),
            metrics_host=metrics.get("host", "127.0.0.1"),
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
    def health_url(self) -> str:
        """HTTP URL for the eRPC health endpoint."""
        return f"http://{self.server_host}:{self.server_port}/"

    def endpoint_url(self, chain_id: int) -> str:
        """Get the proxied endpoint URL for a specific chain.

        Args:
            chain_id: EVM chain identifier.

        Returns:
            Full URL for the proxied RPC endpoint.

        """
        return f"http://{self.server_host}:{self.server_port}/{self.project_id}/evm/{chain_id}"

    def to_yaml(self) -> str:
        """Generate eRPC YAML configuration string.

        Returns:
            YAML-formatted configuration document.

        """
        doc: dict[str, Any] = {
            "logLevel": self.log_level,
            "server": {
                "httpHost": self.server_host,
                "httpPort": self.server_port,
                "maxTimeout": "60s",
            },
            "metrics": {
                "enabled": True,
                "host": self.metrics_host,
                "port": self.metrics_port,
            },
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

        if self.cache.max_items > 0:
            project["cacheConfig"] = {
                "connectors": [
                    {
                        "id": "memory-cache",
                        "driver": "memory",
                        "memory": {"maxItems": self.cache.max_items},
                    }
                ]
            }

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
