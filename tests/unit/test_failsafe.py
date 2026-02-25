"""Tests for eRPC failsafe policy configuration."""

from __future__ import annotations

import pytest

from erpc.failsafe import (
    CircuitBreakerPolicy,
    FailsafeConfig,
    FailsafePresets,
    HedgePolicy,
    MethodFailsafeConfig,
    RetryPolicy,
    TimeoutPolicy,
)


class TestTimeoutPolicy:
    """Tests for TimeoutPolicy dataclass."""

    def test_construction_with_duration(self) -> None:
        policy = TimeoutPolicy(duration="30s")
        assert policy.duration == "30s"

    def test_to_dict(self) -> None:
        policy = TimeoutPolicy(duration="15s")
        assert policy.to_dict() == {"duration": "15s"}

    def test_various_duration_formats(self) -> None:
        for dur in ("100ms", "5s", "1m", "2m30s"):
            policy = TimeoutPolicy(duration=dur)
            assert policy.duration == dur


class TestRetryPolicy:
    """Tests for RetryPolicy dataclass."""

    def test_defaults(self) -> None:
        policy = RetryPolicy()
        assert policy.max_attempts == 3
        assert policy.delay == "1s"
        assert policy.backoff_max_delay == "10s"
        assert policy.backoff_factor == 2.0
        assert policy.jitter == "500ms"

    def test_custom_values(self) -> None:
        policy = RetryPolicy(max_attempts=5, delay="2s", backoff_factor=3.0)
        assert policy.max_attempts == 5
        assert policy.delay == "2s"
        assert policy.backoff_factor == 3.0

    def test_empty_result_fields(self) -> None:
        policy = RetryPolicy(
            empty_result_accept=False,
            empty_result_confidence=0.8,
            empty_result_max_attempts=5,
        )
        assert policy.empty_result_accept is False
        assert policy.empty_result_confidence == 0.8
        assert policy.empty_result_max_attempts == 5

    def test_to_dict(self) -> None:
        policy = RetryPolicy(max_attempts=2, delay="500ms")
        d = policy.to_dict()
        assert d["maxAttempts"] == 2
        assert d["delay"] == "500ms"
        assert d["backoffMaxDelay"] == "10s"
        assert d["backoffFactor"] == 2.0
        assert d["jitter"] == "500ms"

    def test_to_dict_with_empty_result(self) -> None:
        policy = RetryPolicy(empty_result_accept=True, empty_result_confidence=0.9)
        d = policy.to_dict()
        assert d["emptyResultAccept"] is True
        assert d["emptyResultConfidence"] == 0.9

    def test_to_dict_omits_none_empty_result(self) -> None:
        policy = RetryPolicy()
        d = policy.to_dict()
        assert "emptyResultAccept" not in d
        assert "emptyResultConfidence" not in d
        assert "emptyResultMaxAttempts" not in d


class TestHedgePolicy:
    """Tests for HedgePolicy dataclass."""

    def test_construction(self) -> None:
        policy = HedgePolicy(delay="500ms", max_count=2)
        assert policy.delay == "500ms"
        assert policy.max_count == 2

    def test_to_dict(self) -> None:
        policy = HedgePolicy(delay="1s", max_count=3)
        assert policy.to_dict() == {"delay": "1s", "maxCount": 3}


class TestCircuitBreakerPolicy:
    """Tests for CircuitBreakerPolicy dataclass."""

    def test_defaults(self) -> None:
        policy = CircuitBreakerPolicy()
        assert policy.failure_threshold == 5
        assert policy.half_open_after == "60s"
        assert policy.success_threshold == 3

    def test_custom(self) -> None:
        policy = CircuitBreakerPolicy(
            failure_threshold=10, half_open_after="30s", success_threshold=5
        )
        assert policy.failure_threshold == 10

    def test_to_dict(self) -> None:
        policy = CircuitBreakerPolicy()
        d = policy.to_dict()
        assert d == {
            "failureThreshold": 5,
            "halfOpenAfter": "60s",
            "successThreshold": 3,
        }


