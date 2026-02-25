# Project Context — erpc.py

## Project

- **Name:** erpc.py (package: `erpc-py`)
- **Language:** Python 3.10+
- **Purpose:** Subprocess manager for eRPC, a fault-tolerant EVM RPC proxy (Go binary)
- **Pattern:** Configure → serialize to YAML → spawn binary → health-check → manage lifecycle

## Stack

- **Runtime:** Python 3.10–3.13, pyyaml
- **Testing:** pytest, pytest-asyncio, pytest-cov
- **Quality:** mypy (strict), ruff
- **CI:** GitHub Actions

## Structure

```
erpc/                    # Source package
  process.py             # ERPCProcess — sync subprocess manager
  async_process.py       # AsyncERPCProcess — async subprocess manager
  docker.py              # DockerERPCProcess — Docker container manager
  config.py              # ERPCConfig — top-level config, YAML generation
  server.py              # ServerConfig, MetricsConfig
  networks.py            # NetworkConfig — chain definitions
  providers.py           # Provider — RPC endpoint configs
  upstreams.py           # UpstreamConfig
  failsafe.py            # Retry, timeout, hedge, circuit breaker policies
  rate_limiters.py       # Budget-based rate limiting
  database.py            # Cache/DB connectors (Redis, Postgres, DynamoDB, memory)
  auth.py                # JWT, SIWE, secret, network-level auth
  client.py              # ERPCClient — HTTP health/metrics client
  monitoring.py          # HealthMonitor — daemon-thread health watcher
  dynamic.py             # Runtime config mutation (add/remove upstreams)
  install.py             # Binary installer from GitHub releases
  cli.py                 # CLI entrypoint
  logging.py             # Logging configuration
  mixins.py              # Shared mixins
  exceptions.py          # ERPCError hierarchy
  version.py             # Version detection
tests/
  unit/                  # Fast, no I/O — one test file per source module
  integration/           # Real binary required, marker-gated
  conftest.py            # Shared fixtures
```

## Key Classes

| Class | Module | Role |
|---|---|---|
| `ERPCProcess` | `process.py` | Sync subprocess lifecycle (start/stop/health) |
| `AsyncERPCProcess` | `async_process.py` | Async subprocess lifecycle |
| `DockerERPCProcess` | `docker.py` | Docker container lifecycle |
| `ERPCConfig` | `config.py` | Top-level config builder, `to_dict()` → YAML |
| `ERPCClient` | `client.py` | HTTP client for health/metrics endpoints |
| `HealthMonitor` | `monitoring.py` | Daemon-thread health watcher |

## Common Tasks

### Add a new provider type
1. Add dataclass in `erpc/providers.py` following existing pattern
2. Implement `to_dict()` matching eRPC Go struct field names
3. Add unit tests in `tests/unit/test_providers.py`
4. Re-export from `erpc/__init__.py` if public

### Add a config section
1. Create dataclass in appropriate module (or new module)
2. Add `to_dict()` method — output keys must match eRPC Go YAML field names
3. Wire into `ERPCConfig.to_dict()` if it's a top-level section
4. Add tests for serialization round-trip

### Add a new failsafe policy
1. Add dataclass in `erpc/failsafe.py`
2. Follow `to_dict()` pattern — keys match Go struct fields
3. Test in `tests/unit/test_failsafe.py`

## Gotchas

- **Config serialization keys are Go-style**, not Pythonic. `to_dict()` output uses camelCase/Go field names as eRPC expects them. Don't "fix" these to snake_case.
- **HealthMonitor uses daemon threads**, not asyncio. This is intentional for sync compatibility.
- **Integration tests need the real eRPC binary.** Don't run them in default CI.
- **`ERPCConfig.to_dict()` must produce valid eRPC YAML.** Always validate against eRPC's Go config structs when changing serialization.
- **`from __future__ import annotations`** is used everywhere. Don't remove it.
