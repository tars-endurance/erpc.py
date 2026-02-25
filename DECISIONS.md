# Architectural Decision Records

## ADR-001: Subprocess Management Over FFI Bindings

- **Status:** Accepted
- **Context:** eRPC is written in Go. We needed a way to control it from Python. Options: Go FFI bindings (cgo/ctypes), gRPC control plane, or subprocess management.
- **Decision:** Manage eRPC as a subprocess. Generate config YAML, spawn the binary, health-check via HTTP.
- **Consequences:** Clean process isolation — crashes don't take down the Python process. No cgo build complexity. Trade-off: slower startup (process spawn vs function call) and communication limited to HTTP/config files. Acceptable for a long-running proxy.

## ADR-002: PyYAML as Only Runtime Dependency

- **Status:** Accepted
- **Context:** eRPC reads YAML config. We need to serialize Python config objects to YAML.
- **Decision:** `pyyaml` is the sole runtime dependency. Everything else (pytest, mypy, ruff) is dev-only.
- **Consequences:** Minimal footprint — easy to install, no dependency conflicts. Limits serialization options (no TOML/JSON config without adding deps). Acceptable since eRPC only reads YAML.

## ADR-003: Dataclass-Based Config Over Dict Manipulation

- **Status:** Accepted
- **Context:** Config generation could be done with nested dicts or structured objects.
- **Decision:** Use `@dataclass` classes for all config sections. Each has a `to_dict()` method for YAML serialization.
- **Consequences:** Full type safety and IDE autocompletion. mypy catches config errors at lint time. Slightly more code than raw dicts, but dramatically better developer experience and maintainability.

## ADR-004: Separate Unit/Integration Test Directories with Pytest Markers

- **Status:** Accepted
- **Context:** Integration tests require the real eRPC binary and network access. They're slow and environment-dependent.
- **Decision:** `tests/unit/` for fast, isolated tests. `tests/integration/` for real-binary tests. Pytest markers (`unit`, `integration`, `fault_tolerance`, `slow`) gate execution.
- **Consequences:** CI runs fast by default (unit only). Integration tests run nightly or manually. Clear separation of concerns. Developers must remember to mark new tests appropriately.

## ADR-005: Co-Authorship Convention

- **Status:** Accepted
- **Context:** This project is developed with human direction and AI execution. Authorship should be transparent.
- **Decision:** Every AI-assisted commit includes a `Co-authored-by:` trailer for both the human director and the AI executor.
- **Consequences:** Clear attribution and provenance. Git history shows who directed and who implemented. Standard GitHub convention — co-authors appear in the UI.

## ADR-006: Config Serialization Matches eRPC Go Struct Field Names

- **Status:** Accepted
- **Context:** Python convention is `snake_case`. eRPC's Go config uses `camelCase` field names in YAML.
- **Decision:** `to_dict()` methods output Go-style field names (`httpHost`, not `http_host`). Python-side attributes remain `snake_case`.
- **Consequences:** Generated YAML is directly consumable by eRPC without transformation. Developers must maintain the mapping between Python attributes and Go field names. The mapping is explicit in each `to_dict()` method — no magic translation layer.

## ADR-007: HealthMonitor Uses Daemon Threads

- **Status:** Accepted
- **Context:** Health monitoring needs to run in the background. Options: asyncio tasks, threading, or multiprocessing.
- **Decision:** `HealthMonitor` uses daemon threads, not asyncio.
- **Consequences:** Works in sync contexts without an event loop. Daemon threads auto-terminate when the main process exits — no cleanup required. Trade-off: can't use async I/O patterns internally. Acceptable since health checks are simple HTTP GETs with `urllib`.
