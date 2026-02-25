"""eRPC rate limiter configuration.

Provides dataclasses for configuring eRPC rate limiting budgets, rules,
auto-tuning, and storage backends (memory or Redis).

Examples:
    >>> from erpc.rate_limiters import (
    ...     MemoryStore, RateLimiterConfig, RateLimitBudget, RateLimitRule,
    ... )
    >>> budget = RateLimitBudget(
    ...     id="global",
    ...     rules=[RateLimitRule(method="*", max_count=1000, period="minute")],
    ... )
    >>> config = RateLimiterConfig(store=MemoryStore(), budgets=[budget])
    >>> config.to_dict()["store"]["driver"]
    'memory'

"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Union

_VALID_PERIODS = frozenset({"second", "minute", "hour", "day"})


@dataclass
class RateLimitRule:
    """A single rate limiting rule within a budget.

    Args:
        method: RPC method name or ``"*"`` for wildcard matching.
        max_count: Maximum number of requests allowed in the period.
        period: Time window — one of ``"second"``, ``"minute"``, ``"hour"``, ``"day"``.
        per_ip: Apply the limit per source IP address.
        per_user: Apply the limit per authenticated user.
        per_network: Apply the limit per network/chain.

    Raises:
        ValueError: If ``period`` is not a valid time window or ``max_count`` is negative.

    Examples:
        >>> rule = RateLimitRule(method="eth_call", max_count=100, period="second")
        >>> rule.to_dict()["maxCount"]
        100

    """

    method: str
    max_count: int
    period: str
    per_ip: bool = False
    per_user: bool = False
    per_network: bool = False

    def __post_init__(self) -> None:
        if self.period not in _VALID_PERIODS:
            msg = f"period must be one of {sorted(_VALID_PERIODS)}, got {self.period!r}"
            raise ValueError(msg)
        if self.max_count < 0:
            msg = f"max_count must be non-negative, got {self.max_count}"
            raise ValueError(msg)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to an eRPC-compatible dictionary.

        Returns:
            Dictionary with camelCase keys matching eRPC YAML schema.

        """
        return {
            "method": self.method,
            "maxCount": self.max_count,
            "period": self.period,
            "perIP": self.per_ip,
            "perUser": self.per_user,
            "perNetwork": self.per_network,
        }


@dataclass
class AutoTuneConfig:
    """Auto-tuner configuration for dynamic rate limit adjustment.

    The auto-tuner monitors error rates and adjusts budget limits
    automatically within the configured bounds.

    Args:
        enabled: Whether auto-tuning is active.
        adjustment_period: How often to evaluate and adjust (e.g. ``"1m"``, ``"5m"``).
        error_rate_threshold: Error rate above which limits are decreased (0.0–1.0).
        increase_factor: Multiplier when increasing budget (> 1.0).
        decrease_factor: Multiplier when decreasing budget (< 1.0).
        min_budget: Floor for auto-tuned budget value.
        max_budget: Ceiling for auto-tuned budget value.

    Examples:
        >>> config = AutoTuneConfig(enabled=True, max_budget=5000)
        >>> config.to_dict()["maxBudget"]
        5000

    """

    enabled: bool = True
    adjustment_period: str = "1m"
    error_rate_threshold: float = 0.1
    increase_factor: float = 1.1
    decrease_factor: float = 0.9
    min_budget: int = 0
    max_budget: int = 10_000

    def to_dict(self) -> dict[str, Any]:
        """Serialize to an eRPC-compatible dictionary.

        Returns:
            Dictionary with camelCase keys matching eRPC YAML schema.

        """
        return {
            "enabled": self.enabled,
            "adjustmentPeriod": self.adjustment_period,
            "errorRateThreshold": self.error_rate_threshold,
            "increaseFactor": self.increase_factor,
            "decreaseFactor": self.decrease_factor,
            "minBudget": self.min_budget,
            "maxBudget": self.max_budget,
        }


