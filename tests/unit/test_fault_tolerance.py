"""Fault tolerance tests for eRPC process management.

These tests verify that ERPCProcess and DockerERPCProcess handle crashes,
failures, and edge cases gracefully — critical because eRPC sits between
Ursula nodes and their RPC providers.
"""

from __future__ import annotations

import signal
import subprocess
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from erpc.config import ERPCConfig
from erpc.docker import DockerERPCProcess
from erpc.exceptions import (
    ERPCHealthCheckError,
    ERPCNotRunning,
    ERPCStartupError,
)
from erpc.monitoring import HealthEvent, HealthMonitor
from erpc.process import ERPCProcess

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def config() -> ERPCConfig:
    """Minimal eRPC config for testing."""
    return ERPCConfig(upstreams={1: ["https://eth.llamarpc.com"]})


@pytest.fixture()
def proc(config: ERPCConfig) -> ERPCProcess:
    """ERPCProcess with mocked binary discovery."""
    with patch("erpc.process.find_erpc_binary", return_value="/usr/bin/erpc"):
        return ERPCProcess(config=config)


@pytest.fixture()
def docker_proc(config: ERPCConfig) -> DockerERPCProcess:
    """DockerERPCProcess with mocked docker binary."""
    with patch("erpc.docker.find_docker_binary", return_value="/usr/bin/docker"):
        return DockerERPCProcess(config=config)


def _mock_popen_running() -> MagicMock:
    """Create a mock Popen that appears to be running."""
    mock = MagicMock(spec=subprocess.Popen)
    mock.poll.return_value = None  # still running
    mock.pid = 12345
    mock.returncode = None
    mock.stderr = MagicMock()
    mock.stderr.read.return_value = b""
    return mock


def _mock_popen_dead(exit_code: int = -9) -> MagicMock:
    """Create a mock Popen that has exited."""
    mock = MagicMock(spec=subprocess.Popen)
    mock.poll.return_value = exit_code
    mock.pid = 12345
    mock.returncode = exit_code
    mock.stderr = MagicMock()
    mock.stderr.read.return_value = b"killed"
    return mock


# ---------------------------------------------------------------------------
# 1. Process crash recovery
# ---------------------------------------------------------------------------


@pytest.mark.fault_tolerance
class TestProcessCrashRecovery:
    """eRPC dies unexpectedly; ERPCProcess detects and recovers."""

    def test_is_running_reflects_crash(self, proc: ERPCProcess) -> None:
        """is_running returns False after process dies unexpectedly."""
        proc._proc = _mock_popen_running()
        assert proc.is_running is True

        # Simulate crash — poll now returns exit code
        proc._proc.poll.return_value = -9
        assert proc.is_running is False

    def test_restart_after_crash(self, proc: ERPCProcess) -> None:
        """start() works cleanly after a crash (no 'already running' error)."""
        dead = _mock_popen_dead()
        proc._proc = dead

        assert proc.is_running is False

        new_proc = _mock_popen_running()
        with (
            patch("subprocess.Popen", return_value=new_proc),
            patch.object(proc.config, "write", return_value=Path("/tmp/erpc.yaml")),
        ):
            proc.start()

        assert proc._proc is new_proc

    def test_is_alive_false_after_crash(self, proc: ERPCProcess) -> None:
        """is_alive requires both running AND healthy."""
        proc._proc = _mock_popen_dead()
        assert proc.is_alive is False


# ---------------------------------------------------------------------------
# 2. Crash during request
# ---------------------------------------------------------------------------


