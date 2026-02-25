<div align="center">

# erpc.py

**Python subprocess manager for [eRPC](https://github.com/erpc/erpc) — the fault-tolerant EVM RPC proxy.**

Like [py-geth](https://github.com/ethereum/py-geth) for Go-Ethereum, but for eRPC.

[![PyPI](https://img.shields.io/pypi/v/erpc-py)](https://pypi.org/project/erpc-py/)
[![CI](https://github.com/tars-endurance/erpc.py/actions/workflows/ci.yml/badge.svg)](https://github.com/tars-endurance/erpc.py/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/tars-endurance/erpc.py/branch/main/graph/badge.svg)](https://codecov.io/gh/tars-endurance/erpc.py)
[![Python](https://img.shields.io/badge/python-3.10%E2%80%933.13-blue)](https://pypi.org/project/erpc-py/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![mypy](https://img.shields.io/badge/type--checked-mypy%20strict-blue)](https://mypy-lang.org/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://docs.astral.sh/ruff/)

</div>

---

## Overview

**erpc.py** gives you full programmatic control over [eRPC](https://github.com/erpc/erpc) from Python — binary installation, YAML config generation, process lifecycle, health monitoring, and runtime metrics. Pure Python with only `pyyaml` as a runtime dependency.

```python
from erpc import ERPCProcess

with ERPCProcess(upstreams={1: ["https://eth.llamarpc.com"]}) as erpc:
    url = erpc.endpoint_url(1)  # http://127.0.0.1:4000/py-erpc/evm/1
    print(f"Proxying Ethereum mainnet at {url}")
```

---

## Installation

```bash
pip install erpc-py
```

To install the eRPC binary:

```bash
erpc-py install --version 0.0.62
```

Or programmatically:

```python
from erpc.install import install_erpc

install_erpc("0.0.62")  # → /usr/local/bin/erpc
```

---

## Quick Start

### Minimal — just upstreams

```python
from erpc import ERPCProcess

with ERPCProcess(upstreams={1: ["https://eth.llamarpc.com"]}) as erpc:
    print(erpc.endpoint_url(1))
    print(f"Healthy: {erpc.is_healthy}")
```

### Full config

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
    print(erpc.endpoint_url(1))
    print(erpc.endpoint_url(137))
```

---

## Features

### 🔧 Binary Management

Auto-detect or install eRPC binaries from GitHub releases with optional SHA256 verification.

```python
from erpc.install import install_erpc

path = install_erpc("0.0.62", checksum="abc123...")
```

### 📝 Config Builder

Full-fidelity Python config that generates valid `erpc.yaml` — networks, upstreams, failsafe policies, rate limiters, auth, caching, database connectors, and more.

```python
from erpc import ERPCConfig, DatabaseConfig, RedisConnector, AuthConfig, SecretAuth

config = ERPCConfig(
    project_id="production",
    upstreams={1: ["https://eth.llamarpc.com"]},
    database=DatabaseConfig(
        evm_json_rpc_cache=RedisConnector(addr="localhost:6379"),
    ),
    auth=AuthConfig(
        strategies=[SecretAuth(value="my-secret-key")],
    ),
)

config.write("erpc.yaml")  # Write to file
print(config.to_yaml())    # Or get YAML string
```

**Supported config sections:**
- Networks with per-chain policies
- Upstream defaults and rich upstream configs
- 20+ provider presets (Alchemy, Infura, QuickNode, Ankr, etc.)
- Rate limiters and failsafe policies
- Auth strategies (Secret, JWT, SIWE, Network-based)
- Database connectors (Redis, PostgreSQL, DynamoDB, Memory)
- Cache policies with per-method TTLs
- Server config (CORS, timeouts) and metrics

### 🏥 Health & Metrics Client

Query eRPC's runtime health and Prometheus metrics — stdlib only, no `requests` needed.

```python
from erpc.client import ERPCClient

client = ERPCClient("http://localhost:4000")

# Structured health check
status = client.health()
print(f"{status.version} — uptime: {status.uptime}s")

# Prometheus metrics as dict
metrics = client.metrics()
print(metrics.get("erpc_requests_total"))
```

### 📊 Health Monitoring

Track health state transitions over time.

```python
from erpc import HealthMonitor, HealthEvent

monitor = HealthMonitor(url="http://localhost:4000", interval=30.0)
event = monitor.latest_event()  # HealthEvent.HEALTHY / DOWN / etc.
```

### 🐳 Docker Integration

Run eRPC as a Docker container — no local binary needed. Uses the `docker` CLI, no Python Docker SDK required.

```python
from erpc import ERPCConfig, DockerERPCProcess

config = ERPCConfig(upstreams={1: ["https://eth.llamarpc.com"]})

with DockerERPCProcess(config=config, name="my-erpc") as erpc:
    print(erpc.endpoint_url(1))
    print(erpc.logs(tail=20))
```

### 🖥️ CLI Tool

Manage eRPC from the command line:

```bash
erpc-py version                    # Show versions
erpc-py install --version 0.0.62   # Install binary
erpc-py health                     # Check health
erpc-py metrics                    # Show Prometheus metrics
erpc-py config generate \
  --chains 1,137 \
  --upstreams https://eth.llamarpc.com,https://polygon-rpc.com \
  --output erpc.yaml               # Generate config
erpc-py start --config erpc.yaml   # Start eRPC
erpc-py stop                       # Stop eRPC
```

### 🛡️ Provider Presets

20+ built-in provider configurations for popular RPC services:

```python
from erpc import AlchemyProvider, InfuraProvider, ERPCConfig

config = ERPCConfig(
    upstreams={1: ["https://eth.llamarpc.com"]},
    providers=[
        AlchemyProvider(api_key="..."),
        InfuraProvider(api_key="..."),
    ],
)
```

<details>
<summary>All supported providers</summary>

Alchemy · Ankr · BlastAPI · BlockPi · Chainstack · Conduit · DRPC · Dwellir · Envio · Etherspot · Infura · OnFinality · Pimlico · QuickNode · Repository · RouteMesh · Superchain · Tenderly · Thirdweb

</details>

---

## API Overview

| Class | Description |
|---|---|
| `ERPCConfig` | Config builder — generates `erpc.yaml` from Python dataclasses |
| `ERPCProcess` | Subprocess lifecycle manager with context manager support |
| `DockerERPCProcess` | Docker container lifecycle manager |
| `ERPCClient` | Health and Prometheus metrics client (stdlib HTTP) |
| `HealthMonitor` | Health state tracking with event history |
| `install_erpc()` | Binary installer from GitHub releases |
| `CacheConfig` | Memory cache settings with per-method TTLs |
| `DatabaseConfig` | Database connector config (Redis, Postgres, DynamoDB, Memory) |
| `AuthConfig` | Auth strategies (Secret, JWT, SIWE, Network) |
| `ServerConfig` | Server settings (CORS, timeouts, host/port) |

---

## Development

```bash
git clone https://github.com/tars-endurance/erpc.py.git
cd erpc.py
pip install -e ".[dev]"

# Run tests (319 tests, 96% coverage)
pytest

# Type checking
mypy erpc/

# Linting
ruff check .
ruff format --check .
```

---

## License

[MIT](LICENSE)
