"""Docker-based eRPC process lifecycle manager.

Manages eRPC as a Docker container instead of a local binary, using the
``docker`` CLI via subprocess calls to keep dependencies light.

Examples:
    Context manager (recommended)::

        config = ERPCConfig(upstreams={1: ["https://eth.llamarpc.com"]})
        with DockerERPCProcess(config=config) as erpc:
            url = erpc.endpoint_url(1)

    Manual lifecycle::

        proc = DockerERPCProcess(config=config, name="my-erpc")
        proc.start()
        proc.wait_for_health()
        ...
        proc.stop()

"""

from __future__ import annotations

import logging
import shutil
import subprocess
import time
from typing import TYPE_CHECKING
from urllib.error import URLError
from urllib.request import urlopen

from erpc.config import ERPCConfig  # noqa: TC001 — used at runtime in __init__ signature
from erpc.exceptions import (
    ERPCError,
    ERPCHealthCheckError,
    ERPCNotRunning,
)

if TYPE_CHECKING:
    from pathlib import Path
    from types import TracebackType

logger = logging.getLogger(__name__)

_DEFAULT_IMAGE = "ghcr.io/erpc/erpc:latest"
"""Default Docker image for eRPC."""

_CONTAINER_CONFIG_PATH = "/etc/erpc/erpc.yaml"
"""Path where the config file is mounted inside the container."""


def find_docker_binary() -> str:
    """Locate the ``docker`` CLI binary on PATH.

    Returns:
        Absolute path to the docker binary.

    Raises:
        ERPCError: If docker is not installed or not on PATH.

    """
    found = shutil.which("docker")
    if found:
        return found
    raise ERPCError(
        "docker CLI not found on PATH. Install Docker to use DockerERPCProcess. "
        "See: https://docs.docker.com/get-docker/"
    )


