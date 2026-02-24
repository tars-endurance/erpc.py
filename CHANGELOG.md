# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-02-24

### Added

- `ERPCProcess` — subprocess manager with start/stop/restart/health checks.
- `ERPCConfig` / `CacheConfig` — programmatic YAML config generation.
- `find_erpc_binary()` — automatic binary discovery (PATH, env var, common locations).
- `install_erpc()` — download eRPC binary from GitHub releases.
- `get_erpc_version()` — detect installed eRPC version.
- Context manager support (`with ERPCProcess(...) as erpc:`).
- Exception hierarchy: `ERPCError`, `ERPCNotFound`, `ERPCNotRunning`, `ERPCStartupError`, `ERPCHealthCheckError`.

[0.1.0]: https://github.com/tars-endurance/erpc.py/releases/tag/v0.1.0
