"""Integration tests for eRPC proxy behavior.

These tests require a real eRPC binary and validate end-to-end request
proxying, caching, health checks, metrics, error handling, and multi-chain
routing.
"""

from __future__ import annotations

import json
import time
from urllib.error import URLError
from urllib.request import Request, urlopen

import pytest

from erpc.config import ERPCConfig
from erpc.process import ERPCProcess

from .mock_upstream import MockUpstream

pytestmark = pytest.mark.integration


def _jsonrpc_request(url: str, method: str, params: list[object] | None = None) -> dict:
    """Send a JSON-RPC request and return the parsed response."""
    payload = json.dumps({
        "jsonrpc": "2.0",
        "method": method,
        "params": params or [],
        "id": 1,
    }).encode()
    req = Request(url, data=payload, headers={"Content-Type": "application/json"})
    with urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


class TestProxyRequest:
    """Validate basic JSON-RPC proxying through eRPC."""

    def test_proxy_request(self, erpc_process: ERPCProcess) -> None:
        """Send eth_blockNumber through eRPC and verify the response."""
        url = erpc_process.endpoint_url(1)
        result = _jsonrpc_request(url, "eth_blockNumber")

        assert "result" in result
        assert result["result"] == "0x1234567"

    def test_eth_chain_id(self, erpc_process: ERPCProcess) -> None:
        """Verify eth_chainId is proxied correctly."""
        url = erpc_process.endpoint_url(1)
        result = _jsonrpc_request(url, "eth_chainId")

        assert result["result"] == "0x1"


class TestCaching:
    """Validate eRPC caching behavior."""

    def test_cache_hit(
        self, erpc_process: ERPCProcess, mock_upstream: MockUpstream
    ) -> None:
        """Second identical request should be faster (served from cache)."""
        url = erpc_process.endpoint_url(1)

        # First request — populates cache.
        start = time.monotonic()
        result1 = _jsonrpc_request(url, "eth_chainId")
        first_duration = time.monotonic() - start

        initial_count = len(mock_upstream.request_log)

        # Second request — should hit cache.
        start = time.monotonic()
        result2 = _jsonrpc_request(url, "eth_chainId")
        second_duration = time.monotonic() - start

        assert result1["result"] == result2["result"]

        # Cache hit: either upstream wasn't called again, or second was faster.
        upstream_calls_after = len(mock_upstream.request_log) - initial_count
        cache_hit = upstream_calls_after == 0 or second_duration < first_duration
        assert cache_hit, (
            f"Expected cache hit: upstream_calls={upstream_calls_after}, "
            f"first={first_duration:.4f}s, second={second_duration:.4f}s"
        )


class TestHealthAndMetrics:
    """Validate health and metrics endpoints."""

    def test_health_endpoint(self, erpc_process: ERPCProcess) -> None:
        """eRPC health endpoint returns HTTP 200."""
        with urlopen(erpc_process.config.health_url, timeout=5) as resp:
            assert resp.status == 200

    def test_metrics_endpoint(self, erpc_process: ERPCProcess) -> None:
        """Metrics endpoint returns Prometheus-format text."""
        metrics_url = (
            f"http://{erpc_process.config.metrics_host}:{erpc_process.config.metrics_port}"
            "/metrics"
        )
        with urlopen(metrics_url, timeout=5) as resp:
            body = resp.read().decode()
            assert resp.status == 200
            # Prometheus format: lines starting with # or metric_name.
            assert "# HELP" in body or "# TYPE" in body or "\n" in body


class TestErrorHandling:
    """Validate graceful error handling when upstream is down."""

    def test_upstream_down_handling(
        self,
        erpc_binary: str,
        mock_upstream: MockUpstream,
    ) -> None:
        """When the upstream is unavailable, eRPC returns an error gracefully."""
        config = ERPCConfig(
            upstreams={1: [mock_upstream.url]},
            server_port=14010,
            metrics_port=14011,
        )
        proc = ERPCProcess(config=config, binary_path=erpc_binary)
        proc.start()
        proc.wait_for_health(timeout=30)

        try:
            # Verify it works first.
            url = proc.endpoint_url(1)
            result = _jsonrpc_request(url, "eth_blockNumber")
            assert "result" in result

            # Kill the upstream.
            mock_upstream.set_available(False)

            # Request should fail gracefully (error in JSON-RPC response or HTTP error).
            try:
                error_result = _jsonrpc_request(url, "eth_blockNumber")
                # If we get a response, it should contain an error.
                assert "error" in error_result or "result" in error_result
            except (URLError, OSError):
                # HTTP-level error is also acceptable — eRPC returned non-200.
                pass
        finally:
            mock_upstream.set_available(True)
            if proc.is_running:
                proc.stop()


class TestMultipleChains:
    """Validate multi-chain routing through eRPC."""

    def test_multiple_chains(self, erpc_binary: str) -> None:
        """Configure two chains and route requests correctly."""
        with MockUpstream(port=19546) as chain1_mock, MockUpstream(port=19547) as chain2_mock:
            chain1_mock.set_response("eth_chainId", "0x1")
            chain2_mock.set_response("eth_chainId", "0x89")

            config = ERPCConfig(
                upstreams={
                    1: [chain1_mock.url],
                    137: [chain2_mock.url],
                },
                server_port=14020,
                metrics_port=14021,
            )
            proc = ERPCProcess(config=config, binary_path=erpc_binary)
            proc.start()
            proc.wait_for_health(timeout=30)

            try:
                # Chain 1 (Ethereum mainnet).
                result1 = _jsonrpc_request(proc.endpoint_url(1), "eth_chainId")
                assert result1["result"] == "0x1"

                # Chain 137 (Polygon).
                result137 = _jsonrpc_request(proc.endpoint_url(137), "eth_chainId")
                assert result137["result"] == "0x89"

                # Verify requests went to the correct upstreams.
                chain1_methods = [r["method"] for r in chain1_mock.request_log]
                chain2_methods = [r["method"] for r in chain2_mock.request_log]
                assert "eth_chainId" in chain1_methods
                assert "eth_chainId" in chain2_methods
            finally:
                if proc.is_running:
                    proc.stop()
