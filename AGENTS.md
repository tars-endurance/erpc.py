# AGENTS.md — Contributing Guide for Humans & LLMs

## Project Overview

**erpc.py** is a Python subprocess manager for [eRPC](https://github.com/erpc/erpc), a fault-tolerant EVM RPC proxy written in Go. This library lets Python applications configure, launch, monitor, and manage eRPC instances as subprocesses (or Docker containers). Think of it as `py-geth` but for eRPC.

The core loop: build a config → write YAML → spawn the binary → health-check → manage lifecycle.

## Architecture

```
erpc/
├── process.py        # ERPCProcess — sync subprocess lifecycle (start/stop/health)
├── async_process.py  # AsyncERPCProcess — asyncio subprocess lifecycle
├── docker.py         # DockerERPCProcess — Docker container lifecycle
├── config.py         # ERPCConfig — top-level config builder, YAML serialization
├── server.py         # ServerConfig, MetricsConfig — listener/metrics settings
├── networks.py       # NetworkConfig — chain/network definitions
├── providers.py      # Provider classes — RPC endpoint definitions
├── upstreams.py      # UpstreamConfig — upstream grouping
├── failsafe.py       # Failsafe policies — retry, timeout, hedge, circuit breaker
├── rate_limiters.py  # Rate limiter configs — budget-based rate limiting
├── database.py       # Database/cache connectors — Redis, Postgres, DynamoDB, memory
├── auth.py           # Auth configs — JWT, SIWE, secret, network-level auth
├── client.py         # ERPCClient — HTTP client for health/metrics endpoints
├── monitoring.py     # HealthMonitor — daemon-thread health watcher
├── dynamic.py        # Dynamic config updates — add/remove upstreams at runtime
├── install.py        # Binary installer — download eRPC from GitHub releases
├── cli.py            # CLI entrypoint — `erpc-py` command
├── logging.py        # Logging setup
├── mixins.py         # Shared mixins (e.g., ToDict)
├── exceptions.py     # Exception hierarchy
├── version.py        # Version detection
└── __init__.py       # Public API re-exports
```

## Quality Bar

- **Type checking:** mypy strict mode, no untyped defs
- **Linting:** ruff (see `pyproject.toml` for rule config)
- **Coverage:** 90% minimum, enforced in CI
- **Commits:** [Conventional Commits](https://www.conventionalcommits.org/) — `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`
- **Co-authorship:** Every AI-assisted commit must include a `Co-authored-by:` trailer

## Testing Conventions

```bash
# Unit tests (fast, no I/O, runs on every push)
pytest tests/unit/ -m "not integration and not slow"

# Integration tests (real binary required, manual/nightly only)
pytest tests/integration/ -m integration

# Fault tolerance scenarios
pytest -m fault_tolerance

# Full suite with coverage
pytest --cov=erpc --cov-report=term-missing
```

**Markers:** `unit`, `integration`, `fault_tolerance`, `slow`

Unit tests live in `tests/unit/`, integration in `tests/integration/`. Each unit test file maps 1:1 to a source module.

## Frozen Interfaces — Do NOT Change Without Discussion

- `ERPCProcess` public API (`start()`, `stop()`, `is_running`, `wait()`)
- `ERPCConfig.to_dict()` output structure (must match eRPC Go structs)
- `ERPCClient` public methods
- Test infrastructure: `tests/conftest.py`, `tests/integration/mock_upstream.py`

## PR Conventions

- **Branch naming:** `feat/description`, `fix/description`, `refactor/description`
- **Commit format:** `type(scope): description` — e.g., `feat(config): add TLS support`
- **Target:** always `main`
- **Co-authorship:** If you're an AI agent, include a `Co-authored-by:` trailer crediting your human collaborator. If you're a human, credit your AI agent. Attribution is a first-class convention in this repo.

## Dependencies

- **Runtime:** `pyyaml` only. Do not add runtime dependencies without explicit approval.

## Version Pinning

This package is pinned to a specific eRPC binary version via `erpc.ERPC_VERSION`. This is the **single source of truth** for which eRPC release we target.

- **`erpc/__init__.py`** — defines `ERPC_VERSION` (e.g., `"0.0.62"`)
- **`install_erpc()`** — defaults to `ERPC_VERSION` when no version is specified
- **CI integration tests** — read `ERPC_VERSION` from Python to download the correct binary
- **Config generation** — tested against this version's YAML schema

When upgrading the pinned version:
1. Update `ERPC_VERSION` in `erpc/__init__.py`
2. Run integration tests locally with the new binary
3. Check for any config schema changes in the eRPC changelog
4. Update DECISIONS.md if the upgrade changes any architectural assumptions
- **Dev:** pytest, pytest-asyncio, pytest-cov, ruff, mypy, pre-commit, types-PyYAML
- **Philosophy:** Minimal footprint. This is a thin wrapper, not a framework.
