# Getting Started

## Installation

Install erpc.py from PyPI:

```bash
pip install erpc-py
```

This installs the Python library and the `erpc-py` CLI tool. The eRPC binary itself is installed separately.

## Installing the eRPC Binary

erpc.py manages the [eRPC](https://github.com/erpc/erpc) Go binary. Install it via CLI or Python:

=== "CLI"

    ```bash
    erpc-py install --version 0.0.62
    ```

=== "Python"

    ```python
    from erpc.install import install_erpc

    path = install_erpc("0.0.62")
    print(f"Installed to: {path}")
    ```

The binary is placed at `/usr/local/bin/erpc` by default.

!!! tip "SHA256 Verification"
    Pass a checksum for verified installs:
    ```python
    install_erpc("0.0.62", checksum="abc123...")
    ```

## Your First Config

The simplest way to start is with a chain ID → upstream URL mapping:

```python
from erpc import ERPCConfig

config = ERPCConfig(
    upstreams={
        1: ["https://eth.llamarpc.com"],       # Ethereum mainnet
        137: ["https://polygon-rpc.com"],       # Polygon
    },
)

# Preview the generated YAML
print(config.to_yaml())

# Or write it to a file
config.write("erpc.yaml")
```

## Starting eRPC

### Context Manager (Recommended)

```python
from erpc import ERPCProcess

with ERPCProcess(upstreams={1: ["https://eth.llamarpc.com"]}) as erpc:
    print(erpc.endpoint_url(1))
    # → http://127.0.0.1:4000/py-erpc/evm/1

    print(f"Healthy: {erpc.is_healthy}")
    # eRPC is automatically stopped when the block exits
```

### With a Config Object

```python
from erpc import ERPCConfig, ERPCProcess, CacheConfig

config = ERPCConfig(
    project_id="my-app",
    upstreams={1: ["https://eth.llamarpc.com"]},
    cache=CacheConfig(max_items=50_000),
    log_level="info",
)

with ERPCProcess(config=config) as erpc:
    print(erpc.endpoint_url(1))
```

### Via CLI

```bash
# Generate a config
erpc-py config generate \
  --chains 1,137 \
  --upstreams https://eth.llamarpc.com,https://polygon-rpc.com \
  --output erpc.yaml

# Start eRPC
erpc-py start --config erpc.yaml

# Check health
erpc-py health

# Stop
erpc-py stop
```

## Using Docker

No local binary needed — run eRPC in a Docker container:

```python
from erpc import ERPCConfig, DockerERPCProcess

config = ERPCConfig(upstreams={1: ["https://eth.llamarpc.com"]})

with DockerERPCProcess(config=config, name="my-erpc") as erpc:
    print(erpc.endpoint_url(1))
    print(erpc.logs(tail=20))
```

## Next Steps

- [Configuration Guide](configuration.md) — Networks, caching, auth, failsafe, and more
- [Process Management](process-management.md) — Lifecycle patterns and async support
- [Monitoring](monitoring.md) — Health checks and Prometheus metrics
