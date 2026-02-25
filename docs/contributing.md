# Contributing

Thanks for your interest in contributing to erpc.py!

For full contributing guidelines, see [CONTRIBUTING.md on GitHub](https://github.com/tars-endurance/erpc.py/blob/main/CONTRIBUTING.md).

## Quick Start

```bash
git clone https://github.com/tars-endurance/erpc.py.git
cd erpc.py
pip install -e ".[dev]"
pre-commit install
```

## Running Tests

```bash
pytest                        # All tests with coverage
pytest tests/test_config.py   # Single file
pytest -v                     # Verbose output
```

## Code Quality

```bash
ruff check .    # Lint
ruff format .   # Format
mypy erpc       # Type check
```

## Pull Request Checklist

1. Fork and create a feature branch from `main`
2. Write code, tests, and docstrings
3. Pass `ruff check`, `ruff format --check`, `mypy erpc`, and `pytest`
4. Open a PR with a clear description
