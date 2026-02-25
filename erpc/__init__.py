"""erpc.py — Python subprocess manager for eRPC."""

from erpc.auth import AuthConfig, JWTAuth, NetworkAuth, SecretAuth, SIWEAuth
from erpc.config import CacheConfig, ERPCConfig
from erpc.database import (
    CachePolicy,
    CompressionConfig,
    DatabaseConfig,
    DynamoDBConnector,
    MemoryConnector,
    PostgresConnector,
    RedisConnector,
    TLSConfig,
)
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
from erpc.server import CORSConfig, MetricsConfig, ServerConfig
from erpc.exceptions import (
    ERPCConfigError,
    ERPCError,
    ERPCHealthCheckError,
    ERPCNotFound,
    ERPCNotRunning,
    ERPCStartupError,
)
from erpc.logging import ERPCLogStream
from erpc.mixins import LoggingMixin
from erpc.monitoring import HealthEvent, HealthMonitor, HealthStatus
from erpc.process import ERPCProcess

__all__ = [
    "AlchemyProvider",
    "AnkrProvider",
    "AuthConfig",
    "BlastAPIProvider",
    "BlockPiProvider",
    "CORSConfig",
    "CacheConfig",
    "CachePolicy",
    "ChainstackProvider",
    "CompressionConfig",
    "ConduitProvider",
    "DatabaseConfig",
    "DrpcProvider",
    "DwellirProvider",
    "DynamoDBConnector",
    "EnvioProvider",
    "ERPCConfig",
    "ERPCConfigError",
    "ERPCError",
    "ERPCHealthCheckError",
    "ERPCLogStream",
    "ERPCNotFound",
    "ERPCNotRunning",
    "ERPCProcess",
    "ERPCStartupError",
    "EtherspotProvider",
    "HealthEvent",
    "HealthMonitor",
    "HealthStatus",
    "InfuraProvider",
    "JWTAuth",
    "LoggingMixin",
    "MemoryConnector",
    "MetricsConfig",
    "NetworkAuth",
    "OnFinalityProvider",
    "PimlicoProvider",
    "PostgresConnector",
    "Provider",
    "QuickNodeProvider",
    "RedisConnector",
    "RepositoryProvider",
    "RouteMeshProvider",
    "SecretAuth",
    "SIWEAuth",
    "ServerConfig",
    "SuperchainProvider",
    "TenderlyProvider",
    "ThirdwebProvider",
    "TLSConfig",
]

__version__ = "0.1.0"
