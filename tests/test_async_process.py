"""Tests for async eRPC process management."""

from __future__ import annotations

import asyncio
import signal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from erpc.async_process import AsyncERPCProcess
from erpc.config import ERPCConfig
from erpc.exceptions import (
    ERPCHealthCheckError,
    ERPCNotRunning,
    ERPCStartupError,
)


@pytest.fixture()
def binary(tmp_path):
    """Create a fake eRPC binary."""
    b = tmp_path / "erpc"
    b.write_text("#!/bin/bash")
    b.chmod(0o755)
    return str(b)


def _make_proc(binary: str) -> AsyncERPCProcess:
    return AsyncERPCProcess(
        upstreams={1: ["https://rpc.example.com"]},
        binary_path=binary,
    )


class TestAsyncERPCProcess:
    """Tests for AsyncERPCProcess."""

    def test_requires_config_or_upstreams(self) -> None:
        with pytest.raises(ValueError, match="Provide either"):
            AsyncERPCProcess()

    def test_upstreams_shortcut(self, binary: str) -> None:
        proc = _make_proc(binary)
        assert proc.config.upstreams[1] == ["https://rpc.example.com"]

    def test_config_arg(self, binary: str) -> None:
        config = ERPCConfig(upstreams={1: ["https://rpc.example.com"]})
        proc = AsyncERPCProcess(config=config, binary_path=binary)
        assert proc.config is config

    def test_endpoint_url(self, binary: str) -> None:
        proc = _make_proc(binary)
        assert "evm/1" in proc.endpoint_url(1)

    def test_endpoint_property(self, binary: str) -> None:
        proc = _make_proc(binary)
        assert proc.endpoint == "http://127.0.0.1:4000"

    def test_not_running_initially(self, binary: str) -> None:
        proc = _make_proc(binary)
        assert not proc.is_running
        assert proc.pid is None

    @pytest.mark.asyncio()
    async def test_stop_when_not_running(self, binary: str) -> None:
        proc = _make_proc(binary)
        with pytest.raises(ERPCNotRunning):
            await proc.stop()

    @pytest.mark.asyncio()
    async def test_is_healthy_returns_false_when_unreachable(self, binary: str) -> None:
        proc = _make_proc(binary)
        proc.config.server_port = 59999
        assert not await proc.is_healthy()

    @pytest.mark.asyncio()
    async def test_start_already_running(self, binary: str) -> None:
        proc = _make_proc(binary)
        mock = MagicMock()
        mock.returncode = None
        proc._proc = mock
        with pytest.raises(ERPCStartupError, match="already running"):
            await proc.start()

    @pytest.mark.asyncio()
    async def test_start_os_error(self, binary: str) -> None:
        proc = _make_proc(binary)
        with (
            patch(
                "asyncio.create_subprocess_exec",
                side_effect=OSError("boom"),
            ),
            pytest.raises(ERPCStartupError, match="Failed to start"),
        ):
            await proc.start()

    @pytest.mark.asyncio()
    async def test_start_immediate_exit(self, binary: str) -> None:
        proc = _make_proc(binary)
        mock = AsyncMock()
        mock.returncode = 1
        mock_stderr = AsyncMock()
        mock_stderr.read = AsyncMock(return_value=b"error")
        mock.stderr = mock_stderr
        with (
            patch("asyncio.create_subprocess_exec", return_value=mock),
            pytest.raises(ERPCStartupError, match="exited immediately"),
        ):
            await proc.start()

    @pytest.mark.asyncio()
    async def test_stop_already_stopped(self, binary: str) -> None:
        proc = _make_proc(binary)
        mock = MagicMock()
        mock.returncode = 0
        proc._proc = mock
        await proc.stop()
        assert proc._proc is None

    @pytest.mark.asyncio()
    async def test_stop_graceful(self, binary: str) -> None:
        proc = _make_proc(binary)
        mock = MagicMock()
        mock.returncode = None
        mock.pid = 12345
        mock.send_signal = MagicMock()
        mock.wait = AsyncMock(return_value=0)
        proc._proc = mock
        await proc.stop()
        mock.send_signal.assert_called_once_with(signal.SIGTERM)
        assert proc._proc is None

    @pytest.mark.asyncio()
    async def test_stop_force_kill(self, binary: str) -> None:
        proc = _make_proc(binary)
        mock = MagicMock()
        mock.returncode = None
        mock.pid = 12345
        mock.send_signal = MagicMock()
        mock.kill = MagicMock()
        mock.wait = AsyncMock(side_effect=[asyncio.TimeoutError, None])
        proc._proc = mock
        await proc.stop()
        mock.kill.assert_called_once()

    @pytest.mark.asyncio()
    async def test_restart(self, binary: str) -> None:
        proc = _make_proc(binary)
        mock_inner = MagicMock()
        mock_inner.returncode = None
        proc._proc = mock_inner
        with (
            patch.object(proc, "stop", new_callable=AsyncMock) as mock_stop,
            patch.object(proc, "start", new_callable=AsyncMock) as mock_start,
        ):
            await proc.restart()
            mock_stop.assert_awaited_once()
            mock_start.assert_awaited_once()

    @pytest.mark.asyncio()
    async def test_restart_when_not_running(self, binary: str) -> None:
        proc = _make_proc(binary)
        with patch.object(proc, "start", new_callable=AsyncMock) as mock_start:
            await proc.restart()
            mock_start.assert_awaited_once()

    @pytest.mark.asyncio()
    async def test_wait_for_health_process_dies(self, binary: str) -> None:
        proc = _make_proc(binary)
        mock = MagicMock()
        mock.returncode = 1
        proc._proc = mock
        with pytest.raises(ERPCStartupError, match="died during health check"):
            await proc.wait_for_health(timeout=1)

    @pytest.mark.asyncio()
    async def test_wait_for_health_timeout(self, binary: str) -> None:
        proc = _make_proc(binary)
        mock = MagicMock()
        mock.returncode = None
        proc._proc = mock
        proc.config.server_port = 59999
        with pytest.raises(ERPCHealthCheckError, match="did not become healthy"):
            await proc.wait_for_health(timeout=1)

    @pytest.mark.asyncio()
    async def test_context_manager_exit_stops(self, binary: str) -> None:
        proc = _make_proc(binary)
        mock = MagicMock()
        mock.returncode = None
        mock.pid = 12345
        mock.send_signal = MagicMock()
        mock.wait = AsyncMock(return_value=0)
        proc._proc = mock
        await proc.__aexit__(None, None, None)
        assert proc._proc is None

    def test_cleanup_with_config_path(self, binary: str, tmp_path) -> None:
        proc = _make_proc(binary)
        config_file = tmp_path / "test.yaml"
        config_file.write_text("test")
        proc._config_path = config_file
        proc._proc = MagicMock()
        proc._cleanup()
        assert not config_file.exists()
        assert proc._proc is None
        assert proc._config_path is None
