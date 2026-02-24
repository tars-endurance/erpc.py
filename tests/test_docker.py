"""Tests for Docker-based eRPC process management."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from erpc.config import ERPCConfig
from erpc.docker import DockerERPCProcess, find_docker_binary
from erpc.exceptions import ERPCError, ERPCHealthCheckError, ERPCNotRunning


@pytest.fixture()
def config() -> ERPCConfig:
    """Minimal eRPC config for testing."""
    return ERPCConfig(upstreams={1: ["https://eth.llamarpc.com"]})


@pytest.fixture()
def docker_proc(config: ERPCConfig) -> DockerERPCProcess:
    """DockerERPCProcess with defaults."""
    with patch("erpc.docker.find_docker_binary", return_value="/usr/bin/docker"):
        return DockerERPCProcess(config=config)


class TestConstruction:
    """Tests for DockerERPCProcess construction."""

    def test_defaults(self, config: ERPCConfig) -> None:
        """Construction with default image, port, metrics port."""
        with patch("erpc.docker.find_docker_binary", return_value="/usr/bin/docker"):
            proc = DockerERPCProcess(config=config)

        assert proc.image == "ghcr.io/erpc/erpc:latest"
        assert proc.port == 4000
        assert proc.metrics_port == 4001
        assert proc.name is None
        assert proc.container_id is None

    def test_custom_image_and_ports(self, config: ERPCConfig) -> None:
        """Construction with custom image, ports, and container name."""
        with patch("erpc.docker.find_docker_binary", return_value="/usr/bin/docker"):
            proc = DockerERPCProcess(
                config=config,
                image="erpc/erpc:v1.0",
                port=5000,
                metrics_port=5001,
                name="my-erpc",
            )

        assert proc.image == "erpc/erpc:v1.0"
        assert proc.port == 5000
        assert proc.metrics_port == 5001
        assert proc.name == "my-erpc"

    def test_docker_not_installed_raises(self, config: ERPCConfig) -> None:
        """ERPCError raised when docker binary is not found."""
        with (
            patch("erpc.docker.find_docker_binary", side_effect=ERPCError("docker not found")),
            pytest.raises(ERPCError, match="docker not found"),
        ):
            DockerERPCProcess(config=config)


class TestFindDockerBinary:
    """Tests for find_docker_binary helper."""

    def test_found_via_which(self) -> None:
        """Returns path when shutil.which finds docker."""
        with patch("shutil.which", return_value="/usr/bin/docker"):
            assert find_docker_binary() == "/usr/bin/docker"

    def test_not_found_raises(self) -> None:
        """ERPCError when docker is not on PATH."""
        with patch("shutil.which", return_value=None), pytest.raises(ERPCError, match="docker"):
            find_docker_binary()


class TestStart:
    """Tests for starting the Docker container."""

    def test_start_runs_docker_with_correct_args(self, docker_proc: DockerERPCProcess) -> None:
        """start() calls docker run with port mappings and config volume."""
        mock_result = MagicMock()
        mock_result.stdout = "abc123container\n"
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            docker_proc.start()

        # Should have called docker run
        run_call = mock_run.call_args_list[-1]
        cmd = run_call[0][0]
        assert cmd[0] == "/usr/bin/docker"
        assert "run" in cmd
        assert "-d" in cmd
        assert docker_proc.container_id == "abc123container"

    def test_start_mounts_config_as_volume(self, docker_proc: DockerERPCProcess) -> None:
        """Config file is mounted into the container."""
        mock_result = MagicMock()
        mock_result.stdout = "abc123\n"
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            docker_proc.start()

        cmd = mock_run.call_args_list[-1][0][0]
        cmd_str = " ".join(cmd)
        assert "-v" in cmd or "--volume" in cmd_str

    def test_start_with_container_name(self, config: ERPCConfig) -> None:
        """Container name is passed via --name flag."""
        with patch("erpc.docker.find_docker_binary", return_value="/usr/bin/docker"):
            proc = DockerERPCProcess(config=config, name="test-erpc")

        mock_result = MagicMock()
        mock_result.stdout = "abc123\n"
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            proc.start()

        cmd = mock_run.call_args_list[-1][0][0]
        assert "--name" in cmd
        name_idx = cmd.index("--name")
        assert cmd[name_idx + 1] == "test-erpc"

    def test_start_port_mappings(self, docker_proc: DockerERPCProcess) -> None:
        """Port mappings for server and metrics are set."""
        mock_result = MagicMock()
        mock_result.stdout = "abc123\n"
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            docker_proc.start()

        cmd = mock_run.call_args_list[-1][0][0]
        cmd_str = " ".join(cmd)
        assert "4000:4000" in cmd_str
        assert "4001:4001" in cmd_str

    def test_start_already_running_raises(self, docker_proc: DockerERPCProcess) -> None:
        """ERPCError when start() called on already-running container."""
        docker_proc._container_id = "abc123"

        is_running_prop = property(lambda self: True)
        with (
            patch.object(type(docker_proc), "is_running", new_callable=lambda: is_running_prop),
            pytest.raises(ERPCError, match="already running"),
        ):
            docker_proc.start()


class TestStop:
    """Tests for stopping the Docker container."""

    def test_stop_calls_docker_stop_and_rm(self, docker_proc: DockerERPCProcess) -> None:
        """stop() calls docker stop then docker rm."""
        docker_proc._container_id = "abc123"

        with patch("subprocess.run") as mock_run:
            docker_proc.stop()

        calls = mock_run.call_args_list
        stop_cmd = calls[0][0][0]
        rm_cmd = calls[1][0][0]
        assert "stop" in stop_cmd
        assert "abc123" in stop_cmd
        assert "rm" in rm_cmd
        assert "abc123" in rm_cmd
        assert docker_proc.container_id is None

    def test_stop_with_custom_timeout(self, docker_proc: DockerERPCProcess) -> None:
        """stop() passes timeout to docker stop."""
        docker_proc._container_id = "abc123"

        with patch("subprocess.run") as mock_run:
            docker_proc.stop(timeout=20)

        stop_cmd = mock_run.call_args_list[0][0][0]
        assert "--time" in stop_cmd or "-t" in stop_cmd

    def test_stop_not_running_raises(self, docker_proc: DockerERPCProcess) -> None:
        """ERPCNotRunning when no container to stop."""
        with pytest.raises(ERPCNotRunning):
            docker_proc.stop()


class TestLogs:
    """Tests for fetching container logs."""

    def test_logs_calls_docker_logs(self, docker_proc: DockerERPCProcess) -> None:
        """logs() returns stdout from docker logs command."""
        docker_proc._container_id = "abc123"

        mock_result = MagicMock()
        mock_result.stdout = "line1\nline2\n"

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            result = docker_proc.logs(tail=50)

        cmd = mock_run.call_args[0][0]
        assert "logs" in cmd
        assert "--tail" in cmd
        assert "50" in cmd
        assert result == "line1\nline2\n"

    def test_logs_not_running_raises(self, docker_proc: DockerERPCProcess) -> None:
        """ERPCNotRunning when calling logs with no container."""
        with pytest.raises(ERPCNotRunning):
            docker_proc.logs()


class TestIsRunning:
    """Tests for is_running property."""

    def test_is_running_true(self, docker_proc: DockerERPCProcess) -> None:
        """is_running returns True when docker inspect shows running."""
        docker_proc._container_id = "abc123"

        mock_result = MagicMock()
        mock_result.stdout = "true\n"
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result):
            assert docker_proc.is_running is True

    def test_is_running_false_no_container(self, docker_proc: DockerERPCProcess) -> None:
        """is_running returns False when no container_id."""
        assert docker_proc.is_running is False

    def test_is_running_false_inspect_fails(self, docker_proc: DockerERPCProcess) -> None:
        """is_running returns False when docker inspect fails."""
        docker_proc._container_id = "abc123"

        with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "docker")):
            assert docker_proc.is_running is False


class TestHealthCheck:
    """Tests for health checking."""

    def test_is_healthy_true(self, docker_proc: DockerERPCProcess) -> None:
        """is_healthy returns True when health endpoint responds."""
        with patch("erpc.docker.urlopen"):
            assert docker_proc.is_healthy is True

    def test_is_healthy_false(self, docker_proc: DockerERPCProcess) -> None:
        """is_healthy returns False when health endpoint fails."""
        from urllib.error import URLError

        with patch("erpc.docker.urlopen", side_effect=URLError("connection refused")):
            assert docker_proc.is_healthy is False

    def test_wait_for_health_timeout(self, docker_proc: DockerERPCProcess) -> None:
        """wait_for_health raises ERPCHealthCheckError on timeout."""
        docker_proc._container_id = "abc123"

        mock_result = MagicMock()
        mock_result.stdout = "true\n"
        mock_result.returncode = 0

        from urllib.error import URLError

        with (
            patch("subprocess.run", return_value=mock_result),
            patch("erpc.docker.urlopen", side_effect=URLError("refused")),
            patch("time.sleep"),
            pytest.raises(ERPCHealthCheckError),
        ):
            docker_proc.wait_for_health(timeout=1)


class TestRestart:
    """Tests for restart."""

    def test_restart_stops_then_starts(self, docker_proc: DockerERPCProcess) -> None:
        """restart() calls stop() then start()."""
        with (
            patch.object(docker_proc, "stop") as mock_stop,
            patch.object(docker_proc, "start") as mock_start,
            patch.object(
                type(docker_proc), "is_running", new_callable=lambda: property(lambda s: True)
            ),
        ):
            docker_proc.restart()

        mock_stop.assert_called_once()
        mock_start.assert_called_once()


class TestContextManager:
    """Tests for context manager lifecycle."""

    def test_context_manager_starts_and_stops(self, docker_proc: DockerERPCProcess) -> None:
        """Context manager calls start, wait_for_health, and stop."""
        is_running_prop = property(lambda self: True)
        with (
            patch.object(docker_proc, "start") as mock_start,
            patch.object(docker_proc, "wait_for_health") as mock_health,
            patch.object(docker_proc, "stop") as mock_stop,
            patch.object(type(docker_proc), "is_running", new_callable=lambda: is_running_prop),
            docker_proc as proc,
        ):
            assert proc is docker_proc

        mock_start.assert_called_once()
        mock_health.assert_called_once()
        mock_stop.assert_called_once()