@dataclass
class RateLimitBudget:
    """A named rate limit budget containing one or more rules.

    Budgets are referenced by ID in eRPC project and network configurations.

    Args:
        id: Unique budget identifier used for referencing in config.
        rules: List of rate limiting rules applied in this budget.
        auto_tune: Optional auto-tuner configuration for dynamic adjustment.

    Raises:
        ValueError: If ``id`` is empty.

    Examples:
        >>> budget = RateLimitBudget(
        ...     id="global",
        ...     rules=[RateLimitRule(method="*", max_count=100, period="second")],
        ... )
        >>> budget.to_dict()["id"]
        'global'

    """

    id: str
    rules: list[RateLimitRule]
    auto_tune: AutoTuneConfig | None = None

    def __post_init__(self) -> None:
        if not self.id:
            msg = "id must not be empty"
            raise ValueError(msg)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to an eRPC-compatible dictionary.

        Returns:
            Dictionary with camelCase keys matching eRPC YAML schema.

        """
        d: dict[str, Any] = {
            "id": self.id,
            "rules": [r.to_dict() for r in self.rules],
        }
        if self.auto_tune is not None:
            d["autoTune"] = self.auto_tune.to_dict()
        return d


@dataclass
class MemoryStore:
    """In-memory rate limit store backend.

    Uses the eRPC process memory for rate limit tracking. Simple and
    requires no external dependencies, but state is lost on restart.

    Examples:
        >>> MemoryStore().to_dict()
        {'driver': 'memory'}

    """

    def to_dict(self) -> dict[str, Any]:
        """Serialize to an eRPC-compatible dictionary.

        Returns:
            Dictionary with ``driver`` set to ``"memory"``.

        """
        return {"driver": "memory"}


@dataclass
class RedisStore:
    """Redis-backed rate limit store.

    Persists rate limit counters in Redis, enabling shared state across
    multiple eRPC instances.

    Args:
        uri: Redis connection URI (e.g. ``"redis://localhost:6379"``).
        tls: Enable TLS for the Redis connection.
        pool_size: Connection pool size.
        near_limit_ratio: Ratio (0.0–1.0) at which to flag approaching limits.
        cache_key_prefix: Prefix for all Redis keys used by the rate limiter.

    Examples:
        >>> store = RedisStore(uri="redis://localhost:6379")
        >>> store.to_dict()["driver"]
        'redis'

    """

    uri: str
    tls: bool = False
    pool_size: int = 10
    near_limit_ratio: float = 0.8
    cache_key_prefix: str = "erpc_rl_"

    def to_dict(self) -> dict[str, Any]:
        """Serialize to an eRPC-compatible dictionary.

        Returns:
            Dictionary with ``driver`` set to ``"redis"`` and nested config.

        """
        return {
            "driver": "redis",
            "redis": {
                "uri": self.uri,
                "tls": self.tls,
                "poolSize": self.pool_size,
                "nearLimitRatio": self.near_limit_ratio,
                "cacheKeyPrefix": self.cache_key_prefix,
            },
        }


# Type alias for store backends
RateLimitStore = Union[MemoryStore, RedisStore]


@dataclass
class RateLimiterConfig:
    """Top-level rate limiter configuration for eRPC.

    Combines a storage backend with one or more named rate limit budgets.

    Args:
        store: Storage backend for rate limit counters.
        budgets: List of named rate limit budgets.

    Raises:
        ValueError: If duplicate budget IDs are found.

    Examples:
        >>> config = RateLimiterConfig(
        ...     store=MemoryStore(),
        ...     budgets=[
        ...         RateLimitBudget(
        ...             id="default",
        ...             rules=[RateLimitRule(method="*", max_count=100, period="second")],
        ...         )
        ...     ],
        ... )
        >>> config.get_budget("default") is not None
        True

    """

    store: RateLimitStore
    budgets: list[RateLimitBudget] = field(default_factory=list)

    def __post_init__(self) -> None:
        ids = [b.id for b in self.budgets]
        if len(ids) != len(set(ids)):
            msg = "Duplicate budget IDs found"
            raise ValueError(msg)

    def get_budget(self, budget_id: str) -> RateLimitBudget | None:
        """Look up a budget by its ID.

        Args:
            budget_id: The unique budget identifier to search for.

        Returns:
            The matching budget, or ``None`` if not found.

        """
        for budget in self.budgets:
            if budget.id == budget_id:
                return budget
        return None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to an eRPC-compatible dictionary.

        Returns:
            Dictionary with store and budgets configuration.

        """
        return {
            "store": self.store.to_dict(),
            "budgets": [b.to_dict() for b in self.budgets],
        }
