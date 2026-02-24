# erpc.py — Project Standards

This is a portfolio-grade open source project. Every contribution must meet these standards.

## Code Quality

- **Type hints everywhere** — mypy strict mode, no `Any` escape hatches
- **Google-style docstrings** — every public class, method, function. Include Args, Returns, Raises, Examples
- **100% test coverage target** — no feature ships without tests
- **Idiomatic Python** — clean abstractions, no magic, obvious API surface
- **3-line quickstart** — someone should pip install and have eRPC running in 3 lines

## Tooling

- **Linting:** ruff (line-length 99)
- **Formatting:** ruff format
- **Type checking:** mypy strict
- **Testing:** pytest + coverage
- **CI:** GitHub Actions — Python 3.10, 3.11, 3.12, 3.13 matrix
- **Pre-commit:** ruff lint, ruff format, mypy, trailing whitespace, EOF fixer
- **Docs:** MkDocs with Material theme

## Conventions

- **Commits:** Conventional commits (`feat:`, `fix:`, `chore:`, `docs:`, `test:`, `refactor:`)
- **Versioning:** Semantic versioning (MAJOR.MINOR.PATCH)
- **Changelog:** Every release gets a CHANGELOG.md entry
- **Branches:** `main` is stable. Feature branches for development. PRs required.
- **Reviews:** Every PR has tests, docs updates where applicable

## Architecture Principles

- **py-geth is the reference** — follow Ethereum Foundation patterns where applicable
- **Subprocess, not bindings** — manage eRPC as a process, not FFI
- **Config as dataclasses** — every eRPC config surface maps to a Python dataclass
- **No runtime dependencies beyond PyYAML** — keep it lightweight
- **Fail gracefully** — clear exceptions, sensible defaults, bypass modes

## Development Roadmap

See [README.md](README.md) for the 4-phase roadmap (18 issues).

| Phase | Focus | Issues |
|-------|-------|--------|
| 1 | Core Foundation | #1–#3 |
| 2 | Full Config Schema | #4–#11 |
| 3 | Runtime Client | #12–#14 |
| 4 | Advanced | #15–#18 |

## The Bar

Someone reviewing this repo should think: *"This person knows what they're doing."*

No shortcuts. No "good enough." Ship it right.
