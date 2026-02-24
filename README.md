# erpc.py

Python subprocess manager for [eRPC](https://github.com/erpc/erpc) — the fault-tolerant EVM RPC proxy and permanent caching solution.

Inspired by [py-geth](https://github.com/ethereum/py-geth) from the Ethereum Foundation.

## Overview

`erpc.py` provides a clean Python API for managing eRPC as a subprocess. It handles:

- **Binary discovery** — finds the `erpc` binary on PATH or at a specified location
- **Config generation** — programmatic YAML config building with sensible defaults
- **Process lifecycle** — start, stop, restart, health monitoring
- **Health checks** — polls eRPC's HTTP health endpoint
- **Graceful shutdown** — SIGTERM with fallback to SIGKILL
- **Context manager** — `with ERPCProcess(...) as erpc:` pattern

## Installation

```bash
pip install erpc-py
```

## Quick Start

```python
from erpc import ERPCProcess

# Minimal — just provide upstream RPC endpoints
process = ERPCProcess(
    upstreams={
        1: ["https://eth-mainnet.g.alchemy.com/v2/KEY"],
        137: ["https://polygon-mainnet.g.alchemy.com/v2/KEY"],
    }
)

# Context manager handles start/stop
with process:
    print(f"eRPC listening at {process.endpoint}")
    # Your application talks to process.endpoint instead of upstream RPCs
    # e.g., http://127.0.0.1:4000/main/evm/1

# Or manual lifecycle
process.start()
process.wait_for_health(timeout=30)
print(process.is_alive)
process.stop()
```

## Configuration

```python
from erpc import ERPCProcess, ERPCConfig, CacheConfig

config = ERPCConfig(
    project_id="my-project",
    upstreams={
        1: ["https://eth-mainnet.alchemy.com/v2/KEY", "https://mainnet.infura.io/v3/KEY"],
        137: ["https://polygon-mainnet.alchemy.com/v2/KEY"],
    },
    server_host="127.0.0.1",
    server_port=4000,
    metrics_port=4001,
    log_level="warn",
    cache=CacheConfig(
        max_items=10000,
        method_ttls={
            "eth_call": 0,           # No caching for calls (safety)
            "eth_getBlockByNumber": 12,  # 12s for block data
            "eth_getLogs": 2,         # 2s for logs
        }
    ),
)

process = ERPCProcess(config=config)
```

## Architecture

```
┌──────────────────────────────────────────┐
│  Your Application (Python)               │
│                                          │
│  ┌──────────────┐    ┌────────────────┐  │
│  │  ERPCProcess  │───▶│  erpc binary   │  │
│  │  (manager)   │    │  (subprocess)  │  │
│  └──────────────┘    └───────┬────────┘  │
│                              │           │
│         http://127.0.0.1:4000            │
│                              │           │
│                     ┌────────▼────────┐  │
│                     │  Upstream RPCs  │  │
│                     └─────────────────┘  │
└──────────────────────────────────────────┘
```

---

## Development Roadmap

Complete API coverage for eRPC, from subprocess management to full config schema to runtime monitoring.

### Phase 1 — Core Foundation ✅ (current)

Subprocess lifecycle management and basic configuration. **This is where we are.**

| # | Feature | Status | Description |
|---|---------|--------|-------------|
| — | Process lifecycle | ✅ Done | start/stop/restart, health checks, context manager, graceful shutdown |
| — | Basic config generation | ✅ Done | ERPCConfig → YAML, upstreams, cache, server settings |
| — | Binary discovery | ✅ Done | PATH, env var, common locations, explicit path |
| 1 | Binary installation | 🔲 Open | Cross-platform install from GitHub releases, version pinning, checksums |
| 2 | Config file loading | 🔲 Open | `ERPCConfig.from_yaml()`, schema validation, round-trip fidelity |
| 3 | Logging integration | 🔲 Open | Stream eRPC logs to Python logger, structured JSON parsing |

### Phase 2 — Full Config Schema

Complete Python dataclass coverage for every eRPC configuration surface.

| # | Feature | Status | Description |
|---|---------|--------|-------------|
| 4 | Network config | 🔲 Open | Full NetworkConfig: integrity, eth_getLogs controls, aliases, defaults |
| 5 | Upstream config | 🔲 Open | Full UpstreamConfig: block availability, compression, headers, proxies, scoring |
| 6 | Failsafe policies | 🔲 Open | Timeout, retry (empty response handling), hedge, circuit breaker, per-method |
| 7 | Rate limiters | 🔲 Open | Budgets, rules, auto-tuner, store backends (memory/Redis), wildcard matching |
| 8 | Database/cache | 🔲 Open | Memory, Redis, PostgreSQL, DynamoDB connectors; finality-aware cache policies |
| 9 | Provider shortcuts | 🔲 Open | Alchemy, Infura, dRPC, BlastAPI + 15 more with auto-chain discovery |
| 10 | Auth config | 🔲 Open | Secret, JWT, SIWE, Network auth strategies with per-user rate limits |
| 11 | Server & metrics | 🔲 Open | Full ServerConfig, MetricsConfig, CORS, Prometheus endpoint |

### Phase 3 — Runtime Client

HTTP client for eRPC's runtime monitoring and management endpoints.

| # | Feature | Status | Description |
|---|---------|--------|-------------|
| 12 | Health & metrics client | 🔲 Open | Structured health status, Prometheus metrics parsing, cache stats |
| 13 | Dynamic config updates | 🔲 Open | Hot config reload, upstream hot-swap, config diff detection |
| 14 | Upstream monitoring | 🔲 Open | Event callbacks (upstream down/recovered), circuit breaker state tracking |

### Phase 4 — Advanced

Power features for production deployments.

| # | Feature | Status | Description |
|---|---------|--------|-------------|
| 15 | Async support | 🔲 Open | AsyncERPCProcess, asyncio subprocess, async context manager |
| 16 | Docker integration | 🔲 Open | DockerERPCProcess using `ghcr.io/erpc/erpc`, container lifecycle |
| 17 | CLI tool | 🔲 Open | `erpc-py start/stop/health/install/config` command-line interface |
| 18 | Integration tests | 🔲 Open | Real eRPC binary tests, mock upstreams, CI pipeline |

### Coverage Target

```
eRPC Config Surface        Python Coverage
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Server config              Phase 2 (#11)
Projects                   Phase 1 ✅ (basic) → Phase 2 (full)
  ├─ Networks              Phase 2 (#4)
  │   ├─ Failsafe          Phase 2 (#6)
  │   ├─ Integrity         Phase 2 (#4)
  │   └─ eth_getLogs       Phase 2 (#4)
  ├─ Upstreams             Phase 2 (#5)
  │   ├─ Block availability Phase 2 (#5)
  │   ├─ Failsafe          Phase 2 (#6)
  │   └─ Compression       Phase 2 (#5)
  ├─ Providers             Phase 2 (#9)
  └─ Auth                  Phase 2 (#10)
Rate limiters              Phase 2 (#7)
Database/Cache             Phase 2 (#8)
  ├─ Drivers               Phase 2 (#8)
  ├─ Cache policies        Phase 2 (#8)
  └─ Compression           Phase 2 (#8)
Metrics                    Phase 2 (#11) + Phase 3 (#12)
Runtime API                Phase 3 (#12, #13, #14)
Async                      Phase 4 (#15)
Docker                     Phase 4 (#16)
CLI                        Phase 4 (#17)
```

---

## Reference

This project follows the patterns established by [py-geth](https://github.com/ethereum/py-geth), the Ethereum Foundation's Python wrapper for running Go-Ethereum as a subprocess.

## License

MIT
