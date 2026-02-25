# API Reference

Auto-generated API documentation for all erpc.py modules.

## Core

- [Config](config.md) — `ERPCConfig`, `CacheConfig`
- [Process](process.md) — `ERPCProcess`, `find_erpc_binary`
- [Docker](docker.md) — `DockerERPCProcess`
- [Client](client.md) — `ERPCClient`, `HealthStatus`
- [Monitoring](monitoring.md) — `HealthMonitor`, `HealthEvent`
- [Install](install.md) — `install_erpc`

## Configuration

- [Auth](auth.md) — `AuthConfig`, `SecretAuth`, `JWTAuth`, `SIWEAuth`, `NetworkAuth`
- [Database](database.md) — `DatabaseConfig`, connectors
- [Failsafe](failsafe.md) — Retry, timeout, circuit breaker, hedge policies
- [Rate Limiters](rate-limiters.md) — Rate limiting config and stores
- [Networks](networks.md) — Per-chain network configuration
- [Upstreams](upstreams.md) — Upstream endpoint configuration
- [Providers](providers.md) — Provider presets (Alchemy, Infura, etc.)
- [Server](server.md) — Server and metrics configuration

## Utilities

- [Dynamic](dynamic.md) — Runtime config updates
- [Exceptions](exceptions.md) — Error types
- [CLI](cli.md) — CLI internals
