"""eRPC provider shortcut dataclasses.

Provider shortcuts let you add well-known RPC providers with minimal
configuration — typically just an API key. Each provider maps to the
eRPC ``ProviderConfig`` YAML schema with ``vendor`` and ``settings``.

Examples:
    >>> from erpc.providers import AlchemyProvider
    >>> provider = AlchemyProvider(api_key="your-key")
    >>> provider.to_dict()
    {'vendor': 'alchemy', 'settings': {'apiKey': 'your-key'}}

"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Provider(ABC):
    """Base class for eRPC provider shortcuts.

    All providers serialize to a dictionary matching the eRPC
    ``ProviderConfig`` Go struct: ``vendor``, ``settings``, and
    optional network filters.

    Attributes:
        only_networks: Restrict provider to these networks (e.g. ``["evm:1"]``).
        ignore_networks: Exclude these networks from the provider.

    """

    only_networks: list[str] = field(default_factory=list)
    ignore_networks: list[str] = field(default_factory=list)

    @property
    @abstractmethod
    def provider_type(self) -> str:
        """Vendor name for eRPC configuration."""

    def _settings(self) -> dict[str, Any]:
        """Build the vendor-specific settings dict.

        Returns:
            Dictionary of vendor settings. Empty dict if no settings needed.

        """
        return {}

    def to_dict(self) -> dict[str, Any]:
        """Serialize to an eRPC-compatible provider config dictionary.

        Returns:
            Dictionary with ``vendor``, optional ``settings``,
            ``onlyNetworks``, and ``ignoreNetworks`` keys.

        Examples:
            >>> AlchemyProvider(api_key="k").to_dict()
            {'vendor': 'alchemy', 'settings': {'apiKey': 'k'}}

        """
        d: dict[str, Any] = {"vendor": self.provider_type}
        settings = self._settings()
        if settings:
            d["settings"] = settings
        if self.only_networks:
            d["onlyNetworks"] = self.only_networks
        if self.ignore_networks:
            d["ignoreNetworks"] = self.ignore_networks
        return d


# --- API Key Providers ---


@dataclass
class AlchemyProvider(Provider):
    """Alchemy RPC provider shortcut.

    Attributes:
        api_key: Alchemy API key.

    Examples:
        >>> AlchemyProvider(api_key="demo").to_dict()
        {'vendor': 'alchemy', 'settings': {'apiKey': 'demo'}}

    """

    api_key: str = ""

    @property
    def provider_type(self) -> str:
        """Vendor name for eRPC configuration."""
        return "alchemy"

    def _settings(self) -> dict[str, Any]:
        return {"apiKey": self.api_key}


@dataclass
class InfuraProvider(Provider):
    """Infura RPC provider shortcut.

    Attributes:
        api_key: Infura API key.

    Examples:
        >>> InfuraProvider(api_key="demo").to_dict()
        {'vendor': 'infura', 'settings': {'apiKey': 'demo'}}

    """

    api_key: str = ""

    @property
    def provider_type(self) -> str:
        """Vendor name for eRPC configuration."""
        return "infura"

    def _settings(self) -> dict[str, Any]:
        return {"apiKey": self.api_key}


@dataclass
class DrpcProvider(Provider):
    """dRPC provider shortcut.

    Attributes:
        api_key: dRPC API key.

    Examples:
        >>> DrpcProvider(api_key="demo").to_dict()
        {'vendor': 'drpc', 'settings': {'apiKey': 'demo'}}

    """

    api_key: str = ""

    @property
    def provider_type(self) -> str:
        """Vendor name for eRPC configuration."""
        return "drpc"

    def _settings(self) -> dict[str, Any]:
        return {"apiKey": self.api_key}


@dataclass
class BlastAPIProvider(Provider):
    """BlastAPI provider shortcut.

    Attributes:
        api_key: BlastAPI key.

    Examples:
        >>> BlastAPIProvider(api_key="demo").to_dict()
        {'vendor': 'blastapi', 'settings': {'apiKey': 'demo'}}

    """

    api_key: str = ""

    @property
    def provider_type(self) -> str:
        """Vendor name for eRPC configuration."""
        return "blastapi"

    def _settings(self) -> dict[str, Any]:
        return {"apiKey": self.api_key}


@dataclass
class DwellirProvider(Provider):
    """Dwellir provider shortcut.

    Attributes:
        api_key: Dwellir API key.

    """

    api_key: str = ""

    @property
    def provider_type(self) -> str:
        """Vendor name for eRPC configuration."""
        return "dwellir"

    def _settings(self) -> dict[str, Any]:
        return {"apiKey": self.api_key}


@dataclass
class ConduitProvider(Provider):
    """Conduit provider shortcut.

    Attributes:
        api_key: Conduit API key.

    """

    api_key: str = ""

    @property
    def provider_type(self) -> str:
        """Vendor name for eRPC configuration."""
        return "conduit"

    def _settings(self) -> dict[str, Any]:
        return {"apiKey": self.api_key}


@dataclass
class ChainstackProvider(Provider):
    """Chainstack provider shortcut.

    Attributes:
        api_key: Chainstack API key.

    """

    api_key: str = ""

    @property
    def provider_type(self) -> str:
        """Vendor name for eRPC configuration."""
        return "chainstack"

    def _settings(self) -> dict[str, Any]:
        return {"apiKey": self.api_key}


@dataclass
class OnFinalityProvider(Provider):
    """OnFinality provider shortcut.

    Attributes:
        api_key: OnFinality API key.

    """

    api_key: str = ""

    @property
    def provider_type(self) -> str:
        """Vendor name for eRPC configuration."""
        return "onfinality"

    def _settings(self) -> dict[str, Any]:
        return {"apiKey": self.api_key}


@dataclass
class TenderlyProvider(Provider):
    """Tenderly provider shortcut.

    Attributes:
        api_key: Tenderly API key.

    """

    api_key: str = ""

    @property
    def provider_type(self) -> str:
        """Vendor name for eRPC configuration."""
        return "tenderly"

    def _settings(self) -> dict[str, Any]:
        return {"apiKey": self.api_key}


@dataclass
class BlockPiProvider(Provider):
    """BlockPi provider shortcut.

    Attributes:
        api_key: BlockPi API key.

    """

    api_key: str = ""

    @property
    def provider_type(self) -> str:
        """Vendor name for eRPC configuration."""
        return "blockpi"

    def _settings(self) -> dict[str, Any]:
        return {"apiKey": self.api_key}


@dataclass
class AnkrProvider(Provider):
    """Ankr provider shortcut.

    Attributes:
        api_key: Ankr API key.

    """

    api_key: str = ""

    @property
    def provider_type(self) -> str:
        """Vendor name for eRPC configuration."""
        return "ankr"

    def _settings(self) -> dict[str, Any]:
        return {"apiKey": self.api_key}


@dataclass
class QuickNodeProvider(Provider):
    """QuickNode provider shortcut.

    Attributes:
        api_key: QuickNode API key.

    """

    api_key: str = ""

    @property
    def provider_type(self) -> str:
        """Vendor name for eRPC configuration."""
        return "quicknode"

    def _settings(self) -> dict[str, Any]:
        return {"apiKey": self.api_key}


@dataclass
class RouteMeshProvider(Provider):
    """RouteMesh provider shortcut.

    Attributes:
        api_key: RouteMesh API key.

    """

    api_key: str = ""

    @property
    def provider_type(self) -> str:
        """Vendor name for eRPC configuration."""
        return "routemesh"

    def _settings(self) -> dict[str, Any]:
        return {"apiKey": self.api_key}


# --- Client ID Providers ---


@dataclass
class ThirdwebProvider(Provider):
    """Thirdweb provider shortcut.

    Attributes:
        client_id: Thirdweb client ID.

    Examples:
        >>> ThirdwebProvider(client_id="my-id").to_dict()
        {'vendor': 'thirdweb', 'settings': {'clientId': 'my-id'}}

    """

    client_id: str = ""

    @property
    def provider_type(self) -> str:
        """Vendor name for eRPC configuration."""
        return "thirdweb"

    def _settings(self) -> dict[str, Any]:
        return {"clientId": self.client_id}


# --- Endpoint Providers ---


@dataclass
class EnvioProvider(Provider):
    """Envio HyperRPC provider shortcut.

    Attributes:
        endpoint: Envio RPC endpoint URL.

    Examples:
        >>> EnvioProvider(endpoint="https://rpc.hypersync.xyz").to_dict()
        {'vendor': 'envio', 'settings': {'endpoint': 'https://rpc.hypersync.xyz'}}

    """

    endpoint: str = ""

    @property
    def provider_type(self) -> str:
        """Vendor name for eRPC configuration."""
        return "envio"

    def _settings(self) -> dict[str, Any]:
        return {"endpoint": self.endpoint}


@dataclass
class PimlicoProvider(Provider):
    """Pimlico account-abstraction provider shortcut.

    Attributes:
        endpoint: Pimlico RPC endpoint URL.

    """

    endpoint: str = ""

    @property
    def provider_type(self) -> str:
        """Vendor name for eRPC configuration."""
        return "pimlico"

    def _settings(self) -> dict[str, Any]:
        return {"endpoint": self.endpoint}


@dataclass
class EtherspotProvider(Provider):
    """Etherspot account-abstraction provider shortcut.

    Attributes:
        endpoint: Etherspot RPC endpoint URL.

    """

    endpoint: str = ""

    @property
    def provider_type(self) -> str:
        """Vendor name for eRPC configuration."""
        return "etherspot"

    def _settings(self) -> dict[str, Any]:
        return {"endpoint": self.endpoint}


# --- No-Key Providers ---


@dataclass
class SuperchainProvider(Provider):
    """Superchain registry provider shortcut.

    Adds all chains from the Optimism superchain registry.
    No credentials required.

    Examples:
        >>> SuperchainProvider().to_dict()
        {'vendor': 'superchain'}

    """

    @property
    def provider_type(self) -> str:
        """Vendor name for eRPC configuration."""
        return "superchain"


# --- Repository Provider ---


@dataclass
class RepositoryProvider(Provider):
    """Public endpoint repository provider.

    Automatically adds public RPC endpoints for 2,000+ EVM chains
    from a remote JSON repository.

    Attributes:
        url: Custom repository URL. ``None`` uses the eRPC default.

    Examples:
        >>> RepositoryProvider().to_dict()
        {'vendor': 'repository'}
        >>> RepositoryProvider(url="https://custom.repo/endpoints.json").to_dict()
        {'vendor': 'repository', 'settings': {'url': 'https://custom.repo/endpoints.json'}}

    """

    url: str | None = None

    @property
    def provider_type(self) -> str:
        """Vendor name for eRPC configuration."""
        return "repository"

    def _settings(self) -> dict[str, Any]:
        if self.url is not None:
            return {"url": self.url}
        return {}
