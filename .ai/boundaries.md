# Boundaries — erpc.py

## Do NOT without explicit approval

- **Add runtime dependencies.** Only `pyyaml` is allowed at runtime. Everything else is dev-only.
- **Change the public API of `ERPCProcess` or `ERPCConfig`.** These are the primary interfaces consumers depend on. Discuss first.
- **Alter `to_dict()` output structure.** Serialization must match eRPC's Go config format. Changing keys breaks real deployments.

## Do NOT without understanding downstream effects

- **Modify test infrastructure** — `tests/conftest.py`, `tests/integration/conftest.py`, `tests/integration/mock_upstream.py` are shared across many tests. Changes cascade.
- **Remove or rename public exports from `erpc/__init__.py`.** Consumers import from the top-level package.

## CI constraints

- **Integration tests must not run in default CI.** They require the real eRPC binary and are gated behind the `integration` marker.
- **Fault tolerance tests** are slow by nature — keep them marker-gated (`fault_tolerance`).

## Config serialization

- YAML output keys must match eRPC Go struct field names exactly.
- Do not "Pythonify" output keys to snake_case — eRPC won't parse it.
- When in doubt, check eRPC's Go source for the expected field names.
