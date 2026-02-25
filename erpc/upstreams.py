"""Upstream configuration dataclasses for eRPC."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class UpstreamConfig:
    """Configuration for a single eRPC upstream.

    Attributes:
        id: Unique upstream identifier.
        endpoint: RPC endpoint URL.
        type: Upstream type (e.g. ``evm``, ``evm+alchemy``).
        vendor_name: Provider vendor name for provider-specific optimisations.
        allowed_methods: Allowlist of JSON-RPC methods. Empty means all allowed.
        ignored_methods: Denylist of JSON-RPC methods.
        failsafe: Failsafe policy overrides for this upstream.
        json_rpc: JSON-RPC-level configuration overrides.

    """

    id: str = ""
    endpoint: str = ""
    type: str = "evm"
    vendor_name: str = ""
    allowed_methods: list[str] = field(default_factory=list)
    ignored_methods: list[str] = field(default_factory=list)
    failsafe: dict[str, Any] = field(default_factory=dict)
    json_rpc: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialise this upstream config to an eRPC-compatible dictionary."""
        d: dict[str, Any] = {}
        if self.id:
            d["id"] = self.id
        if self.endpoint:
            d["endpoint"] = self.endpoint
        if self.type != "evm":
            d["type"] = self.type
        if self.vendor_name:
            d["vendorName"] = self.vendor_name
        if self.allowed_methods:
            d["allowMethods"] = self.allowed_methods
        if self.ignored_methods:
            d["ignoreMethods"] = self.ignored_methods
        if self.failsafe:
            d["failsafe"] = self.failsafe
        if self.json_rpc:
            d["jsonRpc"] = self.json_rpc
        return d
