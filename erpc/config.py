"""eRPC configuration generation."""

from __future__ import annotations

import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class CacheConfig:
    """Memory cache configuration."""

    max_items: int = 10_000
    method_ttls: dict[str, int] = field(default_factory=dict)


@dataclass
class ERPCConfig:
    """eRPC configuration.

    Generates an erpc.yaml config file from Python dataclasses.

    Args:
        project_id: Unique project identifier for eRPC routing.
        upstreams: Mapping of chain ID → list of RPC endpoint URLs.
        server_host: eRPC server bind address.
        server_port: eRPC server listen port.
        metrics_host: Metrics endpoint bind address.
        metrics_port: Metrics endpoint listen port.
        log_level: Logging verbosity (trace, debug, info, warn, error).
        cache: Memory cache configuration.
    """

    project_id: str = "py-erpc"
    upstreams: dict[int, list[str]] = field(default_factory=dict)
    server_host: str = "127.0.0.1"
    server_port: int = 4000
    metrics_host: str = "127.0.0.1"
    metrics_port: int = 4001
    log_level: str = "warn"
    cache: CacheConfig = field(default_factory=CacheConfig)

    @property
    def health_url(self) -> str:
        return f"http://{self.server_host}:{self.server_port}/"

    def endpoint_url(self, chain_id: int) -> str:
        """Get the proxied endpoint URL for a specific chain."""
        return f"http://{self.server_host}:{self.server_port}/{self.project_id}/evm/{chain_id}"

    def to_yaml(self) -> str:
        """Generate eRPC YAML configuration."""
        doc = {
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

    def write(self, path: Optional[Path] = None) -> Path:
        """Write config to a YAML file. Returns the path.

        If no path is given, writes to a temporary file.
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

    def _build_project(self) -> dict:
        """Build a single eRPC project definition."""
        networks = []
        for chain_id, endpoints in self.upstreams.items():
            upstreams = []
            for i, url in enumerate(endpoints):
                upstreams.append(
                    {
                        "endpoint": url,
                        "id": f"upstream-{chain_id}-{i}",
                    }
                )
            network = {
                "architecture": "evm",
                "evm": {"chainId": chain_id},
                "upstreams": upstreams,
            }

            # Apply method-level cache TTLs if configured
            if self.cache.method_ttls:
                network["policies"] = self._build_cache_policies()

            networks.append(network)

        project = {
            "id": self.project_id,
            "networks": networks,
        }

        # Global cache config
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

    def _build_cache_policies(self) -> list[dict]:
        """Build cache policy rules from method TTL overrides."""
        policies = []
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
