"""eRPC process lifecycle manager.

Inspired by `py-geth <https://github.com/ethereum/py-geth>`_'s BaseGethProcess pattern.
"""

from __future__ import annotations

import contextlib
import logging
import os
import shutil
import signal
import subprocess
import time
from typing import TYPE_CHECKING
from urllib.error import URLError
from urllib.request import urlopen

from erpc.config import ERPCConfig
from erpc.exceptions import (
    ERPCHealthCheckError,
    ERPCNotFound,
    ERPCNotRunning,
    ERPCStartupError,
)

if TYPE_CHECKING:
    from pathlib import Path
    from types import TracebackType

    from erpc.client import ERPCClient

logger = logging.getLogger(__name__)

ERPC_BINARY = "erpc"
"""Default binary name to search for on PATH."""


def find_erpc_binary(binary_path: str | None = None) -> str:
    """Locate the eRPC binary.

    Checks (in order):

    1. Explicit ``binary_path`` argument.
    2. ``ERPC_BINARY`` environment variable.
    3. Common install locations (``/usr/local/bin``, ``/usr/bin``).
    4. System ``PATH`` via :func:`shutil.which`.

    Args:
        binary_path: Explicit path to the eRPC binary.

    Returns:
        Absolute path to the eRPC binary.

    Raises:
        ERPCNotFound: If the binary cannot be located anywhere.

    """
    candidates: list[str] = []

    if binary_path:
        candidates.append(binary_path)

    env_binary = os.environ.get("ERPC_BINARY")
    if env_binary:
        candidates.append(env_binary)

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

    found = shutil.which(ERPC_BINARY) or shutil.which("erpc-server")
    if found:
        return found

    # Auto-install if not found
    try:
        import logging

        from erpc.install import install_erpc

        logging.getLogger("erpc.process").info(
            "eRPC binary not found — downloading automatically..."
        )
        path = install_erpc()
        return str(path)
    except Exception:
        pass  # Fall through to ERPCNotFound

    raise ERPCNotFound(
        "eRPC binary not found. Install it or set ERPC_BINARY env var. "
        "See: https://github.com/erpc/erpc"
    )


