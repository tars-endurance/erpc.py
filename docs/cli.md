# CLI Reference

erpc.py includes the `erpc-py` command-line tool for managing eRPC instances.

## Installation

The CLI is installed automatically with the package:

```bash
pip install erpc-py
```

## Commands

### `erpc-py version`

Show erpc.py and eRPC binary versions:

```bash
erpc-py version
# erpc.py 0.1.0
# eRPC binary: 0.0.62 (/usr/local/bin/erpc)
```

### `erpc-py install`

Install the eRPC binary from GitHub releases:

```bash
erpc-py install --version 0.0.62
```

Options:

| Flag | Description | Default |
|---|---|---|
| `--version` | eRPC version to install | Latest |
| `--path` | Installation directory | `/usr/local/bin` |
| `--checksum` | SHA256 checksum for verification | None |

### `erpc-py config generate`

Generate an `erpc.yaml` configuration file:

```bash
erpc-py config generate \
  --chains 1,137 \
  --upstreams https://eth.llamarpc.com,https://polygon-rpc.com \
  --output erpc.yaml
```

Options:

| Flag | Description | Default |
|---|---|---|
| `--chains` | Comma-separated chain IDs | Required |
| `--upstreams` | Comma-separated RPC URLs | Required |
| `--output` | Output file path | `erpc.yaml` |
| `--project-id` | Project identifier | `py-erpc` |
| `--port` | Server port | `4000` |
| `--metrics-port` | Metrics port | `4001` |
| `--log-level` | Log level | `warn` |

### `erpc-py start`

Start an eRPC instance:

```bash
erpc-py start --config erpc.yaml
```

Options:

| Flag | Description | Default |
|---|---|---|
| `--config` | Path to `erpc.yaml` | `erpc.yaml` |
| `--binary` | Path to eRPC binary | Auto-detect |

### `erpc-py stop`

Stop a running eRPC instance:

```bash
erpc-py stop
```

### `erpc-py health`

Check eRPC health status:

```bash
erpc-py health
# eRPC is healthy (version 0.0.62, uptime: 3600s)
```

Options:

| Flag | Description | Default |
|---|---|---|
| `--url` | Health endpoint URL | `http://127.0.0.1:4000/` |

### `erpc-py metrics`

Display Prometheus metrics:

```bash
erpc-py metrics
```

Options:

| Flag | Description | Default |
|---|---|---|
| `--url` | Metrics endpoint URL | `http://127.0.0.1:4001/metrics` |
