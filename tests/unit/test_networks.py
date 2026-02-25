"""Tests for network configuration dataclasses."""

from __future__ import annotations

import yaml

from erpc.config import ERPCConfig
from erpc.networks import (
    GetLogsConfig,
    IntegrityConfig,
    NetworkConfig,
    SendRawTransactionConfig,
)


class TestGetLogsConfig:
    """Tests for eth_getLogs configuration."""

    def test_defaults(self) -> None:
        cfg = GetLogsConfig()
        assert cfg.max_allowed_range is None
        assert cfg.max_allowed_addresses is None
        assert cfg.max_allowed_topics is None
        assert cfg.split_concurrency is None

    def test_full_config(self) -> None:
        cfg = GetLogsConfig(
            max_allowed_range=10_000,
            max_allowed_addresses=5,
            max_allowed_topics=3,
            split_concurrency=4,
        )
        assert cfg.max_allowed_range == 10_000
        assert cfg.split_concurrency == 4

    def test_to_dict(self) -> None:
        cfg = GetLogsConfig(max_allowed_range=2000, split_concurrency=8)
        d = cfg.to_dict()
        assert d == {
            "getLogsMaxAllowedRange": 2000,
            "getLogsSplitConcurrency": 8,
        }

    def test_to_dict_empty(self) -> None:
        cfg = GetLogsConfig()
        assert cfg.to_dict() == {}


class TestSendRawTransactionConfig:
    """Tests for eth_sendRawTransaction idempotency config."""

    def test_defaults(self) -> None:
        cfg = SendRawTransactionConfig()
        assert cfg.enabled is True

    def test_disabled(self) -> None:
        cfg = SendRawTransactionConfig(enabled=False)
        assert cfg.enabled is False

    def test_to_dict_enabled(self) -> None:
        cfg = SendRawTransactionConfig(enabled=True)
        assert cfg.to_dict() == {}

    def test_to_dict_disabled(self) -> None:
        cfg = SendRawTransactionConfig(enabled=False)
        assert cfg.to_dict() == {"sendRawTransactionIdempotent": False}


class TestIntegrityConfig:
    """Tests for integrity configuration."""

    def test_defaults(self) -> None:
        cfg = IntegrityConfig()
        assert cfg.enforce_get_logs_block_range is None
        assert cfg.consensus is None

    def test_full_config(self) -> None:
        cfg = IntegrityConfig(
            enforce_get_logs_block_range=True,
            consensus={"strategy": "majority", "threshold": 2},
        )
        assert cfg.enforce_get_logs_block_range is True

    def test_to_dict(self) -> None:
        cfg = IntegrityConfig(enforce_get_logs_block_range=True)
        d = cfg.to_dict()
        assert d == {"enforceGetLogsBlockRange": True}

    def test_to_dict_with_consensus(self) -> None:
        consensus = {"strategy": "majority", "threshold": 2}
        cfg = IntegrityConfig(consensus=consensus)
        d = cfg.to_dict()
        assert d == {"consensus": consensus}


