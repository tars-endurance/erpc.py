# Process Management

erpc.py provides three process managers for different deployment scenarios.

## ERPCProcess

The standard subprocess manager. Runs eRPC as a local child process.

### Context Manager (Recommended)

```python
from erpc import ERPCProcess

with ERPCProcess(upstreams={1: ["https://eth.llamarpc.com"]}) as erpc:
    print(erpc.endpoint_url(1))
    print(f"PID: {erpc.pid}")
    print(f"Healthy: {erpc.is_healthy}")
# eRPC is automatically stopped on exit
```

### Manual Lifecycle

```python
from erpc import ERPCConfig, ERPCProcess

config = ERPCConfig(upstreams={1: ["https://eth.llamarpc.com"]})
proc = ERPCProcess(config=config)

proc.start()
proc.wait_for_health(timeout=30)

# ... use eRPC ...

proc.stop()
```

### Shorthand Initialization

Pass `upstreams` directly without creating a config:

```python
proc = ERPCProcess(upstreams={1: ["https://eth.llamarpc.com"]})
```

### Custom Binary Path

```python
proc = ERPCProcess(
    upstreams={1: ["https://eth.llamarpc.com"]},
    binary_path="/opt/erpc/erpc",
)
```

### Health Checks

```python
with ERPCProcess(upstreams={1: ["https://eth.llamarpc.com"]}) as erpc:
    # Boolean health check
    if erpc.is_healthy:
        print("eRPC is up")

    # Structured health via client
    client = erpc.client
    status = client.health()
    print(f"Version: {status.version}, Uptime: {status.uptime}s")
```

### Process Signals

```python
import signal

proc = ERPCProcess(upstreams={1: ["https://eth.llamarpc.com"]})
proc.start()

# Graceful shutdown (SIGTERM)
proc.stop()

# Force kill (SIGKILL) — if stop() doesn't work
proc.stop(force=True)
```

## AsyncERPCProcess

For asyncio applications. Same API as `ERPCProcess` but with async context manager:

```python
import asyncio
from erpc import AsyncERPCProcess

async def main():
    async with AsyncERPCProcess(upstreams={1: ["https://eth.llamarpc.com"]}) as erpc:
        print(erpc.endpoint_url(1))
        print(f"Healthy: {erpc.is_healthy}")

asyncio.run(main())
```

## DockerERPCProcess

Runs eRPC in a Docker container. No local binary needed — uses the `docker` CLI.

### Basic Usage

```python
from erpc import ERPCConfig, DockerERPCProcess

config = ERPCConfig(upstreams={1: ["https://eth.llamarpc.com"]})

with DockerERPCProcess(config=config, name="my-erpc") as erpc:
    print(erpc.endpoint_url(1))
    print(erpc.logs(tail=20))
```

### Custom Image

```python
proc = DockerERPCProcess(
    config=config,
    name="erpc-prod",
    image="ghcr.io/erpc/erpc:0.0.62",
)
```

### Container Logs

```python
with DockerERPCProcess(config=config) as erpc:
    # Get recent logs
    logs = erpc.logs(tail=50)
    print(logs)
```

## Lifecycle Summary

All process managers follow the same pattern:

| Method | Description |
|---|---|
| `start()` | Start the eRPC process/container |
| `stop()` | Gracefully stop eRPC |
| `wait_for_health()` | Block until healthy or timeout |
| `is_healthy` | Property — quick boolean health check |
| `endpoint_url(chain_id)` | Get the RPC URL for a chain |
| `client` | Get an `ERPCClient` bound to this instance |

!!! info "Context Manager"
    Using `with` (or `async with`) is strongly recommended. It ensures cleanup even if exceptions occur.
