"""Async eRPC process lifecycle manager.

Async counterpart of :mod:`erpc.process` — all blocking operations use
``asyncio`` so they can be ``await``-ed without stalling the event loop.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import signal
from typing import TYPE_CHECKING

from erpc.config import ERPCConfig
from erpc.exceptions import (
    ERPCHealthCheckError,
    ERPCNotRunning,
    ERPCStartupError,
)
from erpc.process import find_erpc_binary

if TYPE_CHECKING:
    from pathlib import Path
    from types import TracebackType

logger = logging.getLogger(__name__)


class AsyncERPCProcess:
    """Async manager for an eRPC subprocess.

    Mirrors :class:`~erpc.process.ERPCProcess` but uses ``asyncio``
    subprocesses and non-blocking health checks.

    Examples:
        Async context manager (recommended)::

            async with AsyncERPCProcess(upstreams={1: ["https://..."]}) as erpc:
                url = erpc.endpoint_url(1)

        Manual lifecycle::

            erpc = AsyncERPCProcess(config=my_config)
            await erpc.start()
            await erpc.wait_for_health()
            ...
            await erpc.stop()

    """

    _proc: asyncio.subprocess.Process | None = None
    _config_path: Path | None = None

    def __init__(
        self,
        config: ERPCConfig | None = None,
        upstreams: dict[int, list[str]] | None = None,
        binary_path: str | None = None,
    ) -> None:
        """Initialize AsyncERPCProcess.

        Provide either a full ``ERPCConfig`` or just ``upstreams`` for quick setup.

        Args:
            config: Full eRPC configuration. Takes precedence over ``upstreams``.
            upstreams: Quick setup — mapping of chain_id to endpoint URLs.
            binary_path: Path to eRPC binary (auto-detected if not set).

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

    @property
    def is_running(self) -> bool:
        """Whether the eRPC subprocess is currently running."""
        return self._proc is not None and self._proc.returncode is None

    @property
    def pid(self) -> int | None:
        """PID of the running eRPC process, or ``None``."""
        return self._proc.pid if self._proc else None

    @property
    def endpoint(self) -> str:
        """Base eRPC endpoint URL."""
        return f"http://{self.config.server_host}:{self.config.server_port}"

    def endpoint_url(self, chain_id: int) -> str:
        """Get the proxied endpoint URL for a specific chain.

        Args:
            chain_id: EVM chain identifier.

        Returns:
            Full URL for the proxied RPC endpoint.

        """
        return self.config.endpoint_url(chain_id)

    async def is_healthy(self) -> bool:
        """Whether the eRPC health endpoint responds successfully."""
        try:
            _reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.config.server_host, self.config.server_port),
                timeout=2,
            )
            writer.close()
            await writer.wait_closed()
        except (OSError, asyncio.TimeoutError):
            return False
        else:
            return True

    async def start(self) -> None:
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
            self._proc = await asyncio.create_subprocess_exec(
                *command,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except OSError as e:
            raise ERPCStartupError(f"Failed to start eRPC: {e}") from e

        # Quick check — did it crash immediately?
        await asyncio.sleep(0.1)
        if self._proc.returncode is not None:
            stderr_output = ""
            if self._proc.stderr:
                data = await self._proc.stderr.read()
                stderr_output = data.decode(errors="replace")
            raise ERPCStartupError(
                f"eRPC exited immediately (code {self._proc.returncode}): {stderr_output}"
            )

        logger.info("eRPC started (PID %s)", self._proc.pid)

    async def stop(self, timeout: int = 5) -> None:
        """Stop the eRPC process gracefully.

        Sends ``SIGTERM``, waits up to ``timeout`` seconds, then ``SIGKILL``.

        Args:
            timeout: Seconds to wait for graceful shutdown.

        Raises:
            ERPCNotRunning: If the process is not running.

        """
        if not self._proc:
            raise ERPCNotRunning("eRPC is not running")

        if self._proc.returncode is not None:
            logger.info("eRPC already stopped")
            self._cleanup()
            return

        logger.info("Stopping eRPC (PID %s)...", self._proc.pid)
        self._proc.send_signal(signal.SIGTERM)

        try:
            await asyncio.wait_for(self._proc.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning("eRPC did not stop gracefully, sending SIGKILL")
            self._proc.kill()
            await asyncio.wait_for(self._proc.wait(), timeout=5)

        logger.info("eRPC stopped")
        self._cleanup()

    async def restart(self, timeout: int = 5) -> None:
        """Restart the eRPC process.

        Args:
            timeout: Seconds to wait for graceful shutdown before restart.

        """
        if self.is_running:
            await self.stop(timeout=timeout)
        await self.start()

    async def wait_for_health(self, timeout: int = 30) -> None:
        """Wait for eRPC to become healthy.

        Args:
            timeout: Maximum seconds to wait.

        Raises:
            ERPCHealthCheckError: If health check times out.
            ERPCStartupError: If the process dies during startup.

        """
        logger.info("Waiting for eRPC health (timeout: %ds)...", timeout)
        deadline = asyncio.get_event_loop().time() + timeout

        while asyncio.get_event_loop().time() < deadline:
            if not self.is_running:
                raise ERPCStartupError("eRPC process died during health check")

            if await self.is_healthy():
                logger.info("eRPC is healthy")
                return

            await asyncio.sleep(0.5)

        raise ERPCHealthCheckError(f"eRPC did not become healthy within {timeout}s")

    def _cleanup(self) -> None:
        """Clean up temporary config files."""
        if self._config_path and self._config_path.exists():
            with contextlib.suppress(OSError):
                self._config_path.unlink()
        self._config_path = None
        self._proc = None

    async def __aenter__(self) -> AsyncERPCProcess:
        """Start eRPC and wait for health on context entry."""
        await self.start()
        await self.wait_for_health()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Stop eRPC on context exit."""
        if self.is_running:
            await self.stop()
