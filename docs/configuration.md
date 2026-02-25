# Configuration Guide

erpc.py generates valid `erpc.yaml` configuration from Python dataclasses. Every config section has a corresponding Python class.

## ERPCConfig — The Top-Level Object

```python
from erpc import ERPCConfig

config = ERPCConfig(
    project_id="my-project",
    upstreams={
        1: ["https://eth.llamarpc.com", "https://rpc.ankr.com/eth"],
        137: ["https://polygon-rpc.com"],
    },
    server_port=4000,
    metrics_port=4001,
    log_level="info",
)

# Write to file
config.write("erpc.yaml")

# Get YAML string
yaml_str = config.to_yaml()

# Get endpoint URL for a chain
url = config.endpoint_url(1)
# → http://127.0.0.1:4000/my-project/evm/1
```

## Networks

Configure per-chain policies using `NetworkConfig`:

```python
from erpc.networks import NetworkConfig
from erpc.failsafe import FailsafeConfig, RetryPolicy, TimeoutPolicy

networks = [
    NetworkConfig(
        architecture="evm",
        chain_id=1,
        failsafe=FailsafeConfig(
            timeout=TimeoutPolicy(duration="15s"),
            retry=RetryPolicy(max_attempts=3, delay="1s"),
        ),
    ),
]

config = ERPCConfig(
    upstreams={1: ["https://eth.llamarpc.com"]},
    networks=networks,
)
```

## Upstreams

### Simple Upstreams

The quickest way — just map chain IDs to URLs:

```python
config = ERPCConfig(
    upstreams={
        1: ["https://eth.llamarpc.com"],
        137: ["https://polygon-rpc.com"],
    },
)
```

### Rich Upstream Configs

For full control, use `UpstreamConfig`:

```python
from erpc.upstreams import UpstreamConfig

config = ERPCConfig(
    rich_upstreams=[
        UpstreamConfig(
            id="alchemy-eth",
            endpoint="https://eth-mainnet.g.alchemy.com/v2/YOUR_KEY",
            chain_ids=[1],
            allowed_methods=["eth_call", "eth_getBalance"],
        ),
    ],
)
```

### Upstream Defaults

Apply default settings to all upstreams:

```python
from erpc.upstreams import UpstreamConfig

config = ERPCConfig(
    upstreams={1: ["https://eth.llamarpc.com"]},
    upstream_defaults=UpstreamConfig(
        allowed_methods=["eth_*"],
    ),
)
```

## Cache

Configure the in-memory cache:

```python
from erpc import CacheConfig

config = ERPCConfig(
    upstreams={1: ["https://eth.llamarpc.com"]},
    cache=CacheConfig(
        max_items=50_000,
        method_ttls={
            "eth_getBlockByNumber": 3600,
            "eth_chainId": 0,  # 0 = cache forever
        },
    ),
)
```

## Failsafe Policies

Configure retry, timeout, circuit breaker, and hedge policies:

```python
from erpc.failsafe import (
    FailsafeConfig,
    RetryPolicy,
    TimeoutPolicy,
    CircuitBreakerPolicy,
    HedgePolicy,
)

failsafe = FailsafeConfig(
    timeout=TimeoutPolicy(duration="30s"),
    retry=RetryPolicy(max_attempts=3, delay="1s", backoff_max_delay="10s"),
    circuit_breaker=CircuitBreakerPolicy(
        failure_threshold_count=5,
        success_threshold_count=3,
        half_open_after="30s",
    ),
    hedge=HedgePolicy(delay="5s", max_count=2),
)
```

!!! tip "Presets"
    Use `FailsafePresets` for common configurations:
    ```python
    from erpc.failsafe import FailsafePresets

    failsafe = FailsafePresets.aggressive()
    ```

## Rate Limiters

Control request rates per upstream or globally:

```python
from erpc.rate_limiters import RateLimiterConfig, RateLimitBudget, RateLimitRule

config = ERPCConfig(
    upstreams={1: ["https://eth.llamarpc.com"]},
    rate_limiters=RateLimiterConfig(
        budgets=[
            RateLimitBudget(
                id="global-limit",
                rules=[
                    RateLimitRule(method="*", max_count=100, period="1s"),
                ],
            ),
        ],
    ),
)
```