class DockerERPCProcess:
    """Manages an eRPC instance as a Docker container.

    Uses the ``docker`` CLI via :mod:`subprocess` — no Python Docker SDK required.

    Args:
        config: eRPC configuration to mount into the container.
        image: Docker image to use.
        port: Host port to map to the eRPC server port (container port 4000).
        metrics_port: Host port to map to the metrics port (container port 4001).
        name: Optional container name for easier identification.

    Raises:
        ERPCError: If the ``docker`` binary is not found.

    Examples:
        >>> config = ERPCConfig(upstreams={1: ["https://eth.llamarpc.com"]})
        >>> proc = DockerERPCProcess(config=config, name="my-erpc")
        >>> proc.image
        'ghcr.io/erpc/erpc:latest'

    """

    _container_id: str | None = None
    _config_path: Path | None = None

    def __init__(
        self,
        config: ERPCConfig,
        image: str = _DEFAULT_IMAGE,
        port: int = 4000,
        metrics_port: int = 4001,
        name: str | None = None,
    ) -> None:
        """Initialize DockerERPCProcess.

        Args:
            config: eRPC configuration to mount into the container.
            image: Docker image to use.
            port: Host port to map to the eRPC server port.
            metrics_port: Host port to map to the metrics port.
            name: Optional container name.

        Raises:
            ERPCError: If the ``docker`` binary is not found.

        """
        self._docker = find_docker_binary()
        self.config = config
        self.image = image
        self.port = port
        self.metrics_port = metrics_port
        self.name = name

    @property
    def container_id(self) -> str | None:
        """ID of the running Docker container, or ``None`` if not started.

        Returns:
            Container ID string or ``None``.

        """
        return self._container_id

    @property
    def is_running(self) -> bool:
        """Whether the Docker container is currently running.

        Checks container status via ``docker inspect``.

        Returns:
            ``True`` if the container is running, ``False`` otherwise.

        """
        if not self._container_id:
            return False
        try:
            result = subprocess.run(
                [
                    self._docker,
                    "inspect",
                    "--format",
                    "{{.State.Running}}",
                    self._container_id,
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip().lower() == "true"
        except (subprocess.CalledProcessError, OSError):
            return False

    @property
    def is_healthy(self) -> bool:
        """Whether the eRPC health endpoint responds successfully.

        Returns:
            ``True`` if the health endpoint responds with HTTP 2xx.

        """
        try:
            urlopen(self.config.health_url, timeout=2)
        except (URLError, OSError):
            return False
        else:
            return True

    @property
    def endpoint(self) -> str:
        """Base eRPC endpoint URL.

        Returns:
            HTTP URL for the eRPC server.

        """
        return f"http://{self.config.server_host}:{self.port}"

    def endpoint_url(self, chain_id: int) -> str:
        """Get the proxied endpoint URL for a specific chain.

        Args:
            chain_id: EVM chain identifier.

        Returns:
            Full URL for the proxied RPC endpoint.

        """
        return (
            f"http://{self.config.server_host}:{self.port}/{self.config.project_id}/evm/{chain_id}"
        )

    def start(self) -> None:
        """Start the eRPC Docker container.

        Pulls the image if needed, writes the config to a temp file, and
        runs the container with the config mounted as a volume.

        Raises:
            ERPCError: If the container is already running or fails to start.

        """
        if self.is_running:
            raise ERPCError("eRPC container is already running")

        # Write config to temp file for volume mount
        self._config_path = self.config.write()

        cmd = [
            self._docker,
            "run",
            "-d",
            "-p",
            f"{self.port}:4000",
            "-p",
            f"{self.metrics_port}:4001",
            "-v",
            f"{self._config_path}:{_CONTAINER_CONFIG_PATH}:ro",
        ]

        if self.name:
            cmd.extend(["--name", self.name])

        cmd.append(self.image)

        logger.info("Starting eRPC container: %s", " ".join(cmd))
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )
            self._container_id = result.stdout.strip()
        except subprocess.CalledProcessError as e:
            raise ERPCError(f"Failed to start eRPC container: {e.stderr}") from e

        logger.info("eRPC container started (ID: %s)", self._container_id)

    def stop(self, timeout: int = 10) -> None:
        """Stop and remove the eRPC Docker container.

        Args:
            timeout: Seconds to wait for graceful shutdown before force-killing.

        Raises:
            ERPCNotRunning: If no container is running.

        """
        if not self._container_id:
            raise ERPCNotRunning("eRPC container is not running")

        logger.info("Stopping eRPC container %s...", self._container_id)
        try:
            subprocess.run(
                [self._docker, "stop", "--time", str(timeout), self._container_id],
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError:
            logger.warning("docker stop failed for %s", self._container_id)

        try:
            subprocess.run(
                [self._docker, "rm", "-f", self._container_id],
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError:
            logger.warning("docker rm failed for %s", self._container_id)

        logger.info("eRPC container stopped and removed")
        self._cleanup()

    def restart(self, timeout: int = 10) -> None:
        """Restart the eRPC Docker container.

        Args:
            timeout: Seconds to wait for graceful shutdown before restart.

        """
        if self.is_running:
            self.stop(timeout=timeout)
        self.start()

    def wait_for_health(self, timeout: int = 30) -> None:
        """Wait for eRPC to become healthy.

        Args:
            timeout: Maximum seconds to wait.

        Raises:
            ERPCHealthCheckError: If the health check times out.
            ERPCError: If the container stops during the health check.

        """
        logger.info("Waiting for eRPC health (timeout: %ds)...", timeout)
        deadline = time.monotonic() + timeout

        while time.monotonic() < deadline:
            if self._container_id and not self.is_running:
                raise ERPCError("eRPC container stopped during health check")

            if self.is_healthy:
                logger.info("eRPC is healthy")
                return

            time.sleep(0.5)

        raise ERPCHealthCheckError(f"eRPC did not become healthy within {timeout}s")

    def logs(self, tail: int = 100) -> str:
        """Fetch recent container logs.

        Args:
            tail: Number of recent log lines to retrieve.

        Returns:
            Container log output as a string.

        Raises:
            ERPCNotRunning: If no container exists to fetch logs from.

        """
        if not self._container_id:
            raise ERPCNotRunning("eRPC container is not running")

        result = subprocess.run(
            [self._docker, "logs", "--tail", str(tail), self._container_id],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout

    def _cleanup(self) -> None:
        """Clean up temporary config files and reset state."""
        if self._config_path and self._config_path.exists():
            import contextlib

            with contextlib.suppress(OSError):
                self._config_path.unlink()
        self._config_path = None
        self._container_id = None

    def __enter__(self) -> DockerERPCProcess:
        """Start eRPC container and wait for health on context entry."""
        self.start()
        self.wait_for_health()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Stop eRPC container on context exit."""
        if self.is_running:
            self.stop()
