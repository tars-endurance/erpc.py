"""Tests for eRPC rate limiter configuration."""

from __future__ import annotations

import pytest

from erpc.rate_limiters import (
    AutoTuneConfig,
    MemoryStore,
    RateLimitBudget,
    RateLimiterConfig,
    RateLimitRule,
    RedisStore,
)


class TestRateLimitRule:
    """Tests for RateLimitRule dataclass."""

    def test_basic_rule(self) -> None:
        """A rule with method, maxCount, and period can be created."""
        rule = RateLimitRule(method="eth_call", max_count=100, period="second")
        assert rule.method == "eth_call"
        assert rule.max_count == 100
        assert rule.period == "second"

    def test_default_scope_flags(self) -> None:
        """Scope flags default to False."""
        rule = RateLimitRule(method="*", max_count=1000, period="minute")
        assert rule.per_ip is False
        assert rule.per_user is False
        assert rule.per_network is False

    def test_scope_flags_enabled(self) -> None:
        """Scope flags can be individually enabled."""
        rule = RateLimitRule(
            method="eth_sendRawTransaction",
            max_count=10,
            period="minute",
            per_ip=True,
            per_user=True,
            per_network=True,
        )
        assert rule.per_ip is True
        assert rule.per_user is True
        assert rule.per_network is True

    @pytest.mark.parametrize("period", ["second", "minute", "hour", "day"])
    def test_valid_periods(self, period: str) -> None:
        """All supported period values are accepted."""
        rule = RateLimitRule(method="*", max_count=100, period=period)
        assert rule.period == period

    def test_invalid_period_raises(self) -> None:
        """An invalid period raises ValueError."""
        with pytest.raises(ValueError, match="period"):
            RateLimitRule(method="eth_call", max_count=100, period="week")

    def test_wildcard_method(self) -> None:
        """Wildcard method '*' is valid."""
        rule = RateLimitRule(method="*", max_count=500, period="second")
        assert rule.method == "*"

    def test_to_dict(self) -> None:
        """Rule serializes to eRPC-compatible dict."""
        rule = RateLimitRule(method="eth_call", max_count=100, period="second", per_ip=True)
        d = rule.to_dict()
        assert d == {
            "method": "eth_call",
            "maxCount": 100,
            "period": "second",
            "perIP": True,
            "perUser": False,
            "perNetwork": False,
        }

    def test_negative_max_count_raises(self) -> None:
        """Negative maxCount raises ValueError."""
        with pytest.raises(ValueError, match="max_count"):
            RateLimitRule(method="*", max_count=-1, period="second")


class TestAutoTuneConfig:
    """Tests for AutoTuneConfig dataclass."""

    def test_defaults(self) -> None:
        """AutoTuneConfig has sensible defaults."""
        config = AutoTuneConfig()
        assert config.enabled is True
        assert config.adjustment_period == "1m"
        assert config.error_rate_threshold == 0.1
        assert config.increase_factor == 1.1
        assert config.decrease_factor == 0.9
        assert config.min_budget == 0
        assert config.max_budget == 10_000

    def test_custom_values(self) -> None:
        """AutoTuneConfig accepts custom values."""
        config = AutoTuneConfig(
            enabled=False,
            adjustment_period="5m",
            error_rate_threshold=0.05,
            increase_factor=1.5,
            decrease_factor=0.5,
            min_budget=10,
            max_budget=500,
        )
        assert config.enabled is False
        assert config.max_budget == 500

    def test_to_dict(self) -> None:
        """AutoTuneConfig serializes to eRPC-compatible dict."""
        config = AutoTuneConfig(enabled=True, adjustment_period="2m")
        d = config.to_dict()
        assert d["enabled"] is True
        assert d["adjustmentPeriod"] == "2m"
        assert "errorRateThreshold" in d