### Rate Limiter Stores

```python
from erpc.rate_limiters import MemoryStore, RedisStore

# In-memory (default)
store = MemoryStore(max_items=10_000)

# Redis-backed for distributed setups
store = RedisStore(addr="localhost:6379", db=1)
```

### Auto-Tuning

```python
from erpc.rate_limiters import AutoTuneConfig

auto_tune = AutoTuneConfig(
    enabled=True,
    adjustment_period="60s",
    error_rate_threshold=0.1,
    increase_factor=1.1,
    decrease_factor=0.9,
)
```

## Auth

Protect your eRPC instance with authentication:

```python
from erpc import AuthConfig, SecretAuth, JWTAuth, SIWEAuth, NetworkAuth

# Simple secret key
auth = AuthConfig(
    strategies=[SecretAuth(value="my-secret-key")],
)

# JWT authentication
auth = AuthConfig(
    strategies=[
        JWTAuth(
            verification_keys=[{"key": "your-public-key"}],
        ),
    ],
)

# Multiple strategies
auth = AuthConfig(
    strategies=[
        SecretAuth(value="admin-key"),
        NetworkAuth(allowed_ips=["10.0.0.0/8"]),
    ],
)

config = ERPCConfig(
    upstreams={1: ["https://eth.llamarpc.com"]},
    auth=auth,
)
```

## Providers

Use built-in provider presets for popular RPC services:

```python
from erpc import AlchemyProvider, InfuraProvider, ERPCConfig

config = ERPCConfig(
    upstreams={1: ["https://eth.llamarpc.com"]},
    providers=[
        AlchemyProvider(api_key="your-alchemy-key"),
        InfuraProvider(api_key="your-infura-key"),
    ],
)
```

20+ providers supported: Alchemy, Ankr, BlastAPI, BlockPi, Chainstack, Conduit, DRPC, Dwellir, Envio, Etherspot, Infura, OnFinality, Pimlico, QuickNode, Repository, RouteMesh, Superchain, Tenderly, Thirdweb.

## Database

Configure persistent storage for caching and state:

```python
from erpc import DatabaseConfig, RedisConnector, PostgresConnector

# Redis
db = DatabaseConfig(
    evm_json_rpc_cache=RedisConnector(addr="localhost:6379"),
)

# PostgreSQL
db = DatabaseConfig(
    evm_json_rpc_cache=PostgresConnector(
        connection_uri="postgresql://user:pass@localhost:5432/erpc",
    ),
)

config = ERPCConfig(
    upstreams={1: ["https://eth.llamarpc.com"]},
    database=db,
)
```

### Available Connectors

- **`RedisConnector`** — Redis/Valkey with TLS and auth support
- **`PostgresConnector`** — PostgreSQL
- **`DynamoDBConnector`** — AWS DynamoDB
- **`MemoryConnector`** — In-process memory (default)

### Cache Policies

```python
from erpc.database import CachePolicy

policy = CachePolicy(
    network="evm:1",
    method="eth_getBlockByNumber",
    finality_state="finalized",
    ttl=3600,
)
```

## Server Config

Configure CORS, timeouts, and binding:

```python
from erpc.server import ServerConfig, MetricsConfig

config = ERPCConfig(
    upstreams={1: ["https://eth.llamarpc.com"]},
    server=ServerConfig(
        host="0.0.0.0",
        port=4000,
    ),
    metrics=MetricsConfig(
        host="0.0.0.0",
        port=4001,
    ),
)
```

## Dynamic Config Updates

Update configuration at runtime without restarting:

```python
from erpc.dynamic import add_upstream, remove_upstream, update_config

# Add an upstream
diff = add_upstream("erpc.yaml", chain_id=1, url="https://new-rpc.example.com")

# Remove an upstream
diff = remove_upstream("erpc.yaml", chain_id=1, url="https://old-rpc.example.com")

# Atomic config write (safe for concurrent access)
from erpc.dynamic import atomic_write_config
atomic_write_config("erpc.yaml", config)
```
