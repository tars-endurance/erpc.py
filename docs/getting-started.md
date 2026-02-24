# Getting Started

## Installation

```bash
pip install erpc-py
```

## Prerequisites

You need the eRPC binary installed. See the [eRPC docs](https://github.com/erpc/erpc) or use the built-in installer:

```python
from erpc.install import install_erpc

install_erpc(version="0.0.62")
```

## Basic Usage

```python
from erpc import ERPCProcess

# Quick setup with upstreams
with ERPCProcess(upstreams={1: ["https://eth.llamarpc.com"]}) as erpc:
    print(erpc.endpoint_url(1))
```

## Custom Configuration

```python
from erpc import ERPCConfig, CacheConfig, ERPCProcess

config = ERPCConfig(
    project_id="my-project",
    upstreams={
        1: ["https://eth-rpc-1.example.com", "https://eth-rpc-2.example.com"],
        137: ["https://polygon-rpc.example.com"],
    },
    server_port=4000,
    cache=CacheConfig(max_items=50_000),
)

with ERPCProcess(config=config) as erpc:
    print(erpc.endpoint_url(1))
    print(erpc.endpoint_url(137))
```
