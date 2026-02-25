"""eRPC authentication configuration dataclasses.

Maps the eRPC auth strategy surface to Python dataclasses. Each strategy
type corresponds to a supported eRPC authentication method: secret tokens,
JWT verification, Sign-In with Ethereum (SIWE), and network-level IP filtering.

Examples:
    >>> from erpc.auth import AuthConfig, SecretAuth, SIWEAuth
    >>> auth = AuthConfig(
    ...     strategies=[
    ...         SecretAuth(value="my-api-key", rate_limit_budget="free-tier"),
    ...         SIWEAuth(rate_limit_budget="wallet-tier"),
    ...     ]
    ... )
    >>> auth.to_dict()["strategies"][0]["type"]
    'secret'

"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _omit_none(d: dict[str, Any]) -> dict[str, Any]:
    """Remove keys with ``None`` values from a dictionary.

    Args:
        d: Input dictionary.

    Returns:
        New dictionary with ``None`` values removed.

    """
    return {k: v for k, v in d.items() if v is not None}


@dataclass
class AuthStrategy:
    """Base class for eRPC authentication strategies.

    Subclasses must set ``strategy_type`` and implement ``to_dict()``.

    Attributes:
        strategy_type: The eRPC strategy type identifier.

    """

    strategy_type: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to an eRPC-compatible dictionary.

        Returns:
            Dictionary matching the eRPC auth strategy YAML schema.

        Raises:
            NotImplementedError: If called on the base class directly.

        """
        raise NotImplementedError


@dataclass
class SecretAuth(AuthStrategy):
    """Secret token authentication strategy.

    Authenticates requests via a shared secret value (e.g., API key).

    Attributes:
        value: The secret token value.
        rate_limit_budget: Optional rate limit budget name to apply.

    Examples:
        >>> auth = SecretAuth(value="my-key")
        >>> auth.to_dict()
        {'type': 'secret', 'secret': {'value': 'my-key'}}

    """

    strategy_type: str = field(default="secret", init=False, repr=False)
    value: str = ""
    rate_limit_budget: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to an eRPC-compatible dictionary.

        Returns:
            Dictionary with ``type``, ``secret``, and optional ``rateLimitBudget``.

        """
        d: dict[str, Any] = {
            "type": "secret",
            "secret": {"value": self.value},
        }
        if self.rate_limit_budget is not None:
            d["rateLimitBudget"] = self.rate_limit_budget
        return d


@dataclass
class JWTAuth(AuthStrategy):
    """JWT (JSON Web Token) authentication strategy.

    Verifies JWTs using public keys and extracts rate limit budget
    from a configurable claim.

    Attributes:
        verification_keys: List of key configs (algorithm + publicKeyPem).
        rate_limit_budget_claim_name: JWT claim name containing the budget identifier.
        allowed_issuers: Optional whitelist of token issuers.
        allowed_audiences: Optional whitelist of token audiences.

    Examples:
        >>> keys = [{"algorithm": "RS256", "publicKeyPem": "..."}]
        >>> auth = JWTAuth(verification_keys=keys, rate_limit_budget_claim_name="plan")
        >>> auth.to_dict()["type"]
        'jwt'

    """

    strategy_type: str = field(default="jwt", init=False, repr=False)
    verification_keys: list[dict[str, Any]] = field(default_factory=list)
    rate_limit_budget_claim_name: str = ""
    allowed_issuers: list[str] | None = None
    allowed_audiences: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to an eRPC-compatible dictionary.

        Returns:
            Dictionary with ``type`` and ``jwt`` containing verification config.

        """
        jwt_config: dict[str, Any] = {
            "verificationKeys": self.verification_keys,
            "rateLimitBudgetClaimName": self.rate_limit_budget_claim_name,
        }
        if self.allowed_issuers is not None:
            jwt_config["allowedIssuers"] = self.allowed_issuers
        if self.allowed_audiences is not None:
            jwt_config["allowedAudiences"] = self.allowed_audiences
        return {"type": "jwt", "jwt": jwt_config}


@dataclass
class SIWEAuth(AuthStrategy):
    """Sign-In with Ethereum (SIWE) authentication strategy.

    Authenticates requests using EIP-4361 signed messages.

    Attributes:
        rate_limit_budget: Optional rate limit budget name to apply.

    Examples:
        >>> auth = SIWEAuth(rate_limit_budget="wallet-tier")
        >>> auth.to_dict()
        {'type': 'siwe', 'rateLimitBudget': 'wallet-tier'}

    """

    strategy_type: str = field(default="siwe", init=False, repr=False)
    rate_limit_budget: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to an eRPC-compatible dictionary.

        Returns:
            Dictionary with ``type`` and optional ``rateLimitBudget``.

        """
        d: dict[str, Any] = {"type": "siwe"}
        if self.rate_limit_budget is not None:
            d["rateLimitBudget"] = self.rate_limit_budget
        return d


@dataclass
class NetworkAuth(AuthStrategy):
    """Network-level (IP-based) authentication strategy.

    Restricts access by source IP address or CIDR range.

    Attributes:
        rate_limit_budget: Optional rate limit budget name to apply.
        allowed_ips: Optional list of allowed IP addresses or CIDR ranges.

    Examples:
        >>> auth = NetworkAuth(allowed_ips=["10.0.0.0/8"])
        >>> auth.to_dict()
        {'type': 'network', 'network': {'allowedIPs': ['10.0.0.0/8']}}

    """

    strategy_type: str = field(default="network", init=False, repr=False)
    rate_limit_budget: str | None = None
    allowed_ips: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to an eRPC-compatible dictionary.

        Returns:
            Dictionary with ``type``, optional ``network``, and ``rateLimitBudget``.

        """
        d: dict[str, Any] = {"type": "network"}
        if self.allowed_ips is not None:
            d["network"] = {"allowedIPs": self.allowed_ips}
        if self.rate_limit_budget is not None:
            d["rateLimitBudget"] = self.rate_limit_budget
        return d


@dataclass
class AuthConfig:
    """Composable authentication configuration for an eRPC project.

    Combines multiple authentication strategies. Each strategy is tried
    in order until one succeeds.

    Attributes:
        strategies: Ordered list of authentication strategies.

    Examples:
        >>> config = AuthConfig(strategies=[SecretAuth(value="key")])
        >>> len(config.to_dict()["strategies"])
        1

    """

    strategies: list[AuthStrategy] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to an eRPC-compatible dictionary.

        Returns:
            Dictionary with ``strategies`` list of serialized strategy dicts.

        """
        return {"strategies": [s.to_dict() for s in self.strategies]}
