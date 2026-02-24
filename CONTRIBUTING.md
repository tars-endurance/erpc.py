# Contributing to erpc.py

Thanks for your interest in contributing! This document covers how to get started.

## Development Setup

```bash
# Clone the repo
git clone https://github.com/tars-endurance/erpc.py.git
cd erpc.py

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

## Running Tests

```bash
# Run all tests with coverage
pytest

# Run a specific test file
pytest tests/test_config.py

# Run with verbose output
pytest -v
```

## Code Quality

We use automated tooling to maintain code quality:

```bash
# Lint
ruff check .

# Format
ruff format .

# Type check
mypy erpc
```

All of these run automatically via pre-commit hooks and in CI.

## Code Style

- **Formatting:** Enforced by [ruff](https://docs.astral.sh/ruff/) (line length: 99)
- **Type hints:** Required on all public APIs (mypy strict mode)
- **Docstrings:** Google-style on all public classes, methods, and functions
- **Tests:** Required for all new functionality

## Submitting a Pull Request

1. Fork the repository and create a feature branch from `main`.
2. Write your code, tests, and docstrings.
3. Run `ruff check .`, `ruff format .`, and `mypy erpc` — all must pass.
4. Run `pytest` — all tests must pass with adequate coverage.
5. Open a PR against `main` with a clear description of your changes.

## Reporting Issues

Use [GitHub Issues](https://github.com/tars-endurance/erpc.py/issues) with the
provided templates for bug reports and feature requests.
