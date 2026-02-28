"""erpc.py — Python subprocess manager for eRPC."""

from erpc.async_process import AsyncERPCProcess
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
from erpc.docker import DockerERPCProcess
from erpc.dynamic import (
    ConfigDiff,
    add_upstream,
    atomic_write_config,
    remove_upstream,
    update_config,
)
from erpc.errors import ErrorInfo, parse_rpc_error
from erpc.exceptions import (
    ERPCConfigError,
    ERPCError,
    ERPCHealthCheckError,
    ERPCNotFound,
    ERPCNotRunning,
    ERPCStartupError,
)
from erpc.failsafe import (
    CircuitBreakerPolicy,
    FailsafeConfig,
    FailsafePresets,
    HedgePolicy,
    MethodFailsafeConfig,
    RetryPolicy,
    TimeoutPolicy,
)
from erpc.install import install_erpc
from erpc.logging import ERPCLogStream
from erpc.mixins import LoggingMixin
from erpc.monitoring import HealthEvent, HealthMonitor, HealthStatus
from erpc.process import ERPCProcess
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
from erpc.rate_limiters import (
    AutoTuneConfig,
    MemoryStore,
    RateLimitBudget,
    RateLimiterConfig,
    RateLimitRule,
    RedisStore,
)
from erpc.server import CORSConfig, MetricsConfig, ServerConfig

__all__ = [
    "AlchemyProvider",
    "AnkrProvider",
    "AsyncERPCProcess",
    "AuthConfig",
    "AutoTuneConfig",
    "BlastAPIProvider",
    "BlockPiProvider",
    "CORSConfig",
    "CacheConfig",
    "CachePolicy",
    "ChainstackProvider",
    "CircuitBreakerPolicy",
    "CompressionConfig",
    "ConduitProvider",
    "ConfigDiff",
    "DatabaseConfig",
    "DockerERPCProcess",
    "DrpcProvider",
    "DwellirProvider",
    "DynamoDBConnector",
    "ERPCConfig",
    "ERPCConfigError",
    "ERPCError",
    "ERPCErrorParser",
    "ERPCHealthCheckError",
    "ERPCLogStream",
    "ERPCNotFound",
    "ERPCNotRunning",
    "ERPCProcess",
    "ERPCStartupError",
    "ERPCUpstreamError",
    "EnvioProvider",
    "ErrorInfo",
    "EtherspotProvider",
    "FailsafeConfig",
    "FailsafePresets",
    "HealthEvent",
    "HealthMonitor",
    "HealthStatus",
    "HedgePolicy",
    "InfuraProvider",
    "JWTAuth",
    "LoggingMixin",
    "MemoryConnector",
    "MemoryStore",
    "MethodFailsafeConfig",
    "MetricsConfig",
    "NetworkAuth",
    "OnFinalityProvider",
    "PimlicoProvider",
    "PostgresConnector",
    "Provider",
    "QuickNodeProvider",
    "RateLimitBudget",
    "RateLimitRule",
    "RateLimiterConfig",
    "RedisConnector",
    "RedisStore",
    "RepositoryProvider",
    "RetryPolicy",
    "RouteMeshProvider",
    "SIWEAuth",
    "SecretAuth",
    "ServerConfig",
    "SuperchainProvider",
    "TLSConfig",
    "TenderlyProvider",
    "ThirdwebProvider",
    "TimeoutPolicy",
    "add_upstream",
    "atomic_write_config",
    "install_erpc",
    "parse_rpc_error",
    "remove_upstream",
    "update_config",
]

#: The eRPC binary version this release of erpc.py is tested and compatible with.
#: All CI, integration tests, and config generation target this version.
ERPC_VERSION = "0.0.62"

__version__ = "0.1.0b3"
