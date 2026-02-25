"""Integration test fixtures for eRPC process testing.

Provides fixtures that start a real eRPC binary with a mock upstream,
allowing end-to-end validation of proxy behavior, caching, and metrics.
"""

from __future__ import annotations

from typing import Generator

import pytest

from erpc.config import ERPCConfig
from erpc.process import ERPCProcess, find_erpc_binary

from .mock_upstream import MockUpstream


@pytest.fixture(scope="session")
def erpc_binary() -> str:
    """Locate the eRPC binary or skip the test session.

    Returns:
        Path to the eRPC binary.

    """
    try:
        return find_erpc_binary()
    except Exception:
        pytest.skip("eRPC binary not found — skipping integration tests")


@pytest.fixture()
def mock_upstream() -> Generator[MockUpstream, None, None]:
    """Start a mock JSON-RPC upstream server.

    Yields:
        A running ``MockUpstream`` instance on port 19545.

    """
    with MockUpstream(port=19545) as upstream:
        yield upstream


@pytest.fixture()
def erpc_process(
    erpc_binary: str,
    mock_upstream: MockUpstream,
) -> Generator[ERPCProcess, None, None]:
    """Start an eRPC process configured to proxy through the mock upstream.

    Uses non-default ports (14000/14001) to avoid conflicts.

    Yields:
        A running, healthy ``ERPCProcess`` instance.

    """
    config = ERPCConfig(
        upstreams={1: [mock_upstream.url]},
        server_port=14000,
        metrics_port=14001,
    )
    proc = ERPCProcess(config=config, binary_path=erpc_binary)
    proc.start()
    proc.wait_for_health(timeout=30)
    yield proc
    if proc.is_running:
        proc.stop()
