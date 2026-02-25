# Monitoring

erpc.py provides tools for health checking and metrics collection — all using stdlib HTTP, no `requests` needed.

## ERPCClient

Query eRPC's health endpoint and Prometheus metrics:

```python
from erpc.client import ERPCClient

client = ERPCClient("http://localhost:4000")

# Structured health check
status = client.health()
print(f"Version: {status.version}")
print(f"Uptime: {status.uptime}s")
print(f"Status: {status.status}")

# Prometheus metrics as dict
metrics = client.metrics()
print(metrics.get("erpc_requests_total"))
```

### Using with ERPCProcess

```python
from erpc import ERPCProcess

with ERPCProcess(upstreams={1: ["https://eth.llamarpc.com"]}) as erpc:
    client = erpc.client
    status = client.health()
    print(f"{status.version} — uptime: {status.uptime}s")
```

## HealthMonitor

Track health state transitions over time:

```python
from erpc import HealthMonitor, HealthEvent

monitor = HealthMonitor(
    url="http://localhost:4000",
    interval=30.0,
)

event = monitor.latest_event()
if event == HealthEvent.HEALTHY:
    print("All good")
elif event == HealthEvent.DOWN:
    print("eRPC is down!")
```

### Health Events

| Event | Description |
|---|---|
| `HealthEvent.HEALTHY` | eRPC is responding normally |
| `HealthEvent.DEGRADED` | Partial failures detected |
| `HealthEvent.DOWN` | eRPC is unreachable |
| `HealthEvent.RECOVERED` | Transitioned from down to healthy |

### HealthStatus

The `HealthStatus` dataclass returned by `client.health()`:

```python
from erpc.client import ERPCClient

client = ERPCClient("http://localhost:4000")
status = client.health()

print(status.status)   # "ok" or error state
print(status.version)  # eRPC version string
print(status.uptime)   # Uptime in seconds
```

## Prometheus Metrics

eRPC exposes Prometheus metrics on the metrics port (default 4001):

```python
from erpc.client import ERPCClient

client = ERPCClient("http://localhost:4000", metrics_url="http://localhost:4001/metrics")
metrics = client.metrics()

# Access individual metrics
total_requests = metrics.get("erpc_requests_total")
error_rate = metrics.get("erpc_errors_total")
```

## Log Streaming

Stream eRPC logs programmatically:

```python
from erpc.logging import ERPCLogStream

# Available when using ERPCProcess
with ERPCProcess(upstreams={1: ["https://eth.llamarpc.com"]}) as erpc:
    # Logs are captured from the subprocess stdout/stderr
    pass
```