class TestRateLimitBudget:
    """Tests for RateLimitBudget dataclass."""

    def test_single_rule_budget(self) -> None:
        """Budget with a single rule."""
        rule = RateLimitRule(method="*", max_count=100, period="second")
        budget = RateLimitBudget(id="global", rules=[rule])
        assert budget.id == "global"
        assert len(budget.rules) == 1
        assert budget.auto_tune is None

    def test_multiple_rules_budget(self) -> None:
        """Budget with multiple rules."""
        rules = [
            RateLimitRule(method="*", max_count=1000, period="minute"),
            RateLimitRule(method="eth_call", max_count=100, period="second"),
            RateLimitRule(method="eth_sendRawTransaction", max_count=10, period="minute"),
        ]
        budget = RateLimitBudget(id="tiered", rules=rules)
        assert len(budget.rules) == 3

    def test_budget_with_auto_tune(self) -> None:
        """Budget with auto-tuner configuration."""
        rule = RateLimitRule(method="*", max_count=500, period="minute")
        auto_tune = AutoTuneConfig(enabled=True, max_budget=2000)
        budget = RateLimitBudget(id="adaptive", rules=[rule], auto_tune=auto_tune)
        assert budget.auto_tune is not None
        assert budget.auto_tune.max_budget == 2000

    def test_budget_to_dict(self) -> None:
        """Budget serializes to eRPC-compatible dict."""
        rule = RateLimitRule(method="*", max_count=100, period="second")
        budget = RateLimitBudget(id="basic", rules=[rule])
        d = budget.to_dict()
        assert d["id"] == "basic"
        assert len(d["rules"]) == 1
        assert "autoTune" not in d

    def test_budget_to_dict_with_auto_tune(self) -> None:
        """Budget with auto-tune includes autoTune in dict."""
        rule = RateLimitRule(method="*", max_count=100, period="second")
        auto_tune = AutoTuneConfig()
        budget = RateLimitBudget(id="tuned", rules=[rule], auto_tune=auto_tune)
        d = budget.to_dict()
        assert "autoTune" in d
        assert d["autoTune"]["enabled"] is True

    def test_empty_id_raises(self) -> None:
        """Empty budget ID raises ValueError."""
        with pytest.raises(ValueError, match="id"):
            RateLimitBudget(id="", rules=[])


class TestMemoryStore:
    """Tests for MemoryStore."""

    def test_to_dict(self) -> None:
        """MemoryStore serializes correctly."""
        store = MemoryStore()
        d = store.to_dict()
        assert d == {"driver": "memory"}


class TestRedisStore:
    """Tests for RedisStore."""

    def test_defaults(self) -> None:
        """RedisStore has sensible defaults."""
        store = RedisStore(uri="redis://localhost:6379")
        assert store.uri == "redis://localhost:6379"
        assert store.tls is False
        assert store.pool_size == 10
        assert store.near_limit_ratio == 0.8
        assert store.cache_key_prefix == "erpc_rl_"

    def test_custom_redis_store(self) -> None:
        """RedisStore accepts custom configuration."""
        store = RedisStore(
            uri="redis://redis.prod:6380/2",
            tls=True,
            pool_size=50,
            near_limit_ratio=0.9,
            cache_key_prefix="myapp_",
        )
        assert store.tls is True
        assert store.pool_size == 50

    def test_to_dict(self) -> None:
        """RedisStore serializes to eRPC-compatible dict."""
        store = RedisStore(uri="redis://localhost:6379")
        d = store.to_dict()
        assert d["driver"] == "redis"
        assert d["redis"]["uri"] == "redis://localhost:6379"
        assert d["redis"]["tls"] is False
        assert d["redis"]["poolSize"] == 10


class TestRateLimiterConfig:
    """Tests for RateLimiterConfig top-level config."""

    def test_memory_store_config(self) -> None:
        """Config with memory store and budgets."""
        budget = RateLimitBudget(
            id="global",
            rules=[RateLimitRule(method="*", max_count=100, period="second")],
        )
        config = RateLimiterConfig(store=MemoryStore(), budgets=[budget])
        assert len(config.budgets) == 1

    def test_redis_store_config(self) -> None:
        """Config with Redis store."""
        config = RateLimiterConfig(
            store=RedisStore(uri="redis://localhost:6379"),
            budgets=[],
        )
        assert isinstance(config.store, RedisStore)

    def test_to_dict(self) -> None:
        """Full config serializes to eRPC-compatible dict."""
        budget = RateLimitBudget(
            id="default",
            rules=[RateLimitRule(method="*", max_count=1000, period="minute")],
        )
        config = RateLimiterConfig(store=MemoryStore(), budgets=[budget])
        d = config.to_dict()
        assert "store" in d
        assert "budgets" in d
        assert d["store"]["driver"] == "memory"
        assert len(d["budgets"]) == 1

    def test_get_budget_by_id(self) -> None:
        """Budgets can be looked up by ID."""
        b1 = RateLimitBudget(
            id="free", rules=[RateLimitRule(method="*", max_count=10, period="second")]
        )
        b2 = RateLimitBudget(
            id="premium", rules=[RateLimitRule(method="*", max_count=1000, period="second")]
        )
        config = RateLimiterConfig(store=MemoryStore(), budgets=[b1, b2])
        assert config.get_budget("premium") is b2
        assert config.get_budget("nonexistent") is None

    def test_duplicate_budget_ids_raises(self) -> None:
        """Duplicate budget IDs raise ValueError."""
        b1 = RateLimitBudget(
            id="same", rules=[RateLimitRule(method="*", max_count=10, period="second")]
        )
        b2 = RateLimitBudget(
            id="same", rules=[RateLimitRule(method="*", max_count=20, period="second")]
        )
        with pytest.raises(ValueError, match=r"[Dd]uplicate"):
            RateLimiterConfig(store=MemoryStore(), budgets=[b1, b2])
