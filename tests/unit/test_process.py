"""Tests for eRPC process management."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from erpc.config import ERPCConfig
from erpc.exceptions import (
    ERPCHealthCheckError,
    ERPCNotFound,
    ERPCNotRunning,
    ERPCStartupError,
)
from erpc.process import ERPCProcess, find_erpc_binary


class TestFindBinary:
    def test_explicit_path(self, tmp_path):
        binary = tmp_path / "erpc"
        binary.write_text("#!/bin/bash")
        binary.chmod(0o755)
        assert find_erpc_binary(str(binary)) == str(binary)

    def test_env_var(self, tmp_path, monkeypatch):
        binary = tmp_path / "erpc"
        binary.write_text("#!/bin/bash")
        binary.chmod(0o755)
        monkeypatch.setenv("ERPC_BINARY", str(binary))
        assert find_erpc_binary() == str(binary)

    def test_not_found(self, monkeypatch):
        monkeypatch.delenv("ERPC_BINARY", raising=False)
        with (
            patch("shutil.which", return_value=None),
            patch("os.path.isfile", return_value=False),
            patch("erpc.install.install_erpc", side_effect=ERPCNotFound("install failed")),
            pytest.raises(ERPCNotFound),
        ):
            find_erpc_binary("/nonexistent/erpc")

    def test_which_fallback(self, monkeypatch):
        monkeypatch.delenv("ERPC_BINARY", raising=False)
        with (
            patch("shutil.which", return_value="/usr/bin/erpc"),
            patch("os.path.isfile", return_value=False),
        ):
            assert find_erpc_binary() == "/usr/bin/erpc"


class TestERPCProcess:
    def _make_proc(self, tmp_path):
        binary = tmp_path / "erpc"
        binary.write_text("#!/bin/bash")
        binary.chmod(0o755)
        return ERPCProcess(
            upstreams={1: ["https://rpc.example.com"]},
            binary_path=str(binary),
        )

    def test_requires_config_or_upstreams(self):
        with pytest.raises(ValueError, match="Provide either"):
            ERPCProcess()

    def test_upstreams_shortcut(self, tmp_path):
        proc = self._make_proc(tmp_path)
        assert proc.config.upstreams[1] == ["https://rpc.example.com"]

    def test_config_arg(self, tmp_path):
        binary = tmp_path / "erpc"
        binary.write_text("#!/bin/bash")
        binary.chmod(0o755)
        config = ERPCConfig(upstreams={1: ["https://rpc.example.com"]})
        proc = ERPCProcess(config=config, binary_path=str(binary))
        assert proc.config is config

    def test_endpoint_url(self, tmp_path):
        proc = self._make_proc(tmp_path)
        assert "evm/1" in proc.endpoint_url(1)

    def test_endpoint_property(self, tmp_path):
        proc = self._make_proc(tmp_path)
        assert proc.endpoint == "http://127.0.0.1:4000"

    def test_not_running_initially(self, tmp_path):
        proc = self._make_proc(tmp_path)
        assert not proc.is_running
        assert not proc.is_alive
        assert proc.pid is None

    def test_stop_when_not_running(self, tmp_path):
        proc = self._make_proc(tmp_path)
        with pytest.raises(ERPCNotRunning):
            proc.stop()

    def test_is_healthy_returns_false_when_unreachable(self, tmp_path):
        proc = self._make_proc(tmp_path)
        # Use a port nothing listens on
        proc.config.server_port = 59999
        assert not proc.is_healthy

    def test_start_already_running(self, tmp_path):
        proc = self._make_proc(tmp_path)
        mock_popen = MagicMock()
        mock_popen.poll.return_value = None
        proc._proc = mock_popen
        with pytest.raises(ERPCStartupError, match="already running"):
            proc.start()

    def test_start_os_error(self, tmp_path):
        proc = self._make_proc(tmp_path)
        with (
            patch("subprocess.Popen", side_effect=OSError("boom")),
            pytest.raises(ERPCStartupError, match="Failed to start"),
        ):
            proc.start()

    def test_start_immediate_exit(self, tmp_path):
        proc = self._make_proc(tmp_path)
        mock_popen = MagicMock()
        mock_popen.poll.return_value = 1
        mock_popen.returncode = 1
        mock_stderr = MagicMock()
        mock_stderr.read.return_value = b"error"
        mock_popen.stderr = mock_stderr
        with (
            patch("subprocess.Popen", return_value=mock_popen),
            pytest.raises(ERPCStartupError, match="exited immediately"),
        ):
            proc.start()

    def test_stop_already_stopped(self, tmp_path):
        proc = self._make_proc(tmp_path)
        mock_popen = MagicMock()
        mock_popen.poll.return_value = 0  # already exited
        proc._proc = mock_popen
        proc.stop()
        assert proc._proc is None

    def test_stop_graceful(self, tmp_path):
        proc = self._make_proc(tmp_path)
        mock_popen = MagicMock()
        mock_popen.poll.return_value = None
        mock_popen.wait.return_value = 0
        mock_popen.pid = 12345
        proc._proc = mock_popen
        proc.stop()
        mock_popen.send_signal.assert_called_once()
        assert proc._proc is None

    def test_stop_force_kill(self, tmp_path):
        proc = self._make_proc(tmp_path)
        mock_popen = MagicMock()
        mock_popen.poll.return_value = None
        mock_popen.wait.side_effect = [subprocess.TimeoutExpired("erpc", 5), None]
        mock_popen.pid = 12345
        proc._proc = mock_popen
        proc.stop()
        mock_popen.kill.assert_called_once()

    def test_restart(self, tmp_path):
        proc = self._make_proc(tmp_path)
        with (
            patch.object(proc, "stop") as mock_stop,
            patch.object(proc, "start") as mock_start,
            patch.object(type(proc), "is_running", new_callable=lambda: property(lambda s: True)),
        ):
            proc.restart()
            mock_stop.assert_called_once()
            mock_start.assert_called_once()

    def test_restart_when_not_running(self, tmp_path):
        proc = self._make_proc(tmp_path)
        with patch.object(proc, "start") as mock_start:
            proc.restart()
            mock_start.assert_called_once()

    def test_wait_for_health_process_dies(self, tmp_path):
        proc = self._make_proc(tmp_path)
        proc._proc = MagicMock()
        proc._proc.poll.return_value = 1  # process died
        with pytest.raises(ERPCStartupError, match="died during health check"):
            proc.wait_for_health(timeout=1)

    def test_wait_for_health_timeout(self, tmp_path):
        proc = self._make_proc(tmp_path)
        proc._proc = MagicMock()
        proc._proc.poll.return_value = None  # still running
        proc.config.server_port = 59999  # unreachable
        with pytest.raises(ERPCHealthCheckError, match="did not become healthy"):
            proc.wait_for_health(timeout=1)

    def test_cleanup_with_config_path(self, tmp_path):
        proc = self._make_proc(tmp_path)
        config_file = tmp_path / "test.yaml"
        config_file.write_text("test")
        proc._config_path = config_file
        proc._proc = MagicMock()
        proc._cleanup()
        assert not config_file.exists()
        assert proc._proc is None
        assert proc._config_path is None

    def test_cleanup_missing_config(self, tmp_path):
        proc = self._make_proc(tmp_path)
        proc._config_path = tmp_path / "nonexistent.yaml"
        proc._proc = MagicMock()
        proc._cleanup()  # should not raise

    def test_context_manager_exit_stops(self, tmp_path):
        proc = self._make_proc(tmp_path)
        mock_popen = MagicMock()
        mock_popen.poll.return_value = None
        mock_popen.wait.return_value = 0
        mock_popen.pid = 12345
        proc._proc = mock_popen
        proc.__exit__(None, None, None)
        assert proc._proc is None

    def test_check_upstream_health_not_running(self, tmp_path):
        """Test check_upstream_health when process is not running."""
        proc = self._make_proc(tmp_path)
        with pytest.raises(ERPCNotRunning):
            proc.check_upstream_health()

    def test_check_upstream_health_metrics_error(self, tmp_path):
        """Test check_upstream_health when metrics fetch fails."""
        proc = self._make_proc(tmp_path)
        mock_popen = MagicMock()
        mock_popen.poll.return_value = None
        proc._proc = mock_popen

        mock_client = MagicMock()
        mock_client.metrics.side_effect = ERPCHealthCheckError("connection failed")
        proc._client = mock_client

        with pytest.raises(ERPCHealthCheckError, match="Failed to fetch metrics"):
            proc.check_upstream_health()

    def test_check_upstream_health_with_health_metrics(self, tmp_path):
        """Test check_upstream_health with direct health metrics."""
        proc = self._make_proc(tmp_path)
        mock_popen = MagicMock()
        mock_popen.poll.return_value = None
        proc._proc = mock_popen

        metrics = {
            'erpc_upstream_health{chain_id="1",upstream="upstream_1"}': 1.0,
            'erpc_upstream_health{chain_id="1",upstream="upstream_2"}': 0.0,
            'erpc_upstream_health{chain_id="137",upstream="upstream_1"}': 1.0,
        }

        mock_client = MagicMock()
        mock_client.metrics.return_value = metrics
        proc._client = mock_client

        result = proc.check_upstream_health()

        expected = {
            1: {"upstream_1": True, "upstream_2": False},
            137: {"upstream_1": True},
        }
        assert result == expected

    def test_check_upstream_health_with_status_metrics(self, tmp_path):
        """Test check_upstream_health with status variation metrics."""
        proc = self._make_proc(tmp_path)
        mock_popen = MagicMock()
        mock_popen.poll.return_value = None
        proc._proc = mock_popen

        metrics = {
            'erpc_upstream_status{chain_id="1",upstream="upstream_1"}': 1.0,
            'erpc_upstream_available{chain_id="1",upstream="upstream_2"}': 0.0,
        }

        mock_client = MagicMock()
        mock_client.metrics.return_value = metrics
        proc._client = mock_client

        result = proc.check_upstream_health()

        expected = {1: {"upstream_1": True, "upstream_2": False}}
        assert result == expected

    def test_check_upstream_health_with_request_metrics(self, tmp_path):
        """Test check_upstream_health inferring from request success/error rates."""
        proc = self._make_proc(tmp_path)
        mock_popen = MagicMock()
        mock_popen.poll.return_value = None
        proc._proc = mock_popen

        metrics = {
            'erpc_requests_total{chain_id="1",upstream="upstream_1"}': 100.0,
            'erpc_requests_failed{chain_id="1",upstream="upstream_1"}': 10.0,
            'erpc_requests_success{chain_id="1",upstream="upstream_2"}': 20.0,
            'erpc_requests_failed{chain_id="1",upstream="upstream_2"}': 80.0,
            'erpc_requests_total{chain_id="137",upstream="upstream_1"}': 50.0,
            'erpc_requests_failed{chain_id="137",upstream="upstream_1"}': 5.0,
        }

        mock_client = MagicMock()
        mock_client.metrics.return_value = metrics
        proc._client = mock_client

        result = proc.check_upstream_health()

        # upstream_1 on chain 1: 90% success (healthy)
        # upstream_2 on chain 1: 20% success (unhealthy)
        # upstream_1 on chain 137: 90% success (healthy)
        expected = {
            1: {"upstream_1": True, "upstream_2": False},
            137: {"upstream_1": True},
        }
        assert result == expected

    def test_check_upstream_health_no_activity(self, tmp_path):
        """Test check_upstream_health with upstreams that have no activity."""
        proc = self._make_proc(tmp_path)
        mock_popen = MagicMock()
        mock_popen.poll.return_value = None
        proc._proc = mock_popen

        metrics = {
            'erpc_requests_total{chain_id="1",upstream="upstream_1"}': 0.0,
            'erpc_requests_failed{chain_id="1",upstream="upstream_1"}': 0.0,
        }

        mock_client = MagicMock()
        mock_client.metrics.return_value = metrics
        proc._client = mock_client

        result = proc.check_upstream_health()

        # No activity should be considered unhealthy
        expected = {1: {"upstream_1": False}}
        assert result == expected

    def test_check_upstream_health_empty_metrics(self, tmp_path):
        """Test check_upstream_health with empty metrics."""
        proc = self._make_proc(tmp_path)
        mock_popen = MagicMock()
        mock_popen.poll.return_value = None
        proc._proc = mock_popen

        mock_client = MagicMock()
        mock_client.metrics.return_value = {}
        proc._client = mock_client

        result = proc.check_upstream_health()

        assert result == {}

    def test_parse_upstream_health_metrics_complex(self, tmp_path):
        """Test _parse_upstream_health_metrics with complex metric names."""
        proc = self._make_proc(tmp_path)
        metrics = {
            'erpc_upstream_health{chain_id="1",upstream="upstream_1",status="active"}': 1.0,
            'erpc_upstream_health{chain_id="1",upstream="upstream_2",status="inactive"}': 0.0,
            'erpc_other_metric{chain_id="1"}': 42.0,  # Should be ignored
            'erpc_upstream_health{chain_id="invalid",upstream="test"}': 1.0,  # Invalid chain_id
        }

        result = proc._parse_upstream_health_metrics(metrics)
        expected = {1: {"upstream_1": True, "upstream_2": False}}
        assert result == expected

    def test_parse_upstream_health_metrics_edge_cases(self, tmp_path):
        """Test _parse_upstream_health_metrics with edge case values."""
        proc = self._make_proc(tmp_path)
        metrics = {
            'erpc_upstream_health{chain_id="1",upstream="upstream_1"}': 0.5,  # Positive but < 1
            'erpc_upstream_health{chain_id="1",upstream="upstream_2"}': -1.0,  # Negative
            'erpc_upstream_health{chain_id="1",upstream="upstream_3"}': 1.1,  # > 1
        }

        result = proc._parse_upstream_health_metrics(metrics)
        expected = {
            1: {
                "upstream_1": True,  # 0.5 > 0.0
                "upstream_2": False,  # -1.0 <= 0.0
                "upstream_3": True,  # 1.1 > 0.0
            }
        }
        assert result == expected
