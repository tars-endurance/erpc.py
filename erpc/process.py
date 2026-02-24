"""eRPC process lifecycle manager.

Inspired by py-geth's BaseGethProcess pattern.
"""

from __future__ import annotations

import logging
import os
import shutil
import signal
import subprocess
import time
from pathlib import Path
from types import TracebackType
from typing import Optional
from urllib.error import URLError
from urllib.request import urlopen

from erpc.config import ERPCConfig
from erpc.exceptions import (
    ERPCHealthCheckError,
    ERPCNotFound,
    ERPCNotRunning,
    ERPCStartupError,
)

logger = logging.getLogger(__name__)

# Default binary name
ERPC_BINARY = "erpc"


def find_erpc_binary(binary_path: Optional[str] = None) -> str:
    """Locate the eRPC binary.

    Checks (in order):
    1. Explicit binary_path argument
    2. ERPC_BINARY environment variable
    3. Common install locations
    4. System PATH via shutil.which

    Raises:
        ERPCNotFound: If the binary cannot be located.
    """
    candidates = []

    if binary_path:
        candidates.append(binary_path)

    env_binary = os.environ.get("ERPC_BINARY")
    if env_binary:
        candidates.append(env_binary)

    # Common locations
    candidates.extend(
        [
            "/usr/local/bin/erpc",
            "/usr/local/bin/erpc-server",
            "/usr/bin/erpc",
        ]
    )

    for candidate in candidates:
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate

    # Fall back to PATH
    found = shutil.which(ERPC_BINARY) or shutil.which("erpc-server")
    if found:
        return found

    raise ERPCNotFound(
        "eRPC binary not found. Install it or set ERPC_BINARY env var. "
        "See: https://github.com/erpc/erpc"
    )


class ERPCProcess:
    """Manages an eRPC instance as a subprocess.

    Usage:
        # Context manager (recommended)
        with ERPCProcess(upstreams={1: ["https://..."]}) as erpc:
            url = erpc.endpoint_url(1)

        # Manual lifecycle
        erpc = ERPCProcess(config=my_config)
        erpc.start()
        erpc.wait_for_health()
        ...
        erpc.stop()
    """

    _proc: Optional[subprocess.Popen] = None
    _config_path: Optional[Path] = None

    def __init__(
        self,
        config: Optional[ERPCConfig] = None,
        upstreams: Optional[dict[int, list[str]]] = None,
        binary_path: Optional[str] = None,
        stdin: int = subprocess.DEVNULL,
        stdout: int = subprocess.PIPE,
        stderr: int = subprocess.PIPE,
    ):
        """Initialize ERPCProcess.

        Provide either a full ERPCConfig or just upstreams for quick setup.

        Args:
            config: Full eRPC configuration. Takes precedence over upstreams.
            upstreams: Quick setup — mapping of chain_id → endpoint URLs.
            binary_path: Path to eRPC binary (auto-detected if not set).
            stdin: Subprocess stdin file descriptor.
            stdout: Subprocess stdout file descriptor.
            stderr: Subprocess stderr file descriptor.
        """
        if config is not None:
            self.config = config
        elif upstreams is not None:
            self.config = ERPCConfig(upstreams=upstreams)
        else:
            raise ValueError("Provide either config or upstreams")

        self.binary = find_erpc_binary(binary_path)
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr

    @property
    def is_running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    @property
    def is_alive(self) -> bool:
        """Check if process is running AND healthy."""
        return self.is_running and self.is_healthy

    @property
    def is_healthy(self) -> bool:
        """Check eRPC health endpoint."""
        try:
            urlopen(self.config.health_url, timeout=2)
            return True
        except (URLError, OSError):
            return False

    @property
    def pid(self) -> Optional[int]:
        return self._proc.pid if self._proc else None

    @property
    def endpoint(self) -> str:
        """Base eRPC endpoint URL."""
        return f"http://{self.config.server_host}:{self.config.server_port}"

    def endpoint_url(self, chain_id: int) -> str:
        """Get the proxied endpoint URL for a specific chain."""
        return self.config.endpoint_url(chain_id)

    def start(self) -> None:
        """Start the eRPC process.

        Raises:
            ERPCStartupError: If the process fails to start or is already running.
        """
        if self.is_running:
            raise ERPCStartupError("eRPC is already running")

        # Write config to temp file
        self._config_path = self.config.write()
        command = [self.binary, str(self._config_path)]

        logger.info(f"Starting eRPC: {' '.join(command)}")
        try:
            self._proc = subprocess.Popen(
                command,
                stdin=self.stdin,
                stdout=self.stdout,
                stderr=self.stderr,
            )
        except OSError as e:
            raise ERPCStartupError(f"Failed to start eRPC: {e}") from e

        # Quick check — did it crash immediately?
        time.sleep(0.1)
        if self._proc.poll() is not None:
            stderr_output = ""
            if self._proc.stderr:
                stderr_output = self._proc.stderr.read().decode(errors="replace")
            raise ERPCStartupError(
                f"eRPC exited immediately (code {self._proc.returncode}): {stderr_output}"
            )

        logger.info(f"eRPC started (PID {self._proc.pid})")

    def stop(self, timeout: int = 5) -> None:
        """Stop the eRPC process gracefully.

        Sends SIGTERM, waits up to `timeout` seconds, then SIGKILL.

        Raises:
            ERPCNotRunning: If the process is not running.
        """
        if not self._proc:
            raise ERPCNotRunning("eRPC is not running")

        if self._proc.poll() is not None:
            logger.info("eRPC already stopped")
            self._cleanup()
            return

        logger.info(f"Stopping eRPC (PID {self._proc.pid})...")
        self._proc.send_signal(signal.SIGTERM)

        try:
            self._proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            logger.warning("eRPC did not stop gracefully, sending SIGKILL")
            self._proc.kill()
            self._proc.wait(timeout=5)

        logger.info("eRPC stopped")
        self._cleanup()

    def restart(self, timeout: int = 5) -> None:
        """Restart the eRPC process."""
        if self.is_running:
            self.stop(timeout=timeout)
        self.start()

    def wait_for_health(self, timeout: int = 30) -> None:
        """Wait for eRPC to become healthy.

        Args:
            timeout: Maximum seconds to wait.

        Raises:
            ERPCHealthCheckError: If health check times out.
            ERPCStartupError: If the process dies during startup.
        """
        logger.info(f"Waiting for eRPC health (timeout: {timeout}s)...")
        deadline = time.monotonic() + timeout

        while time.monotonic() < deadline:
            if not self.is_running:
                raise ERPCStartupError("eRPC process died during health check")

            if self.is_healthy:
                logger.info("eRPC is healthy")
                return

            time.sleep(0.5)

        raise ERPCHealthCheckError(
            f"eRPC did not become healthy within {timeout}s"
        )

    def _cleanup(self) -> None:
        """Clean up temporary config files."""
        if self._config_path and self._config_path.exists():
            try:
                self._config_path.unlink()
            except OSError:
                pass
        self._config_path = None
        self._proc = None

    def __enter__(self) -> ERPCProcess:
        self.start()
        self.wait_for_health()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self.is_running:
            self.stop()
