# py-erpc

Python subprocess manager for [eRPC](https://github.com/erpc/erpc) — the fault-tolerant EVM RPC proxy and permanent caching solution.

Inspired by [py-geth](https://github.com/ethereum/py-geth) from the Ethereum Foundation.

## Overview

`py-erpc` provides a clean Python API for managing eRPC as a subprocess. It handles:

- **Binary discovery** — finds the `erpc` binary on PATH or at a specified location
- **Config generation** — programmatic YAML config building with sensible defaults
- **Process lifecycle** — start, stop, restart, health monitoring
- **Health checks** — polls eRPC's HTTP health endpoint
- **Graceful shutdown** — SIGTERM with fallback to SIGKILL
- **Context manager** — `with ERPCProcess(...) as erpc:` pattern

## Installation

```bash
pip install py-erpc
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
from erpc import ERPCProcess, ERPCConfig

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
        # Per-method TTL overrides
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

## Reference

This project follows the patterns established by [py-geth](https://github.com/ethereum/py-geth), the Ethereum Foundation's Python wrapper for running Go-Ethereum as a subprocess.

## License

MIT