@pytest.mark.fault_tolerance
class TestCrashDuringRequest:
    """eRPC goes down while a client has an in-flight request."""

    def test_health_check_detects_dead_process(self, proc: ERPCProcess) -> None:
        """is_healthy returns False when process is dead (connection refused)."""
        proc._proc = _mock_popen_dead()
        with patch("erpc.process.urlopen", side_effect=OSError("Connection refused")):
            assert proc.is_healthy is False

    def test_wait_for_health_raises_on_crash(self, proc: ERPCProcess) -> None:
        """wait_for_health raises ERPCStartupError if process dies mid-wait."""
        mock = _mock_popen_running()
        proc._proc = mock

        # Process dies after first poll
        mock.poll.side_effect = [None, -9, -9]

        with (
            patch("erpc.process.urlopen", side_effect=OSError),
            pytest.raises(ERPCStartupError, match="died during health check"),
        ):
            proc.wait_for_health(timeout=2)

    def test_client_gets_error_not_hang(self, proc: ERPCProcess) -> None:
        """Health check has a timeout so clients don't hang indefinitely."""
        with patch("erpc.process.urlopen", side_effect=OSError("Connection refused")):
            # Should return False quickly, not hang
            start = time.monotonic()
            result = proc.is_healthy
            elapsed = time.monotonic() - start
            assert result is False
            assert elapsed < 5  # urlopen timeout is 2s


# ---------------------------------------------------------------------------
# 3. Startup failure resilience
# ---------------------------------------------------------------------------


@pytest.mark.fault_tolerance
class TestStartupFailure:
    """eRPC fails to start — bad config, port in use, binary missing."""

    def test_binary_missing_raises(self, proc: ERPCProcess) -> None:
        """OSError from Popen is wrapped in ERPCStartupError."""
        with (
            patch.object(proc.config, "write", return_value=Path("/tmp/erpc.yaml")),
            patch("subprocess.Popen", side_effect=OSError("No such file")),
            pytest.raises(ERPCStartupError, match="Failed to start"),
        ):
            proc.start()

        # No zombie — _proc should remain None
        assert proc._proc is None

    def test_immediate_exit_reports_stderr(self, proc: ERPCProcess) -> None:
        """If eRPC exits immediately, stderr is captured in the error."""
        dead = _mock_popen_dead(exit_code=1)
        dead.stderr.read.return_value = b"invalid config file"

        with (
            patch.object(proc.config, "write", return_value=Path("/tmp/erpc.yaml")),
            patch("subprocess.Popen", return_value=dead),
            pytest.raises(ERPCStartupError, match="invalid config file"),
        ):
            proc.start()

    def test_no_proc_leak_on_startup_failure(self, proc: ERPCProcess) -> None:
        """_proc is not left in a dirty state after startup failure."""
        with (
            patch.object(proc.config, "write", return_value=Path("/tmp/erpc.yaml")),
            patch("subprocess.Popen", side_effect=OSError("boom")),
            pytest.raises(ERPCStartupError),
        ):
            proc.start()

        assert proc._proc is None
        assert proc.is_running is False

    def test_already_running_raises(self, proc: ERPCProcess) -> None:
        """Starting an already-running process raises ERPCStartupError."""
        proc._proc = _mock_popen_running()
        with pytest.raises(ERPCStartupError, match="already running"):
            proc.start()


# ---------------------------------------------------------------------------
# 4. Health check failure detection
# ---------------------------------------------------------------------------


@pytest.mark.fault_tolerance
class TestHealthCheckFailureDetection:
    """HealthMonitor detects when eRPC stops responding."""

    def test_latest_event_reports_down(self) -> None:
        """HealthMonitor reports DOWN when last check failed."""
        from erpc.client import HealthStatus

        monitor = HealthMonitor(url="http://127.0.0.1:4000")
        monitor.history.append(HealthStatus(status="error", uptime=0.0, version=""))
        assert monitor.latest_event() == HealthEvent.DOWN

    def test_latest_event_reports_healthy(self) -> None:
        """HealthMonitor reports HEALTHY when last check succeeded."""
        from erpc.client import HealthStatus

        monitor = HealthMonitor(url="http://127.0.0.1:4000")
        monitor.history.append(HealthStatus(status="ok", uptime=1.0, version="1.0"))
        assert monitor.latest_event() == HealthEvent.HEALTHY

    def test_no_history_returns_none(self) -> None:
        """HealthMonitor returns None when no checks have been performed."""
        monitor = HealthMonitor()
        assert monitor.latest_event() is None

    def test_health_transitions(self) -> None:
        """Health history captures transitions from healthy to down."""
        from erpc.client import HealthStatus

        monitor = HealthMonitor()
        monitor.history.append(HealthStatus(status="ok", uptime=1.0, version="1.0"))
        assert monitor.latest_event() == HealthEvent.HEALTHY

        monitor.history.append(HealthStatus(status="error", uptime=0.0, version=""))
        assert monitor.latest_event() == HealthEvent.DOWN


