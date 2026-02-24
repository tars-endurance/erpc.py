# erpc.py

Python subprocess manager for [eRPC](https://github.com/erpc/erpc) — the fault-tolerant EVM RPC proxy.

## Quick Start

```python
from erpc import ERPCProcess

with ERPCProcess(upstreams={1: ["https://eth.llamarpc.com"]}) as erpc:
    url = erpc.endpoint_url(1)
    # Use `url` with web3.py, httpx, etc.
```

## Features

- **Binary discovery** — finds `erpc` on PATH or at a specified location
- **Config generation** — programmatic YAML config with sensible defaults
- **Process lifecycle** — start, stop, restart, health monitoring
- **Context manager** — clean resource management
- **Type-safe** — fully typed with py.typed marker

## Installation

```bash
pip install erpc-py
```

## License

MIT
