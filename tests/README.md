# Test Suite

## Structure

```
tests/
├── conftest.py          # Auto-applies unit/integration markers
├── unit/                # Fast, no I/O, fully mocked (~393 tests)
│   ├── test_auth.py     # Authentication config dataclasses
│   ├── test_cli.py      # CLI argument parsing and entrypoint
│   ├── test_client.py   # HTTP client for health/metrics
│   ├── test_config.py   # Config generation (ERPCConfig → YAML)
│   ├── test_config_loading.py  # Loading/validating existing YAML configs
│   ├── test_database.py # Database/cache configuration
│   ├── test_docker.py   # Docker-based process management
│   ├── test_dynamic.py  # Dynamic config updates
│   ├── test_exceptions.py # Exception hierarchy
│   ├── test_failsafe.py # Failsafe policy configuration
│   ├── test_install.py  # Binary installation logic
│   ├── test_logging.py  # Logging integration and output capture
│   ├── test_monitoring.py # Health monitoring
│   ├── test_networks.py # Network configuration dataclasses
│   ├── test_process.py  # Process lifecycle management
│   ├── test_providers.py # Provider shortcuts
│   ├── test_rate_limiters.py # Rate limiter configuration
│   ├── test_server.py   # Server, metrics, CORS config
│   ├── test_upstreams.py # Upstream configuration
│   └── test_version.py  # Version detection
└── integration/         # Needs real eRPC binary (~7 tests)
    ├── conftest.py      # Fixtures: binary discovery, mock upstream
    ├── mock_upstream.py  # Flask mock for upstream testing
    └── test_proxy.py    # End-to-end proxy behavior
```

## Running Tests

```bash
# Unit tests only (default, fast — CI on every push)
pytest

# Integration tests only (needs eRPC binary)
pytest -m integration

# All tests
pytest -m ""

# Specific file
pytest tests/unit/test_config.py
```

## Markers

| Marker        | Description                          | CI Cadence        |
|---------------|--------------------------------------|-------------------|
| `unit`        | Fast, mocked, no I/O                | Every push/PR     |
| `integration` | Needs real eRPC binary              | Nightly / manual  |
| `slow`        | Any test taking >1s                 | Every push (but flagged) |

## Coverage

Unit tests target **90%** line coverage of the `erpc` package (enforced in CI).
Integration tests are excluded from default coverage measurement.