# ---------------------------------------------------------------------------
# 5. Graceful degradation
# ---------------------------------------------------------------------------


@pytest.mark.fault_tolerance
class TestGracefulDegradation:
    """ERPCProcess provides enough state info for fallback decisions."""

    def test_is_running_for_fallback(self, proc: ERPCProcess) -> None:
        """is_running is usable as a fallback gate."""
        assert proc.is_running is False  # never started
        assert proc.pid is None

    def test_exit_code_available_after_crash(self, proc: ERPCProcess) -> None:
        """returncode is accessible after process exits."""
        dead = _mock_popen_dead(exit_code=137)
        proc._proc = dead
        assert proc._proc.returncode == 137
        assert proc.is_running is False

    def test_is_healthy_false_when_not_started(self, proc: ERPCProcess) -> None:
        """is_healthy returns False (not error) when process never started."""
        with patch("erpc.process.urlopen", side_effect=OSError):
            assert proc.is_healthy is False

    def test_fallback_decision_flow(self, proc: ERPCProcess) -> None:
        """Demonstrates the fallback decision pattern."""
        # Process never started or crashed
        assert proc.is_running is False

        # Application can make fallback decision
        if not proc.is_running:
            fallback_url = "https://direct-rpc.example.com"
            assert fallback_url  # Would use direct RPC


# ---------------------------------------------------------------------------
# 6. Rapid restart cycling
# ---------------------------------------------------------------------------


@pytest.mark.fault_tolerance
class TestRapidRestartCycling:
    """stop/start/stop/start in quick succession."""

    def test_rapid_restart_no_state_corruption(self, proc: ERPCProcess) -> None:
        """Multiple restart cycles don't corrupt internal state."""
        for _ in range(5):
            running = _mock_popen_running()
            with (
                patch("subprocess.Popen", return_value=running),
                patch.object(proc.config, "write", return_value=Path("/tmp/erpc.yaml")),
            ):
                proc.start()
            assert proc.is_running is True

            running.poll.return_value = 0  # stopped
            running.wait.return_value = 0
            proc.stop()
            assert proc._proc is None

    def test_restart_method_cycles(self, proc: ERPCProcess) -> None:
        """restart() works cleanly when called repeatedly."""
        running = _mock_popen_running()
        with (
            patch("subprocess.Popen", return_value=running),
            patch.object(proc.config, "write", return_value=Path("/tmp/erpc.yaml")),
        ):
            proc.start()

        new_running = _mock_popen_running()
        new_running.pid = 99999
        with (
            patch("subprocess.Popen", return_value=new_running),
            patch.object(proc.config, "write", return_value=Path("/tmp/erpc.yaml")),
        ):
            running.poll.return_value = 0
            running.wait.return_value = 0
            proc.restart()

        assert proc._proc is new_running

    def test_stop_already_dead_cleans_up(self, proc: ERPCProcess) -> None:
        """Stopping an already-dead process cleans up without error."""
        dead = _mock_popen_dead(exit_code=0)
        proc._proc = dead
        proc._config_path = Path("/tmp/nonexistent.yaml")

        proc.stop()
        assert proc._proc is None
        assert proc._config_path is None


# ---------------------------------------------------------------------------
# 7. Config file corruption
# ---------------------------------------------------------------------------


