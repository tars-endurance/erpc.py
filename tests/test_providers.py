"""Tests for eRPC provider shortcuts."""

from __future__ import annotations

import pytest

from erpc.providers import (
    AlchemyProvider,
    AnkrProvider,
    BlastAPIProvider,
    BlockPiProvider,
    ChainstackProvider,
    ConduitProvider,
    DrpcProvider,
    DwellirProvider,
    EnvioProvider,
    EtherspotProvider,
    InfuraProvider,
    OnFinalityProvider,
    PimlicoProvider,
    Provider,
    QuickNodeProvider,
    RepositoryProvider,
    RouteMeshProvider,
    SuperchainProvider,
    TenderlyProvider,
    ThirdwebProvider,
)


class TestProviderBase:
    """Tests for the Provider base class."""

    def test_provider_is_abstract(self) -> None:
        """Provider base cannot be instantiated without provider_type."""
        # Provider is a base; subclasses must set provider_type
        with pytest.raises(TypeError):
            Provider()  # type: ignore[abstract]


class TestAPIKeyProviders:
    """Tests for providers that accept an API key."""

    @pytest.mark.parametrize(
        ("cls", "vendor", "key"),
        [
            (AlchemyProvider, "alchemy", "abc123"),
            (InfuraProvider, "infura", "inf-key"),
            (DrpcProvider, "drpc", "drpc-key"),
            (BlastAPIProvider, "blastapi", "blast-key"),
            (DwellirProvider, "dwellir", "dw-key"),
            (ConduitProvider, "conduit", "cd-key"),
            (ChainstackProvider, "chainstack", "cs-key"),
            (OnFinalityProvider, "onfinality", "of-key"),
            (TenderlyProvider, "tenderly", "td-key"),
            (BlockPiProvider, "blockpi", "bp-key"),
            (AnkrProvider, "ankr", "ankr-key"),
            (QuickNodeProvider, "quicknode", "qn-key"),
            (RouteMeshProvider, "routemesh", "rm-key"),
        ],
    )
    def test_api_key_provider_to_dict(
        self, cls: type[Provider], vendor: str, key: str
    ) -> None:
        """API key providers serialize with vendor and settings.apiKey."""
        provider = cls(api_key=key)  # type: ignore[call-arg]
        result = provider.to_dict()
        assert result["vendor"] == vendor
        assert result["settings"]["apiKey"] == key

    def test_alchemy_provider_attributes(self) -> None:
        """AlchemyProvider stores api_key correctly."""
        p = AlchemyProvider(api_key="test-key")
        assert p.api_key == "test-key"
        assert p.provider_type == "alchemy"


class TestClientIdProviders:
    """Tests for providers that accept a client ID."""

    def test_thirdweb_provider(self) -> None:
        """ThirdwebProvider serializes with clientId setting."""
        p = ThirdwebProvider(client_id="tw-client")
        result = p.to_dict()
        assert result["vendor"] == "thirdweb"
        assert result["settings"]["clientId"] == "tw-client"


class TestEndpointProviders:
    """Tests for providers that accept an endpoint URL."""

    @pytest.mark.parametrize(
        ("cls", "vendor", "endpoint"),
        [
            (EnvioProvider, "envio", "https://rpc.hypersync.xyz"),
            (PimlicoProvider, "pimlico", "https://api.pimlico.io/v2"),
            (EtherspotProvider, "etherspot", "https://api.etherspot.io"),
        ],
    )
    def test_endpoint_provider_to_dict(
        self, cls: type[Provider], vendor: str, endpoint: str
    ) -> None:
        """Endpoint providers serialize with vendor and settings.endpoint."""
        provider = cls(endpoint=endpoint)  # type: ignore[call-arg]
        result = provider.to_dict()
        assert result["vendor"] == vendor
        assert result["settings"]["endpoint"] == endpoint


class TestNoKeyProviders:
    """Tests for providers that need no credentials."""

    def test_superchain_provider(self) -> None:
        """SuperchainProvider serializes with no settings."""
        p = SuperchainProvider()
        result = p.to_dict()
        assert result["vendor"] == "superchain"
        assert "settings" not in result or result.get("settings") == {}


class TestRepositoryProvider:
    """Tests for the special repository provider."""

    def test_repository_default_url(self) -> None:
        """RepositoryProvider with no URL uses default."""
        p = RepositoryProvider()
        result = p.to_dict()
        assert result["vendor"] == "repository"
        assert "settings" not in result or result.get("settings", {}).get("url") is None

    def test_repository_custom_url(self) -> None:
        """RepositoryProvider with custom URL includes it in settings."""
        p = RepositoryProvider(url="https://custom.repo/endpoints.json")
        result = p.to_dict()
        assert result["vendor"] == "repository"
        assert result["settings"]["url"] == "https://custom.repo/endpoints.json"


class TestProviderOptionalFields:
    """Tests for optional provider configuration fields."""

    def test_only_networks(self) -> None:
        """Providers can restrict to specific networks."""
        p = AlchemyProvider(api_key="k", only_networks=["evm:1", "evm:137"])
        result = p.to_dict()
        assert result["onlyNetworks"] == ["evm:1", "evm:137"]

    def test_ignore_networks(self) -> None:
        """Providers can ignore specific networks."""
        p = AlchemyProvider(api_key="k", ignore_networks=["evm:56"])
        result = p.to_dict()
        assert result["ignoreNetworks"] == ["evm:56"]

    def test_optional_fields_omitted_by_default(self) -> None:
        """Optional fields are not present when not set."""
        p = AlchemyProvider(api_key="k")
        result = p.to_dict()
        assert "onlyNetworks" not in result
        assert "ignoreNetworks" not in result


class TestProviderIntegration:
    """Tests for provider integration with ERPCConfig."""

    def test_providers_in_config_yaml(self) -> None:
        """Providers appear in the project config when set."""
        from erpc.config import ERPCConfig

        providers = [
            AlchemyProvider(api_key="alchemy-key"),
            InfuraProvider(api_key="infura-key"),
        ]
        config = ERPCConfig(providers=providers)
        yaml_str = config.to_yaml()
        assert "alchemy" in yaml_str
        assert "infura" in yaml_str
        assert "alchemy-key" in yaml_str

    def test_multiple_providers_in_project(self) -> None:
        """Multiple providers serialize correctly in project dict."""
        from erpc.config import ERPCConfig

        providers = [
            AlchemyProvider(api_key="a"),
            DrpcProvider(api_key="d"),
            SuperchainProvider(),
            RepositoryProvider(),
        ]
        config = ERPCConfig(providers=providers)
        yaml_str = config.to_yaml()
        assert "alchemy" in yaml_str
        assert "drpc" in yaml_str
        assert "superchain" in yaml_str
        assert "repository" in yaml_str
