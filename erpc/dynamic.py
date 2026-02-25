"""Dynamic configuration updates for eRPC processes.

Supports runtime config changes via stop -> rewrite -> start cycle,
since eRPC does not support SIGHUP-based config reload natively.

Examples:
    Update the full config::

        from erpc.dynamic import update_config

        diff = update_config(process, new_config)
        print(diff)

    Hot-add an upstream::

        from erpc.dynamic import add_upstream

        add_upstream(process, chain_id=137, endpoint="https://polygon.llamarpc.com")

"""

from __future__ import annotations

import contextlib
import os
import tempfile
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from erpc.exceptions import ERPCNotRunning

if TYPE_CHECKING:
    from erpc.config import ERPCConfig
    from erpc.process import ERPCProcess

_SCALAR_FIELDS = (
    "project_id",
    "server_host",
    "server_port",
    "metrics_host",
    "metrics_port",
    "log_level",
)


@dataclass
class ConfigDiff:
    """Tracks what changed between two eRPC configurations.

    Attributes:
        added_upstreams: Chain IDs and their endpoints that were added entirely.
        removed_upstreams: Chain IDs and their endpoints that were removed entirely.
        added_endpoints: New endpoints added to existing chains.
        removed_endpoints: Endpoints removed from existing chains.
        changed_fields: List of scalar field names that changed.

    Examples:
        >>> diff = ConfigDiff(added_upstreams={137: ["https://polygon.example.com"]})
        >>> diff.has_changes
        True

    """

    added_upstreams: dict[int, list[str]] = field(default_factory=dict)
    removed_upstreams: dict[int, list[str]] = field(default_factory=dict)
    added_endpoints: dict[int, list[str]] = field(default_factory=dict)
    removed_endpoints: dict[int, list[str]] = field(default_factory=dict)
    changed_fields: list[str] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        """Whether any differences were detected.

        Returns:
            ``True`` if at least one field differs between configs.

        """
        return bool(
            self.added_upstreams
            or self.removed_upstreams
            or self.added_endpoints
            or self.removed_endpoints
            or self.changed_fields
        )

    def __str__(self) -> str:
        """Human-readable summary of config changes.

        Returns:
            Multi-line string describing all detected changes.

        """
        parts: list[str] = []
        if self.added_upstreams:
            chains = ", ".join(str(c) for c in self.added_upstreams)
            parts.append(f"Added chains: {chains}")
        if self.removed_upstreams:
            chains = ", ".join(str(c) for c in self.removed_upstreams)
            parts.append(f"Removed chains: {chains}")
        if self.added_endpoints:
            for chain_id, eps in self.added_endpoints.items():
                parts.append(f"Added endpoints on chain {chain_id}: {eps}")
        if self.removed_endpoints:
            for chain_id, eps in self.removed_endpoints.items():
                parts.append(f"Removed endpoints on chain {chain_id}: {eps}")
        if self.changed_fields:
            joined = ", ".join(self.changed_fields)
            parts.append(f"Changed fields: {joined}")
        return "\n".join(parts) if parts else "No changes"


def _diff_configs(old: ERPCConfig, new: ERPCConfig) -> ConfigDiff:
    """Compare two ERPCConfig instances and return a ConfigDiff.

    Args:
        old: The original configuration.
        new: The updated configuration.

    Returns:
        A ConfigDiff describing all differences.

    """
    diff = ConfigDiff()

    old_chains = set(old.upstreams.keys())
    new_chains = set(new.upstreams.keys())

    for chain_id in new_chains - old_chains:
        diff.added_upstreams[chain_id] = list(new.upstreams[chain_id])
    for chain_id in old_chains - new_chains:
        diff.removed_upstreams[chain_id] = list(old.upstreams[chain_id])

    for chain_id in old_chains & new_chains:
        old_eps = set(old.upstreams[chain_id])
        new_eps = set(new.upstreams[chain_id])
        added = new_eps - old_eps
        removed = old_eps - new_eps
        if added:
            diff.added_endpoints[chain_id] = sorted(added)
        if removed:
            diff.removed_endpoints[chain_id] = sorted(removed)

    for field_name in _SCALAR_FIELDS:
        if getattr(old, field_name) != getattr(new, field_name):
            diff.changed_fields.append(field_name)

    return diff