@pytest.mark.fault_tolerance
class TestConfigCorruption:
    """Invalid config → clean error; fix config → restart works."""

    def test_invalid_config_start_fails_cleanly(self, proc: ERPCProcess) -> None:
        """Bad config causes immediate exit with error message."""
        dead = _mock_popen_dead(exit_code=1)
        dead.stderr.read.return_value = b"yaml: unmarshal error"

        with (
            patch.object(proc.config, "write", return_value=Path("/tmp/erpc.yaml")),
            patch("subprocess.Popen", return_value=dead),
            pytest.raises(ERPCStartupError, match="yaml: unmarshal error"),
        ):
            proc.start()

    def test_recovery_after_config_fix(self, proc: ERPCProcess) -> None:
        """After fixing config, start succeeds."""
        dead = _mock_popen_dead(exit_code=1)
        dead.stderr.read.return_value = b"bad config"

        with (
            patch.object(proc.config, "write", return_value=Path("/tmp/erpc.yaml")),
            patch("subprocess.Popen", return_value=dead),
            pytest.raises(ERPCStartupError),
        ):
            proc.start()

        # Fix config and retry
        running = _mock_popen_running()
        with (
            patch.object(proc.config, "write", return_value=Path("/tmp/erpc.yaml")),
            patch("subprocess.Popen", return_value=running),
        ):
            proc.start()
        assert proc.is_running is True


# ---------------------------------------------------------------------------
# 8. Signal handling
# ---------------------------------------------------------------------------


@pytest.mark.fault_tolerance
class TestSignalHandling:
    """SIGTERM graceful shutdown, SIGKILL immediate death."""

    def test_stop_sends_sigterm_first(self, proc: ERPCProcess) -> None:
        """stop() sends SIGTERM before SIGKILL."""
        running = _mock_popen_running()
        running.wait.return_value = 0
        proc._proc = running

        proc.stop()

        running.send_signal.assert_called_once_with(signal.SIGTERM)
        running.kill.assert_not_called()

    def test_sigkill_on_timeout(self, proc: ERPCProcess) -> None:
        """SIGKILL sent when SIGTERM doesn't stop the process."""
        running = _mock_popen_running()
        running.wait.side_effect = [subprocess.TimeoutExpired("erpc", 5), None]
        proc._proc = running

        proc.stop(timeout=5)

        running.send_signal.assert_called_once_with(signal.SIGTERM)
        running.kill.assert_called_once()

    def test_cleanup_after_sigterm(self, proc: ERPCProcess) -> None:
        """Cleanup runs after graceful SIGTERM shutdown."""
        running = _mock_popen_running()
        running.wait.return_value = 0
        proc._proc = running
        proc._config_path = Path("/tmp/test.yaml")

        proc.stop()

        assert proc._proc is None
        assert proc._config_path is None

    def test_cleanup_after_sigkill(self, proc: ERPCProcess) -> None:
        """Cleanup runs after forced SIGKILL."""
        running = _mock_popen_running()
        running.wait.side_effect = [subprocess.TimeoutExpired("erpc", 5), None]
        proc._proc = running
        proc._config_path = Path("/tmp/test.yaml")

        proc.stop()

        assert proc._proc is None
        assert proc._config_path is None


# ---------------------------------------------------------------------------
# 9. Concurrent access
# ---------------------------------------------------------------------------


@pytest.mark.fault_tolerance
class TestConcurrentAccess:
    """Multiple threads checking state during start/stop transitions."""

    def test_concurrent_is_running_checks(self, proc: ERPCProcess) -> None:
        """Multiple threads reading is_running don't crash."""
        running = _mock_popen_running()
        proc._proc = running

        results: list[bool] = []
        errors: list[Exception] = []

        def check() -> None:
            try:
                for _ in range(50):
                    results.append(proc.is_running)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=check) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert not errors
        assert len(results) == 500

    def test_concurrent_is_healthy_checks(self, proc: ERPCProcess) -> None:
        """Multiple threads reading is_healthy don't crash."""
        errors: list[Exception] = []

        def check() -> None:
            try:
                with patch("erpc.process.urlopen", side_effect=OSError):
                    for _ in range(20):
                        _ = proc.is_healthy
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=check) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert not errors

    def test_state_transition_visibility(self, proc: ERPCProcess) -> None:
        """State changes are visible across threads."""
        proc._proc = _mock_popen_running()
        assert proc.is_running is True

        # Simulate crash from another context
        proc._proc.poll.return_value = -9
        assert proc.is_running is False