class TestNetworkConfig:
    """Tests for full network configuration."""

    def test_minimal_config(self) -> None:
        net = NetworkConfig(chain_id=1)
        assert net.chain_id == 1
        assert net.architecture == "evm"
        assert net.aliases is None
        assert net.failsafe_policies is None
        assert net.rate_limit_budget is None

    def test_full_config(self) -> None:
        net = NetworkConfig(
            chain_id=1,
            architecture="evm",
            aliases=["ethereum", "eth-mainnet"],
            failsafe_policies={"retry": {"maxRetries": 3}},
            rate_limit_budget="global-budget",
            integrity=IntegrityConfig(enforce_get_logs_block_range=True),
            get_logs=GetLogsConfig(max_allowed_range=10_000, split_concurrency=4),
            send_raw_transaction=SendRawTransactionConfig(enabled=True),
        )
        assert net.aliases == ["ethereum", "eth-mainnet"]
        assert net.rate_limit_budget == "global-budget"

    def test_to_dict_minimal(self) -> None:
        net = NetworkConfig(chain_id=1)
        d = net.to_dict()
        assert d == {
            "architecture": "evm",
            "evm": {"chainId": 1},
        }

    def test_to_dict_full(self) -> None:
        net = NetworkConfig(
            chain_id=137,
            aliases=["polygon"],
            failsafe_policies={"timeout": {"duration": "15s"}},
            rate_limit_budget="my-budget",
            integrity=IntegrityConfig(enforce_get_logs_block_range=True),
            get_logs=GetLogsConfig(max_allowed_range=5000),
        )
        d = net.to_dict()
        assert d["architecture"] == "evm"
        assert d["evm"]["chainId"] == 137
        assert d["aliases"] == ["polygon"]
        assert d["failsafe"]["timeout"]["duration"] == "15s"
        assert d["rateLimitBudget"] == "my-budget"
        assert d["evm"]["integrity"]["enforceGetLogsBlockRange"] is True
        assert d["evm"]["getLogsMaxAllowedRange"] == 5000

    def test_to_dict_omits_none_fields(self) -> None:
        net = NetworkConfig(chain_id=42161)
        d = net.to_dict()
        assert "aliases" not in d
        assert "failsafe" not in d
        assert "rateLimitBudget" not in d
        assert "integrity" not in d.get("evm", {})

    def test_aliases(self) -> None:
        net = NetworkConfig(chain_id=1, aliases=["ethereum", "eth"])
        d = net.to_dict()
        assert d["aliases"] == ["ethereum", "eth"]


class TestNetworkConfigIntegration:
    """Tests for NetworkConfig integration with ERPCConfig."""

    def test_erpc_config_with_networks(self) -> None:
        networks = [
            NetworkConfig(chain_id=1),
            NetworkConfig(chain_id=137, aliases=["polygon"]),
        ]
        config = ERPCConfig(
            upstreams={
                1: ["https://eth.example.com"],
                137: ["https://polygon.example.com"],
            },
            networks=networks,
        )
        doc = yaml.safe_load(config.to_yaml())
        project = doc["projects"][0]
        net1 = next(n for n in project["networks"] if n["evm"]["chainId"] == 1)
        net137 = next(n for n in project["networks"] if n["evm"]["chainId"] == 137)
        assert "aliases" not in net1
        assert net137["aliases"] == ["polygon"]

    def test_network_defaults(self) -> None:
        defaults = NetworkConfig(
            chain_id=0,
            failsafe_policies={"retry": {"maxRetries": 3}},
        )
        config = ERPCConfig(
            upstreams={1: ["https://eth.example.com"]},
            network_defaults=defaults,
        )
        doc = yaml.safe_load(config.to_yaml())
        project = doc["projects"][0]
        assert "networkDefaults" in project
        assert project["networkDefaults"]["failsafe"]["retry"]["maxRetries"] == 3

    def test_network_config_serializes_get_logs(self) -> None:
        net = NetworkConfig(
            chain_id=1,
            get_logs=GetLogsConfig(
                max_allowed_range=10_000,
                max_allowed_addresses=10,
                max_allowed_topics=4,
                split_concurrency=8,
            ),
        )
        d = net.to_dict()
        evm = d["evm"]
        assert evm["getLogsMaxAllowedRange"] == 10_000
        assert evm["getLogsMaxAllowedAddresses"] == 10
        assert evm["getLogsMaxAllowedTopics"] == 4
        assert evm["getLogsSplitConcurrency"] == 8

    def test_network_config_send_raw_tx_disabled(self) -> None:
        net = NetworkConfig(
            chain_id=1,
            send_raw_transaction=SendRawTransactionConfig(enabled=False),
        )
        d = net.to_dict()
        assert d["evm"]["sendRawTransactionIdempotent"] is False

    def test_backward_compat_upstreams_only(self) -> None:
        """ERPCConfig without explicit networks still works."""
        config = ERPCConfig(upstreams={1: ["https://eth.example.com"]})
        doc = yaml.safe_load(config.to_yaml())
        assert len(doc["projects"][0]["networks"]) == 1
