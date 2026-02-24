"""Network configuration dataclasses for eRPC.

Maps the eRPC network configuration surface — chain identity, integrity checks,
eth_getLogs controls, eth_sendRawTransaction idempotency, failsafe policies,
rate-limit budgets, and name aliasing — to typed Python dataclasses.

See https://docs.erpc.cloud/config/projects/networks for the upstream schema.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class GetLogsConfig:
    """Controls for ``eth_getLogs`` request validation and splitting.

    Network-level limits that reject oversized requests early and control
    how the eRPC proxy splits large log queries into parallel sub-requests.

    Attributes:
        max_allowed_range: Maximum block range allowed per request.
            Requests exceeding this are rejected.
        max_allowed_addresses: Maximum number of addresses per filter.
        max_allowed_topics: Maximum number of topics per filter.
        split_concurrency: Maximum parallel sub-requests when splitting.

    Examples:
        >>> cfg = GetLogsConfig(max_allowed_range=10_000, split_concurrency=4)
        >>> cfg.to_dict()
        {'getLogsMaxAllowedRange': 10000, 'getLogsSplitConcurrency': 4}

    """

    max_allowed_range: int | None = None
    max_allowed_addresses: int | None = None
    max_allowed_topics: int | None = None
    split_concurrency: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to eRPC YAML-compatible dictionary.

        Returns:
            Dictionary with only non-None fields, using eRPC camelCase keys.

        """
        d: dict[str, Any] = {}
        if self.max_allowed_range is not None:
            d["getLogsMaxAllowedRange"] = self.max_allowed_range
        if self.max_allowed_addresses is not None:
            d["getLogsMaxAllowedAddresses"] = self.max_allowed_addresses
        if self.max_allowed_topics is not None:
            d["getLogsMaxAllowedTopics"] = self.max_allowed_topics
        if self.split_concurrency is not None:
            d["getLogsSplitConcurrency"] = self.split_concurrency
        return d


@dataclass
class SendRawTransactionConfig:
    """Idempotent broadcasting configuration for ``eth_sendRawTransaction``.

    When enabled (the default), eRPC converts duplicate-transaction errors
    (``"already known"``, ``"nonce too low"`` with on-chain verification)
    into success responses, making retry and hedge policies safe.

    Attributes:
        enabled: Whether idempotent broadcasting is active. Defaults to ``True``
            (eRPC's default behavior).

    Examples:
        >>> SendRawTransactionConfig(enabled=False).to_dict()
        {'sendRawTransactionIdempotent': False}

    """

    enabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Serialize to eRPC YAML-compatible dictionary.

        Returns:
            Empty dict when enabled (default), otherwise explicit disable flag.

        """
        if not self.enabled:
            return {"sendRawTransactionIdempotent": False}
        return {}


@dataclass
class IntegrityConfig:
    """Data integrity configuration for a network.

    Controls block-range enforcement for ``eth_getLogs`` and consensus
    strategies across multiple upstreams.

    Attributes:
        enforce_get_logs_block_range: When ``True``, validates that the upstream
            has data for the requested ``fromBlock..toBlock`` range.
        consensus: Consensus policy configuration dict (strategy, threshold,
            preferHighestValueFor, etc.). Passed through as-is to eRPC.

    Examples:
        >>> cfg = IntegrityConfig(enforce_get_logs_block_range=True)
        >>> cfg.to_dict()
        {'enforceGetLogsBlockRange': True}

    """

    enforce_get_logs_block_range: bool | None = None
    consensus: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to eRPC YAML-compatible dictionary.

        Returns:
            Dictionary with only non-None fields.

        """
        d: dict[str, Any] = {}
        if self.enforce_get_logs_block_range is not None:
            d["enforceGetLogsBlockRange"] = self.enforce_get_logs_block_range
        if self.consensus is not None:
            d["consensus"] = self.consensus
        return d


@dataclass
class NetworkConfig:
    """Full network configuration for an eRPC project.

    Represents a single chain (e.g. Ethereum mainnet, Polygon) with its
    architecture, integrity settings, RPC method controls, failsafe policies,
    rate-limit budget, and optional human-friendly aliases.

    Attributes:
        chain_id: EVM chain identifier (e.g. ``1`` for Ethereum mainnet).
        architecture: Network architecture type. Defaults to ``"evm"``.
        aliases: Optional friendly names (e.g. ``["ethereum", "eth-mainnet"]``)
            that can be used in place of ``/evm/<chainId>`` in request paths.
        failsafe_policies: Failsafe policy configuration (retry, hedge, timeout,
            circuit-breaker). Passed through as-is to eRPC.
        rate_limit_budget: Reference to a named rate-limit budget defined at
            the project or global level.
        integrity: Data integrity configuration.
        get_logs: ``eth_getLogs`` request controls.
        send_raw_transaction: ``eth_sendRawTransaction`` idempotency config.

    Examples:
        >>> net = NetworkConfig(chain_id=1, aliases=["ethereum"])
        >>> net.to_dict()["aliases"]
        ['ethereum']

    """

    chain_id: int = 0
    architecture: str = "evm"
    aliases: list[str] | None = None
    failsafe_policies: dict[str, Any] | None = None
    rate_limit_budget: str | None = None
    integrity: IntegrityConfig = field(default_factory=IntegrityConfig)
    get_logs: GetLogsConfig = field(default_factory=GetLogsConfig)
    send_raw_transaction: SendRawTransactionConfig = field(
        default_factory=SendRawTransactionConfig
    )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to eRPC YAML-compatible dictionary.

        Produces the structure expected under ``projects[].networks[]``
        in an eRPC configuration file. Only non-default fields are included.

        Returns:
            Dictionary ready for YAML serialization.

        """
        evm: dict[str, Any] = {"chainId": self.chain_id}

        # Integrity
        integrity_d = self.integrity.to_dict()
        if integrity_d:
            evm["integrity"] = integrity_d

        # getLogs controls (flat in evm block)
        get_logs_d = self.get_logs.to_dict()
        evm.update(get_logs_d)

        # sendRawTransaction
        send_tx_d = self.send_raw_transaction.to_dict()
        evm.update(send_tx_d)

        d: dict[str, Any] = {
            "architecture": self.architecture,
            "evm": evm,
        }

        if self.aliases is not None:
            d["aliases"] = self.aliases

        if self.failsafe_policies is not None:
            d["failsafe"] = self.failsafe_policies

        if self.rate_limit_budget is not None:
            d["rateLimitBudget"] = self.rate_limit_budget

        return d

    def to_defaults_dict(self) -> dict[str, Any]:
        """Serialize for use as ``networkDefaults`` (omits chain-specific fields).

        Returns:
            Dictionary suitable for the ``networkDefaults`` project key.

        """
        d: dict[str, Any] = {}

        if self.failsafe_policies is not None:
            d["failsafe"] = self.failsafe_policies

        if self.rate_limit_budget is not None:
            d["rateLimitBudget"] = self.rate_limit_budget

        integrity_d = self.integrity.to_dict()
        if integrity_d:
            evm: dict[str, Any] = {"integrity": integrity_d}
            d["evm"] = evm

        return d