class ERPCProcess:
    """Manages an eRPC instance as a subprocess.

    Supports both context-manager and manual lifecycle patterns.

    Examples:
        Context manager (recommended)::

            with ERPCProcess(upstreams={1: ["https://..."]}) as erpc:
                url = erpc.endpoint_url(1)

        Manual lifecycle::

            erpc = ERPCProcess(config=my_config)
            erpc.start()
            erpc.wait_for_health()
            ...
            erpc.stop()

    """

    _proc: subprocess.Popen[bytes] | None = None
    _config_path: Path | None = None
    _client: ERPCClient | None = None

    def __init__(
        self,
        config: ERPCConfig | None = None,
        upstreams: dict[int, list[str]] | None = None,
        binary_path: str | None = None,
        stdin: int = subprocess.DEVNULL,
        stdout: int = subprocess.PIPE,
        stderr: int = subprocess.PIPE,
    ) -> None:
        """Initialize ERPCProcess.

        Provide either a full ``ERPCConfig`` or just ``upstreams`` for quick setup.

        Args:
            config: Full eRPC configuration. Takes precedence over ``upstreams``.
            upstreams: Quick setup — mapping of chain_id to endpoint URLs.
            binary_path: Path to eRPC binary (auto-detected if not set).
            stdin: Subprocess stdin file descriptor.
            stdout: Subprocess stdout file descriptor.
            stderr: Subprocess stderr file descriptor.

        Raises:
            ValueError: If neither ``config`` nor ``upstreams`` is provided.
            ERPCNotFound: If the eRPC binary cannot be located.

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
        """Whether the eRPC subprocess is currently running."""
        return self._proc is not None and self._proc.poll() is None

    @property
    def is_alive(self) -> bool:
        """Whether the process is running AND the health endpoint responds."""
        return self.is_running and self.is_healthy

    @property
    def is_healthy(self) -> bool:
        """Whether the eRPC health endpoint responds successfully."""
        try:
            urlopen(self.config.health_url, timeout=2)
        except (URLError, OSError):
            return False
        else:
            return True

    @property
    def pid(self) -> int | None:
        """PID of the running eRPC process, or ``None``."""
        return self._proc.pid if self._proc else None

    @property
    def endpoint(self) -> str:
        """Base eRPC endpoint URL."""
        return f"http://{self.config.server_host}:{self.config.server_port}"

    @property
    def client(self) -> ERPCClient:
        """Return an :class:`~erpc.client.ERPCClient` pointed at this instance.

        The client is lazily created and cached for the lifetime of the process.

        Returns:
            An HTTP client configured with this instance's server and metrics URLs.

        """
        if self._client is None:
            from erpc.client import ERPCClient

            self._client = ERPCClient(
                base_url=self.endpoint,
                metrics_port=self.config.metrics_port,
            )
        return self._client

    def endpoint_url(self, chain_id: int) -> str:
        """Get the proxied endpoint URL for a specific chain.

        Args:
            chain_id: EVM chain identifier.

        Returns:
            Full URL for the proxied RPC endpoint.

        """
        return self.config.endpoint_url(chain_id)

    def start(self) -> None:
        """Start the eRPC process.

        Raises:
            ERPCStartupError: If the process fails to start or is already running.

        """
        if self.is_running:
            raise ERPCStartupError("eRPC is already running")

        self._config_path = self.config.write()
        command = [self.binary, str(self._config_path)]

        logger.info("Starting eRPC: %s", " ".join(command))
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

        logger.info("eRPC started (PID %s)", self._proc.pid)

    def stop(self, timeout: int = 5) -> None:
        """Stop the eRPC process gracefully.

        Sends ``SIGTERM``, waits up to ``timeout`` seconds, then ``SIGKILL``.

        Args:
            timeout: Seconds to wait for graceful shutdown.

        Raises:
            ERPCNotRunning: If the process is not running.

        """
        if not self._proc:
            raise ERPCNotRunning("eRPC is not running")

        if self._proc.poll() is not None:
            logger.info("eRPC already stopped")
            self._cleanup()
            return

        logger.info("Stopping eRPC (PID %s)...", self._proc.pid)
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
        """Restart the eRPC process.

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
            ERPCHealthCheckError: If health check times out.
            ERPCStartupError: If the process dies during startup.

        """
        logger.info("Waiting for eRPC health (timeout: %ds)...", timeout)
        deadline = time.monotonic() + timeout

        while time.monotonic() < deadline:
            if not self.is_running:
                raise ERPCStartupError("eRPC process died during health check")

            if self.is_healthy:
                logger.info("eRPC is healthy")
                return

            time.sleep(0.5)

        raise ERPCHealthCheckError(f"eRPC did not become healthy within {timeout}s")

    def check_upstream_health(self) -> dict[int, dict[str, bool]]:
        """Check the health status of upstream endpoints per chain.

        Scrapes the Prometheus metrics endpoint to determine which upstream
        endpoints are healthy or unhealthy for each chain.

        Returns:
            Mapping of chain_id to upstream health status. Each chain maps to
            a dict of upstream_id -> is_healthy boolean.

        Raises:
            ERPCNotRunning: If the eRPC process is not running.
            ERPCHealthCheckError: If metrics cannot be fetched or parsed.

        Examples:
            >>> erpc.check_upstream_health()
            {
                1: {"upstream_1": True, "upstream_2": False},
                137: {"upstream_1": True}
            }

        """
        if not self.is_running:
            raise ERPCNotRunning("Cannot check upstream health: eRPC is not running")

        try:
            metrics = self.client.metrics()
        except ERPCHealthCheckError as exc:
            raise ERPCHealthCheckError(f"Failed to fetch metrics for health check: {exc}") from exc

        return self._parse_upstream_health_metrics(metrics)

    def _parse_upstream_health_metrics(
        self, metrics: dict[str, float]
    ) -> dict[int, dict[str, bool]]:
        """Parse Prometheus metrics to extract upstream health status.

        Args:
            metrics: Parsed Prometheus metrics from the eRPC instance.

        Returns:
            Mapping of chain_id to upstream health status.

        """
        import re

        health_status: dict[int, dict[str, bool]] = {}

        # Look for metrics that indicate upstream health
        # Common patterns: erpc_upstream_health{chain_id="1",upstream="upstream_1"} 1.0
        health_pattern = re.compile(
            r"erpc_upstream_(?:health|status|available)"
            r'\{.*?chain_id="(\d+)".*?upstream="([^"]+)".*?\}'
        )

        # Also check for request total/success/failure rates
        total_pattern = re.compile(
            r"erpc_requests_total"
            r'\{.*?chain_id="(\d+)".*?upstream="([^"]+)".*?\}'
        )

        success_pattern = re.compile(
            r"erpc_requests_success"
            r'\{.*?chain_id="(\d+)".*?upstream="([^"]+)".*?\}'
        )

        error_pattern = re.compile(
            r"erpc_requests_(?:failed|error)"
            r'\{.*?chain_id="(\d+)".*?upstream="([^"]+)".*?\}'
        )

        # Process health metrics directly
        for metric_name, value in metrics.items():
            match = health_pattern.search(metric_name)
            if match:
                chain_id = int(match.group(1))
                upstream = match.group(2)
                is_healthy = value > 0.0

                if chain_id not in health_status:
                    health_status[chain_id] = {}
                health_status[chain_id][upstream] = is_healthy

        # If no direct health metrics, infer from request patterns
        if not health_status:
            total_counts: dict[tuple[int, str], float] = {}
            success_counts: dict[tuple[int, str], float] = {}
            error_counts: dict[tuple[int, str], float] = {}

            for metric_name, value in metrics.items():
                total_match = total_pattern.search(metric_name)
                if total_match:
                    chain_id = int(total_match.group(1))
                    upstream = total_match.group(2)
                    total_counts[(chain_id, upstream)] = value

                success_match = success_pattern.search(metric_name)
                if success_match:
                    chain_id = int(success_match.group(1))
                    upstream = success_match.group(2)
                    success_counts[(chain_id, upstream)] = value

                error_match = error_pattern.search(metric_name)
                if error_match:
                    chain_id = int(error_match.group(1))
                    upstream = error_match.group(2)
                    error_counts[(chain_id, upstream)] = value

            # Calculate health based on success/error ratios
            # Derive successes from total - errors when only total is available
            all_upstreams = (
                set(total_counts.keys()) | set(success_counts.keys()) | set(error_counts.keys())
            )
            for chain_id, upstream in all_upstreams:
                key = (chain_id, upstream)
                total = total_counts.get(key, 0.0)
                errors = error_counts.get(key, 0.0)

                if key in success_counts:
                    successes = success_counts[key]
                elif total > 0:
                    successes = total - errors
                else:
                    successes = 0.0

                denominator = total if total > 0 else (successes + errors)

                # Consider healthy if success rate > 50% and has some activity
                is_healthy = denominator > 0 and (successes / denominator) > 0.5

                if chain_id not in health_status:
                    health_status[chain_id] = {}
                health_status[chain_id][upstream] = is_healthy

        return health_status

    def _cleanup(self) -> None:
        """Clean up temporary config files."""
        if self._config_path and self._config_path.exists():
            with contextlib.suppress(OSError):
                self._config_path.unlink()
        self._config_path = None
        self._proc = None

    def __enter__(self) -> ERPCProcess:
        """Start eRPC and wait for health on context entry."""
        self.start()
        self.wait_for_health()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Stop eRPC on context exit."""
        if self.is_running:
            self.stop()
