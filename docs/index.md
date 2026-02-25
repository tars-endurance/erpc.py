# erpc.py

**Python subprocess manager for [eRPC](https://github.com/erpc/erpc) — the fault-tolerant EVM RPC proxy.**

Like [py-geth](https://github.com/ethereum/py-geth) for Go-Ethereum, but for eRPC.

[![CI](https://github.com/tars-endurance/erpc.py/actions/workflows/ci.yml/badge.svg)](https://github.com/tars-endurance/erpc.py/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%E2%80%933.13-blue)](https://pypi.org/project/erpc-py/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](https://github.com/tars-endurance/erpc.py/blob/main/LICENSE)

---

## What is erpc.py?

**erpc.py** gives you full programmatic control over [eRPC](https://github.com/erpc/erpc) from Python:

- **Binary installation** — download and verify eRPC binaries from GitHub releases
- **YAML config generation** — type-safe Python dataclasses that emit valid `erpc.yaml`
- **Process lifecycle** — start, stop, health-check, and monitor eRPC as a subprocess or Docker container
- **Health monitoring** — query health endpoints and Prometheus metrics with stdlib HTTP (no `requests` needed)
- **CLI tool** — manage eRPC from the command line

Pure Python with only `pyyaml` as a runtime dependency.

## Quick Example

```python
from erpc import ERPCProcess

with ERPCProcess(upstreams={1: ["https://eth.llamarpc.com"]}) as erpc:
    url = erpc.endpoint_url(1)  # http://127.0.0.1:4000/py-erpc/evm/1
    print(f"Proxying Ethereum mainnet at {url}")
    print(f"Healthy: {erpc.is_healthy}")
```

## Full Config Example

```python
from erpc import ERPCConfig, ERPCProcess, CacheConfig

config = ERPCConfig(
    project_id="my-project",
    upstreams={
        1: ["https://eth.llamarpc.com", "https://rpc.ankr.com/eth"],
        137: ["https://polygon-rpc.com"],
    },
    server_port=4000,
    metrics_port=4001,
    log_level="info",
    cache=CacheConfig(max_items=50_000),
)

with ERPCProcess(config=config) as erpc:
    print(erpc.endpoint_url(1))    # Ethereum
    print(erpc.endpoint_url(137))  # Polygon
```

## Key Classes

| Class | Description |
|---|---|
| [`ERPCConfig`](api/config.md) | Config builder — generates `erpc.yaml` from Python dataclasses |
| [`ERPCProcess`](api/process.md) | Subprocess lifecycle manager with context manager support |
| [`DockerERPCProcess`](api/docker.md) | Docker container lifecycle manager |
| [`ERPCClient`](api/client.md) | Health and Prometheus metrics client (stdlib HTTP) |
| [`HealthMonitor`](api/monitoring.md) | Health state tracking with event history |
| [`install_erpc()`](api/install.md) | Binary installer from GitHub releases |

## Next Steps

- [Getting Started](getting-started.md) — Installation and first run
- [Configuration Guide](configuration.md) — Full config reference
- [Process Management](process-management.md) — Lifecycle patterns
- [API Reference](api/index.md) — Auto-generated API docs