def atomic_write_config(config: ERPCConfig, path: Path) -> Path:
    """Write config to a file atomically (write to temp, then rename).

    Args:
        config: The eRPC configuration to write.
        path: Target file path.

    Returns:
        The path the config was written to.

    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(
        suffix=".yaml",
        prefix=".erpc-tmp-",
        dir=str(path.parent),
    )
    try:
        with os.fdopen(fd, "w") as f:
            f.write(config.to_yaml())
        os.replace(tmp_path, str(path))
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)
        raise

    return path


def _clone_config_with_upstreams(
    source: ERPCConfig, new_upstreams: dict[int, list[str]]
) -> ERPCConfig:
    """Create a new ERPCConfig with different upstreams but same settings.

    Args:
        source: The source configuration to clone settings from.
        new_upstreams: The new upstreams mapping to use.

    Returns:
        A new ERPCConfig instance with updated upstreams.

    """
    from dataclasses import fields as dc_fields

    from erpc.config import ERPCConfig as _ERPCConfig

    kwargs: dict[str, Any] = {}
    for f in dc_fields(source):
        if f.name == "upstreams":
            kwargs["upstreams"] = new_upstreams
        else:
            kwargs[f.name] = getattr(source, f.name)
    return _ERPCConfig(**kwargs)


def update_config(process: ERPCProcess, new_config: ERPCConfig) -> ConfigDiff:
    """Update a running eRPC process with a new configuration.

    Performs a stop -> rewrite config -> start cycle since eRPC does not
    support SIGHUP-based config reload natively.

    Args:
        process: The running ERPCProcess to update.
        new_config: The new configuration to apply.

    Returns:
        A ConfigDiff describing what changed.

    Raises:
        ERPCNotRunning: If the process is not currently running.

    """
    if not process.is_running:
        raise ERPCNotRunning("Cannot update config: eRPC is not running")

    diff = _diff_configs(process.config, new_config)
    process.config = new_config
    process.stop()
    process.start()
    return diff


def add_upstream(process: ERPCProcess, chain_id: int, endpoint: str) -> ConfigDiff:
    """Add an upstream endpoint to a running eRPC process.

    If the chain ID does not exist yet, it will be created.

    Args:
        process: The running ERPCProcess to update.
        chain_id: EVM chain identifier.
        endpoint: RPC endpoint URL to add.

    Returns:
        A ConfigDiff describing what changed.

    Raises:
        ERPCNotRunning: If the process is not currently running.

    """
    new_upstreams = deepcopy(process.config.upstreams)
    if chain_id in new_upstreams:
        new_upstreams[chain_id].append(endpoint)
    else:
        new_upstreams[chain_id] = [endpoint]

    new_config = _clone_config_with_upstreams(process.config, new_upstreams)
    return update_config(process, new_config)


def remove_upstream(process: ERPCProcess, chain_id: int, endpoint: str) -> ConfigDiff:
    """Remove an upstream endpoint from a running eRPC process.

    If the endpoint is the last one for a chain, the chain is removed entirely.

    Args:
        process: The running ERPCProcess to update.
        chain_id: EVM chain identifier.
        endpoint: RPC endpoint URL to remove.

    Returns:
        A ConfigDiff describing what changed.

    Raises:
        ERPCNotRunning: If the process is not currently running.
        ValueError: If the endpoint is not found for the given chain.

    """
    if chain_id not in process.config.upstreams:
        msg = f"Endpoint not found for chain {chain_id}: {endpoint}"
        raise ValueError(msg)

    if endpoint not in process.config.upstreams[chain_id]:
        msg = f"Endpoint not found for chain {chain_id}: {endpoint}"
        raise ValueError(msg)

    new_upstreams = deepcopy(process.config.upstreams)
    new_upstreams[chain_id].remove(endpoint)
    if not new_upstreams[chain_id]:
        del new_upstreams[chain_id]

    new_config = _clone_config_with_upstreams(process.config, new_upstreams)
    return update_config(process, new_config)