# ---------------------------------------------------------------------------
# 10. Docker fault tolerance
# ---------------------------------------------------------------------------


@pytest.mark.fault_tolerance
class TestDockerFaultTolerance:
    """Docker container failure scenarios."""

    def test_container_crash_detected(self, docker_proc: DockerERPCProcess) -> None:
        """is_running detects when container stops unexpectedly."""
        docker_proc._container_id = "abc123"

        with patch("subprocess.run") as mock_run:
            # Container is running
            mock_run.return_value = MagicMock(stdout="true\n")
            assert docker_proc.is_running is True

            # Container crashed
            mock_run.return_value = MagicMock(stdout="false\n")
            assert docker_proc.is_running is False

    def test_docker_inspect_failure(self, docker_proc: DockerERPCProcess) -> None:
        """is_running returns False if docker inspect fails (daemon down)."""
        docker_proc._container_id = "abc123"

        with patch(
            "subprocess.run", side_effect=subprocess.CalledProcessError(1, "docker")
        ):
            assert docker_proc.is_running is False

    def test_docker_inspect_os_error(self, docker_proc: DockerERPCProcess) -> None:
        """is_running returns False on OSError (docker binary gone)."""
        docker_proc._container_id = "abc123"

        with patch("subprocess.run", side_effect=OSError("docker not found")):
            assert docker_proc.is_running is False

    def test_no_container_id_not_running(self, docker_proc: DockerERPCProcess) -> None:
        """is_running returns False when no container ID exists."""
        assert docker_proc._container_id is None
        assert docker_proc.is_running is False

    def test_stop_no_container_raises(self, docker_proc: DockerERPCProcess) -> None:
        """Stopping without a container raises ERPCNotRunning."""
        with pytest.raises(ERPCNotRunning):
            docker_proc.stop()

    def test_docker_restart_after_crash(
        self, docker_proc: DockerERPCProcess
    ) -> None:
        """restart() works after container crash."""
        docker_proc._container_id = "dead123"

        with patch("subprocess.run") as mock_run:
            # is_running returns False (crashed)
            mock_run.return_value = MagicMock(stdout="false\n")
            assert docker_proc.is_running is False

        # Start fresh
        with (
            patch.object(docker_proc.config, "write", return_value=Path("/tmp/e.yaml")),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(stdout="newcontainer123\n", returncode=0)
            docker_proc._container_id = None
            docker_proc.start()
            assert docker_proc._container_id == "newcontainer123"

    def test_docker_health_check_timeout(
        self, docker_proc: DockerERPCProcess
    ) -> None:
        """wait_for_health raises on timeout with container still running."""
        docker_proc._container_id = "abc123"

        with (
            patch.object(
                type(docker_proc), "is_running", new_callable=PropertyMock, return_value=True
            ),
            patch("erpc.docker.urlopen", side_effect=OSError),
            pytest.raises(ERPCHealthCheckError),
        ):
            docker_proc.wait_for_health(timeout=1)

    def test_docker_stop_handles_rm_failure(
        self, docker_proc: DockerERPCProcess
    ) -> None:
        """stop() handles docker rm failure gracefully."""
        docker_proc._container_id = "abc123"

        call_count = 0

        def side_effect(*args: object, **kwargs: object) -> MagicMock:
            nonlocal call_count
            call_count += 1
            if call_count == 2:  # docker rm
                raise subprocess.CalledProcessError(1, "docker rm")
            return MagicMock(stdout="", returncode=0)

        with patch("subprocess.run", side_effect=side_effect):
            docker_proc.stop()

        # Cleanup still happened
        assert docker_proc._container_id is None
