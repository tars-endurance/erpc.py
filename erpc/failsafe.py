"""eRPC failsafe policy configuration.

Provides dataclasses for timeout, retry, hedge, and circuit breaker policies
that map directly to eRPC's failsafe configuration surface. Includes preset
configurations for common use cases.

Examples:
    >>> from erpc.failsafe import FailsafeConfig, TimeoutPolicy, RetryPolicy
    >>> config = FailsafeConfig(
    ...     timeout=TimeoutPolicy(duration="30s"),
    ...     retry=RetryPolicy(max_attempts=3),
    ... )
    >>> config.to_dict()
    {'timeout': {'duration': '30s'}, 'retry': {'maxAttempts': 3, ...}}

"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TimeoutPolicy:
    """Timeout policy for eRPC requests.

    Args:
        duration: Timeout duration string (e.g. "30s", "100ms", "1m").

    Examples:
        >>> TimeoutPolicy(duration="30s").to_dict()
        {'duration': '30s'}

    """

    duration: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize to eRPC-compatible dictionary.

        Returns:
            Dictionary with camelCase keys matching eRPC config schema.

        """
        return {"duration": self.duration}


@dataclass
class RetryPolicy:
    """Retry policy with exponential backoff and empty response handling.

    Args:
        max_attempts: Maximum number of retry attempts.
        delay: Initial delay between retries (e.g. "1s").
        backoff_max_delay: Maximum backoff delay cap (e.g. "10s").
        backoff_factor: Multiplier for exponential backoff.
        jitter: Random jitter added to delay (e.g. "500ms").
        empty_result_accept: Whether to accept empty results as valid.
        empty_result_confidence: Confidence threshold for empty result detection.
        empty_result_max_attempts: Max retries specifically for empty results.

    Examples:
        >>> RetryPolicy(max_attempts=5, delay="2s").to_dict()
        {'maxAttempts': 5, 'delay': '2s', ...}

    """

    max_attempts: int = 3
    delay: str = "1s"
    backoff_max_delay: str = "10s"
    backoff_factor: float = 2.0
    jitter: str = "500ms"
    empty_result_accept: bool | None = None
    empty_result_confidence: float | None = None
    empty_result_max_attempts: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to eRPC-compatible dictionary.

        Returns:
            Dictionary with camelCase keys. Empty result fields are omitted when None.

        """
        d: dict[str, Any] = {
            "maxAttempts": self.max_attempts,
            "delay": self.delay,
            "backoffMaxDelay": self.backoff_max_delay,
            "backoffFactor": self.backoff_factor,
            "jitter": self.jitter,
        }
        if self.empty_result_accept is not None:
            d["emptyResultAccept"] = self.empty_result_accept
        if self.empty_result_confidence is not None:
            d["emptyResultConfidence"] = self.empty_result_confidence
        if self.empty_result_max_attempts is not None:
            d["emptyResultMaxAttempts"] = self.empty_result_max_attempts
        return d


@dataclass
class HedgePolicy:
    """Hedge policy for parallel speculative requests.

    Sends additional requests after a delay to reduce tail latency.

    Args:
        delay: Time to wait before sending hedge request (e.g. "500ms").
        max_count: Maximum number of hedge requests to send.

    Examples:
        >>> HedgePolicy(delay="500ms", max_count=2).to_dict()
        {'delay': '500ms', 'maxCount': 2}

    """

    delay: str
    max_count: int

    def to_dict(self) -> dict[str, Any]:
        """Serialize to eRPC-compatible dictionary.

        Returns:
            Dictionary with camelCase keys matching eRPC config schema.

        """
        return {"delay": self.delay, "maxCount": self.max_count}


@dataclass
class CircuitBreakerPolicy:
    """Circuit breaker policy to prevent cascading failures.

    Args:
        failure_threshold: Number of failures before opening the circuit.
        half_open_after: Duration before transitioning to half-open state.
        success_threshold: Successes needed in half-open to close the circuit.

    Examples:
        >>> CircuitBreakerPolicy().to_dict()
        {'failureThreshold': 5, 'halfOpenAfter': '60s', 'successThreshold': 3}

    """

    failure_threshold: int = 5
    half_open_after: str = "60s"
    success_threshold: int = 3

    def to_dict(self) -> dict[str, Any]:
        """Serialize to eRPC-compatible dictionary.

        Returns:
            Dictionary with camelCase keys matching eRPC config schema.

        """
        return {
            "failureThreshold": self.failure_threshold,
            "halfOpenAfter": self.half_open_after,
            "successThreshold": self.success_threshold,
        }


@dataclass
class FailsafeConfig:
    """Composite failsafe configuration combining multiple policies.

    Args:
        timeout: Timeout policy, or None to disable.
        retry: Retry policy, or None to disable.
        hedge: Hedge policy, or None to disable.
        circuit_breaker: Circuit breaker policy, or None to disable.

    Examples:
        >>> config = FailsafeConfig(
        ...     timeout=TimeoutPolicy(duration="30s"),
        ...     retry=RetryPolicy(),
        ... )
        >>> sorted(config.to_dict().keys())
        ['retry', 'timeout']

    """

    timeout: TimeoutPolicy | None = None
    retry: RetryPolicy | None = None
    hedge: HedgePolicy | None = None
    circuit_breaker: CircuitBreakerPolicy | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to eRPC-compatible dictionary.

        Returns:
            Dictionary with only non-None policies included.

        """
        d: dict[str, Any] = {}
        if self.timeout is not None:
            d["timeout"] = self.timeout.to_dict()
        if self.retry is not None:
            d["retry"] = self.retry.to_dict()
        if self.hedge is not None:
            d["hedge"] = self.hedge.to_dict()
        if self.circuit_breaker is not None:
            d["circuitBreaker"] = self.circuit_breaker.to_dict()
        return d


