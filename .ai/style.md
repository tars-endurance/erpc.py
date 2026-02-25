# Code Style — erpc.py

Beyond what ruff enforces automatically.

## Docstrings

Google-style with `Args`, `Returns`, `Raises`, `Examples` sections:

```python
def start(self, timeout: float = 30.0) -> None:
    """Start the eRPC subprocess and wait for health.

    Args:
        timeout: Seconds to wait for healthy status.

    Raises:
        ERPCStartupError: If process fails to start within timeout.

    Examples:
        >>> process = ERPCProcess(config=cfg)
        >>> process.start(timeout=10.0)
    """
```

## Type Hints

- Every function signature fully typed — no untyped defs
- `from __future__ import annotations` at top of every module
- Use `TYPE_CHECKING` guard for import-only types
- Prefer `X | None` over `Optional[X]`

## Config Classes

- **Always dataclasses** — never plain dicts for structured config
- Every config dataclass has a `to_dict()` method for YAML serialization
- `to_dict()` output keys match eRPC Go struct field names (not snake_case)
- Omit `None` values from `to_dict()` output

```python
@dataclass
class ServerConfig:
    """eRPC server listener configuration."""

    host: str = "0.0.0.0"
    port: int = 4000

    def to_dict(self) -> dict[str, Any]:
        return {"httpHost": self.host, "httpPort": self.port}
```

## Testing

- Test classes grouped by scenario, each with a docstring
- Class names: `TestFeatureBehavior`, e.g., `TestProcessStartup`, `TestConfigSerialization`
- Use fixtures from conftest, don't duplicate setup
- Assert messages on critical assertions

```python
class TestProcessStartup:
    """Verify ERPCProcess startup and health-check behavior."""

    def test_start_sets_running_flag(self, process):
        ...

    def test_start_timeout_raises(self, process):
        ...
```

## General

- **Explicit over implicit** — no magic, no metaclasses
- Dataclasses over NamedTuples for mutable config
- Keep modules focused — one concern per file
- Imports: stdlib → third-party → local, separated by blank lines
- No wildcard imports