class TestFailsafeConfig:
    """Tests for composite FailsafeConfig."""

    def test_all_policies(self) -> None:
        config = FailsafeConfig(
            timeout=TimeoutPolicy(duration="30s"),
            retry=RetryPolicy(max_attempts=3),
            hedge=HedgePolicy(delay="500ms", max_count=2),
            circuit_breaker=CircuitBreakerPolicy(),
        )
        d = config.to_dict()
        assert "timeout" in d
        assert "retry" in d
        assert "hedge" in d
        assert "circuitBreaker" in d

    def test_partial_policies(self) -> None:
        config = FailsafeConfig(timeout=TimeoutPolicy(duration="10s"))
        d = config.to_dict()
        assert "timeout" in d
        assert "retry" not in d
        assert "hedge" not in d
        assert "circuitBreaker" not in d

    def test_empty_config(self) -> None:
        config = FailsafeConfig()
        assert config.to_dict() == {}

    def test_disable_policy_with_none(self) -> None:
        config = FailsafeConfig(timeout=None, retry=None)
        assert config.to_dict() == {}


class TestMethodFailsafeConfig:
    """Tests for per-method failsafe configuration."""

    def test_wildcard_match(self) -> None:
        cfg = MethodFailsafeConfig(
            match_method="eth_*",
            failsafe=FailsafeConfig(timeout=TimeoutPolicy(duration="5s")),
        )
        d = cfg.to_dict()
        assert d["matchMethod"] == "eth_*"
        assert "failsafe" in d

    def test_specific_method(self) -> None:
        cfg = MethodFailsafeConfig(
            match_method="eth_getLogs",
            failsafe=FailsafeConfig(
                timeout=TimeoutPolicy(duration="60s"),
                retry=RetryPolicy(max_attempts=5),
            ),
        )
        d = cfg.to_dict()
        assert d["matchMethod"] == "eth_getLogs"
        assert d["failsafe"]["timeout"]["duration"] == "60s"
        assert d["failsafe"]["retry"]["maxAttempts"] == 5

    @pytest.mark.parametrize(
        "finality",
        ["finalized", "unfinalized", "realtime", "unknown"],
    )
    def test_match_finality_states(self, finality: str) -> None:
        cfg = MethodFailsafeConfig(
            match_method="*",
            match_finality=finality,
            failsafe=FailsafeConfig(timeout=TimeoutPolicy(duration="10s")),
        )
        d = cfg.to_dict()
        assert d["matchFinality"] == finality

    def test_no_finality_omitted(self) -> None:
        cfg = MethodFailsafeConfig(
            match_method="eth_call",
            failsafe=FailsafeConfig(),
        )
        d = cfg.to_dict()
        assert "matchFinality" not in d


class TestFailsafePresets:
    """Tests for preset failsafe configurations."""

    def test_high_performance_defi(self) -> None:
        configs = FailsafePresets.high_performance_defi()
        assert isinstance(configs, FailsafeConfig)
        d = configs.to_dict()
        assert "timeout" in d
        assert "retry" in d
        assert "hedge" in d

    def test_indexer(self) -> None:
        config = FailsafePresets.indexer()
        assert isinstance(config, FailsafeConfig)
        d = config.to_dict()
        assert "timeout" in d
        assert "retry" in d
        # Indexers prioritize reliability, no hedging needed
        assert "hedge" not in d

    def test_finality_based(self) -> None:
        configs = FailsafePresets.finality_based()
        assert isinstance(configs, list)
        assert len(configs) >= 2
        for cfg in configs:
            assert isinstance(cfg, MethodFailsafeConfig)
            d = cfg.to_dict()
            assert "matchFinality" in d
            assert "failsafe" in d

    def test_presets_produce_valid_dicts(self) -> None:
        """All presets should produce serializable structures."""
        defi = FailsafePresets.high_performance_defi().to_dict()
        indexer = FailsafePresets.indexer().to_dict()
        finality = [c.to_dict() for c in FailsafePresets.finality_based()]
        # Smoke check: all are dicts
        assert isinstance(defi, dict)
        assert isinstance(indexer, dict)
        assert all(isinstance(d, dict) for d in finality)