@dataclass
class MethodFailsafeConfig:
    """Per-method failsafe policy override.

    Allows different failsafe settings for specific RPC methods or finality states.

    Args:
        match_method: Method name or glob pattern (e.g. "eth_*", "eth_getLogs").
        match_finality: Finality state filter (finalized, unfinalized, realtime, unknown).
        failsafe: Failsafe configuration to apply for matching requests.

    Examples:
        >>> cfg = MethodFailsafeConfig(
        ...     match_method="eth_getLogs",
        ...     match_finality="finalized",
        ...     failsafe=FailsafeConfig(timeout=TimeoutPolicy(duration="60s")),
        ... )
        >>> cfg.to_dict()["matchMethod"]
        'eth_getLogs'

    """

    match_method: str
    failsafe: FailsafeConfig = field(default_factory=FailsafeConfig)
    match_finality: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to eRPC-compatible dictionary.

        Returns:
            Dictionary with matchMethod, optional matchFinality, and failsafe config.

        """
        d: dict[str, Any] = {"matchMethod": self.match_method}
        if self.match_finality is not None:
            d["matchFinality"] = self.match_finality
        d["failsafe"] = self.failsafe.to_dict()
        return d


class FailsafePresets:
    """Pre-built failsafe configurations for common use cases.

    Examples:
        >>> config = FailsafePresets.high_performance_defi()
        >>> "timeout" in config.to_dict()
        True

    """

    @staticmethod
    def high_performance_defi() -> FailsafeConfig:
        """Failsafe preset optimized for DeFi applications.

        Low timeouts, aggressive hedging, and fast retries for latency-sensitive
        trading and DeFi operations.

        Returns:
            FailsafeConfig tuned for low-latency DeFi workloads.

        """
        return FailsafeConfig(
            timeout=TimeoutPolicy(duration="5s"),
            retry=RetryPolicy(max_attempts=2, delay="250ms", backoff_max_delay="2s"),
            hedge=HedgePolicy(delay="300ms", max_count=2),
            circuit_breaker=CircuitBreakerPolicy(
                failure_threshold=3, half_open_after="30s", success_threshold=2
            ),
        )

    @staticmethod
    def indexer() -> FailsafeConfig:
        """Failsafe preset optimized for blockchain indexing.

        Generous timeouts and retries for reliability over large batch queries.
        No hedging to avoid unnecessary duplicate load.

        Returns:
            FailsafeConfig tuned for reliable indexing workloads.

        """
        return FailsafeConfig(
            timeout=TimeoutPolicy(duration="120s"),
            retry=RetryPolicy(
                max_attempts=10,
                delay="2s",
                backoff_max_delay="30s",
                backoff_factor=3.0,
                jitter="1s",
            ),
            circuit_breaker=CircuitBreakerPolicy(
                failure_threshold=10, half_open_after="120s", success_threshold=5
            ),
        )

    @staticmethod
    def finality_based() -> list[MethodFailsafeConfig]:
        """Failsafe presets that vary by block finality state.

        Returns different policies for finalized vs unfinalized data, reflecting
        that finalized data is immutable and can be cached/retried more aggressively.

        Returns:
            List of MethodFailsafeConfig entries for different finality states.

        """
        return [
            MethodFailsafeConfig(
                match_method="*",
                match_finality="finalized",
                failsafe=FailsafeConfig(
                    timeout=TimeoutPolicy(duration="30s"),
                    retry=RetryPolicy(max_attempts=5, delay="1s"),
                ),
            ),
            MethodFailsafeConfig(
                match_method="*",
                match_finality="unfinalized",
                failsafe=FailsafeConfig(
                    timeout=TimeoutPolicy(duration="10s"),
                    retry=RetryPolicy(max_attempts=2, delay="500ms"),
                    hedge=HedgePolicy(delay="500ms", max_count=1),
                ),
            ),
            MethodFailsafeConfig(
                match_method="*",
                match_finality="realtime",
                failsafe=FailsafeConfig(
                    timeout=TimeoutPolicy(duration="5s"),
                    retry=RetryPolicy(max_attempts=1, delay="100ms"),
                    hedge=HedgePolicy(delay="200ms", max_count=2),
                ),
            ),
        ]
