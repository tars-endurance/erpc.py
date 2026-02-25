"""Tests for eRPC authentication configuration dataclasses."""

from __future__ import annotations

from erpc.auth import (
    AuthConfig,
    JWTAuth,
    NetworkAuth,
    SecretAuth,
    SIWEAuth,
)


class TestSecretAuth:
    """Tests for SecretAuth strategy."""

    def test_construction(self) -> None:
        """SecretAuth stores value and defaults rateLimitBudget to None."""
        auth = SecretAuth(value="my-secret-key")
        assert auth.value == "my-secret-key"
        assert auth.rate_limit_budget is None

    def test_with_rate_limit_budget(self) -> None:
        """SecretAuth accepts an optional rate limit budget."""
        auth = SecretAuth(value="key", rate_limit_budget="free-tier")
        assert auth.rate_limit_budget == "free-tier"

    def test_serialization(self) -> None:
        """SecretAuth serializes to eRPC-compatible dict."""
        auth = SecretAuth(value="super-secret")
        result = auth.to_dict()
        assert result == {"type": "secret", "secret": {"value": "super-secret"}}

    def test_serialization_with_budget(self) -> None:
        """SecretAuth includes rateLimitBudget when set."""
        auth = SecretAuth(value="key", rate_limit_budget="premium")
        result = auth.to_dict()
        assert result == {
            "type": "secret",
            "secret": {"value": "key"},
            "rateLimitBudget": "premium",
        }


class TestJWTAuth:
    """Tests for JWTAuth strategy."""

    def test_construction_defaults(self) -> None:
        """JWTAuth stores keys and claim name, defaults optional fields to None."""
        keys = [{"algorithm": "RS256", "publicKeyPem": "-----BEGIN PUBLIC KEY-----"}]
        auth = JWTAuth(verification_keys=keys, rate_limit_budget_claim_name="plan")
        assert auth.verification_keys == keys
        assert auth.rate_limit_budget_claim_name == "plan"
        assert auth.allowed_issuers is None
        assert auth.allowed_audiences is None

    def test_with_issuers_and_audiences(self) -> None:
        """JWTAuth accepts allowed issuers and audiences."""
        auth = JWTAuth(
            verification_keys=[{"algorithm": "RS256", "publicKeyPem": "pem-data"}],
            rate_limit_budget_claim_name="tier",
            allowed_issuers=["https://auth.example.com"],
            allowed_audiences=["my-app"],
        )
        assert auth.allowed_issuers == ["https://auth.example.com"]
        assert auth.allowed_audiences == ["my-app"]

    def test_serialization(self) -> None:
        """JWTAuth serializes with verification keys and claim name."""
        keys = [{"algorithm": "RS256", "publicKeyPem": "pem-data"}]
        auth = JWTAuth(verification_keys=keys, rate_limit_budget_claim_name="plan")
        result = auth.to_dict()
        assert result == {
            "type": "jwt",
            "jwt": {
                "verificationKeys": keys,
                "rateLimitBudgetClaimName": "plan",
            },
        }

    def test_serialization_full(self) -> None:
        """JWTAuth serializes all optional fields when present."""
        keys = [{"algorithm": "ES256", "publicKeyPem": "ec-key"}]
        auth = JWTAuth(
            verification_keys=keys,
            rate_limit_budget_claim_name="tier",
            allowed_issuers=["https://issuer.io"],
            allowed_audiences=["app-1", "app-2"],
        )
        result = auth.to_dict()
        assert result["jwt"]["allowedIssuers"] == ["https://issuer.io"]
        assert result["jwt"]["allowedAudiences"] == ["app-1", "app-2"]


class TestSIWEAuth:
    """Tests for SIWEAuth (Sign-In with Ethereum) strategy."""

    def test_construction_defaults(self) -> None:
        """SIWEAuth defaults rateLimitBudget to None."""
        auth = SIWEAuth()
        assert auth.rate_limit_budget is None

    def test_serialization(self) -> None:
        """SIWEAuth serializes to minimal eRPC dict."""
        auth = SIWEAuth()
        assert auth.to_dict() == {"type": "siwe"}

    def test_serialization_with_budget(self) -> None:
        """SIWEAuth includes rateLimitBudget when set."""
        auth = SIWEAuth(rate_limit_budget="wallet-tier")
        assert auth.to_dict() == {"type": "siwe", "rateLimitBudget": "wallet-tier"}


class TestNetworkAuth:
    """Tests for NetworkAuth (IP-based) strategy."""

    def test_construction_defaults(self) -> None:
        """NetworkAuth defaults all optional fields to None."""
        auth = NetworkAuth()
        assert auth.rate_limit_budget is None
        assert auth.allowed_ips is None

    def test_with_allowed_ips(self) -> None:
        """NetworkAuth accepts a list of allowed IPs/CIDRs."""
        auth = NetworkAuth(allowed_ips=["10.0.0.0/8", "192.168.1.1"])
        assert auth.allowed_ips == ["10.0.0.0/8", "192.168.1.1"]

    def test_serialization(self) -> None:
        """NetworkAuth serializes to minimal eRPC dict."""
        auth = NetworkAuth()
        assert auth.to_dict() == {"type": "network"}

    def test_serialization_full(self) -> None:
        """NetworkAuth serializes all fields when present."""
        auth = NetworkAuth(rate_limit_budget="internal", allowed_ips=["10.0.0.0/8"])
        result = auth.to_dict()
        assert result == {
            "type": "network",
            "network": {"allowedIPs": ["10.0.0.0/8"]},
            "rateLimitBudget": "internal",
        }


class TestAuthConfig:
    """Tests for AuthConfig composing multiple strategies."""

    def test_empty_strategies(self) -> None:
        """AuthConfig can be created with no strategies."""
        config = AuthConfig(strategies=[])
        assert config.to_dict() == {"strategies": []}

    def test_multiple_strategies(self) -> None:
        """AuthConfig composes multiple strategy types."""
        config = AuthConfig(strategies=[
            SecretAuth(value="key-1", rate_limit_budget="free"),
            SIWEAuth(rate_limit_budget="wallet"),
            NetworkAuth(allowed_ips=["127.0.0.1"]),
        ])
        result = config.to_dict()
        assert len(result["strategies"]) == 3
        assert result["strategies"][0]["type"] == "secret"
        assert result["strategies"][1]["type"] == "siwe"
        assert result["strategies"][2]["type"] == "network"


class TestAuthStrategyBase:
    """Tests for AuthStrategy base class."""

    def test_strategy_type_attribute(self) -> None:
        """All strategies expose strategy_type."""
        assert SecretAuth(value="x").strategy_type == "secret"
        assert JWTAuth(
            verification_keys=[], rate_limit_budget_claim_name="p"
        ).strategy_type == "jwt"
        assert SIWEAuth().strategy_type == "siwe"
        assert NetworkAuth().strategy_type == "network"


class TestERPCConfigIntegration:
    """Integration tests: AuthConfig with ERPCConfig."""

    def test_auth_in_project_yaml(self) -> None:
        """AuthConfig integrates into ERPCConfig YAML output."""
        from erpc.config import ERPCConfig

        auth = AuthConfig(strategies=[
            SecretAuth(value="test-key"),
        ])
        config = ERPCConfig(
            upstreams={1: ["https://eth.llamarpc.com"]},
            auth=auth,
        )
        yaml_str = config.to_yaml()
        assert "auth" in yaml_str
        assert "secret" in yaml_str
        assert "test-key" in yaml_str
