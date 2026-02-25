"""Tests for erpc.client — HTTP client for eRPC health and metrics."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from erpc.client import ERPCClient, HealthStatus
from erpc.exceptions import ERPCHealthCheckError

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_HEALTH_JSON = json.dumps({"status": "ok", "uptime": 12345.6, "version": "0.0.49"}).encode()

SAMPLE_METRICS_TEXT = b"""\
# HELP erpc_requests_total Total requests
# TYPE erpc_requests_total counter
erpc_requests_total{method="eth_call"} 42
erpc_requests_total{method="eth_getBalance"} 7
# HELP erpc_cache_hits_total Cache hits
# TYPE erpc_cache_hits_total counter
erpc_cache_hits_total 100
# HELP erpc_uptime_seconds Uptime in seconds
# TYPE erpc_uptime_seconds gauge
erpc_uptime_seconds 12345.6
"""


def _mock_response(data: bytes, status: int = 200) -> MagicMock:
    """Build a fake :class:`http.client.HTTPResponse`-like context manager."""
    resp = MagicMock()
    resp.status = status
    resp.read.return_value = data
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


# ---------------------------------------------------------------------------
# HealthStatus dataclass
# ---------------------------------------------------------------------------


class TestHealthStatus:
    """Tests for the HealthStatus dataclass."""

    def test_fields(self) -> None:
        hs = HealthStatus(status="ok", uptime=1.0, version="0.0.1")
        assert hs.status == "ok"
        assert hs.uptime == 1.0
        assert hs.version == "0.0.1"

    def test_equality(self) -> None:
        a = HealthStatus(status="ok", uptime=1.0, version="0.0.1")
        b = HealthStatus(status="ok", uptime=1.0, version="0.0.1")
        assert a == b

    def test_repr(self) -> None:
        hs = HealthStatus(status="ok", uptime=0.0, version="1.0.0")
        assert "ok" in repr(hs)

    def test_from_dict_factory(self) -> None:
        data: dict[str, Any] = {"status": "ok", "uptime": 99.0, "version": "0.1.0"}
        hs = HealthStatus.from_dict(data)
        assert hs == HealthStatus(status="ok", uptime=99.0, version="0.1.0")

    def test_from_dict_missing_fields_use_defaults(self) -> None:
        hs = HealthStatus.from_dict({})
        assert hs.status == "unknown"
        assert hs.uptime == 0.0
        assert hs.version == "unknown"


# ---------------------------------------------------------------------------
# ERPCClient construction
# ---------------------------------------------------------------------------


class TestERPCClientInit:
    """Tests for client initialisation and URL handling."""

    def test_base_url_stored(self) -> None:
        client = ERPCClient("http://localhost:4000")
        assert client.base_url == "http://localhost:4000"

    def test_trailing_slash_stripped(self) -> None:
        client = ERPCClient("http://localhost:4000/")
        assert client.base_url == "http://localhost:4000"

    def test_custom_metrics_port(self) -> None:
        client = ERPCClient("http://localhost:4000", metrics_port=9090)
        assert client.metrics_port == 9090

    def test_default_metrics_port(self) -> None:
        client = ERPCClient("http://localhost:4000")
        assert client.metrics_port == 4001

    def test_custom_timeout(self) -> None:
        client = ERPCClient("http://localhost:4000", timeout=10)
        assert client.timeout == 10

    def test_default_timeout(self) -> None:
        client = ERPCClient("http://localhost:4000")
        assert client.timeout == 5


# ---------------------------------------------------------------------------
# health()
# ---------------------------------------------------------------------------


class TestHealth:
    """Tests for ERPCClient.health()."""

    @patch("erpc.client.urlopen")
    def test_health_success(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.return_value = _mock_response(SAMPLE_HEALTH_JSON)
        client = ERPCClient("http://localhost:4000")
        result = client.health()
        assert isinstance(result, HealthStatus)
        assert result.status == "ok"
        assert result.uptime == 12345.6
        assert result.version == "0.0.49"

    @patch("erpc.client.urlopen")
    def test_health_connection_refused(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.side_effect = ConnectionRefusedError("Connection refused")
        client = ERPCClient("http://localhost:4000")
        with pytest.raises(ERPCHealthCheckError, match="Connection refused"):
            client.health()

    @patch("erpc.client.urlopen")
    def test_health_timeout(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.side_effect = TimeoutError("timed out")
        client = ERPCClient("http://localhost:4000")
        with pytest.raises(ERPCHealthCheckError, match="timed out"):
            client.health()

    @patch("erpc.client.urlopen")
    def test_health_non_json_response(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.return_value = _mock_response(b"not json")
        client = ERPCClient("http://localhost:4000")
        with pytest.raises(ERPCHealthCheckError, match="parse"):
            client.health()

    @patch("erpc.client.urlopen")
    def test_health_uses_timeout(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.return_value = _mock_response(SAMPLE_HEALTH_JSON)
        client = ERPCClient("http://localhost:4000", timeout=7)
        client.health()
        _, kwargs = mock_urlopen.call_args
        assert kwargs["timeout"] == 7


# ---------------------------------------------------------------------------
# is_healthy
# ---------------------------------------------------------------------------


class TestIsHealthy:
    """Tests for the is_healthy convenience property."""

    @patch("erpc.client.urlopen")
    def test_is_healthy_true(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.return_value = _mock_response(SAMPLE_HEALTH_JSON)
        assert ERPCClient("http://localhost:4000").is_healthy is True

    @patch("erpc.client.urlopen")
    def test_is_healthy_false_on_error(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.side_effect = ConnectionRefusedError()
        assert ERPCClient("http://localhost:4000").is_healthy is False


# ---------------------------------------------------------------------------
# metrics()
# ---------------------------------------------------------------------------


class TestMetrics:
    """Tests for ERPCClient.metrics()."""

    @patch("erpc.client.urlopen")
    def test_metrics_success(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.return_value = _mock_response(SAMPLE_METRICS_TEXT)
        client = ERPCClient("http://localhost:4000")
        result = client.metrics()
        assert isinstance(result, dict)
        assert result['erpc_requests_total{method="eth_call"}'] == 42.0
        assert result["erpc_cache_hits_total"] == 100.0
        assert result["erpc_uptime_seconds"] == 12345.6

    @patch("erpc.client.urlopen")
    def test_metrics_endpoint_unavailable(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.side_effect = ConnectionRefusedError("refused")
        client = ERPCClient("http://localhost:4000")
        with pytest.raises(ERPCHealthCheckError, match="metrics"):
            client.metrics()

    @patch("erpc.client.urlopen")
    def test_metrics_uses_metrics_port(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.return_value = _mock_response(b"# empty\n")
        client = ERPCClient("http://localhost:4000", metrics_port=9090)
        client.metrics()
        url_arg = mock_urlopen.call_args[0][0]
        assert ":9090" in url_arg


# ---------------------------------------------------------------------------
# ERPCProcess.client integration
# ---------------------------------------------------------------------------


class TestProcessClientIntegration:
    """Tests for ERPCProcess.client property."""

    @patch("erpc.process.find_erpc_binary", return_value="/usr/local/bin/erpc")
    def test_process_client_returns_erpc_client(self, _mock_bin: MagicMock) -> None:
        from erpc.process import ERPCProcess

        proc = ERPCProcess(upstreams={1: ["https://eth.llamarpc.com"]})
        client = proc.client
        assert isinstance(client, ERPCClient)

    @patch("erpc.process.find_erpc_binary", return_value="/usr/local/bin/erpc")
    def test_process_client_uses_correct_urls(self, _mock_bin: MagicMock) -> None:
        from erpc.process import ERPCProcess

        proc = ERPCProcess(upstreams={1: ["https://eth.llamarpc.com"]})
        client = proc.client
        assert "4000" in client.base_url
        assert client.metrics_port == 4001

    @patch("erpc.process.find_erpc_binary", return_value="/usr/local/bin/erpc")
    def test_process_client_cached(self, _mock_bin: MagicMock) -> None:
        from erpc.process import ERPCProcess

        proc = ERPCProcess(upstreams={1: ["https://eth.llamarpc.com"]})
        assert proc.client is proc.client
