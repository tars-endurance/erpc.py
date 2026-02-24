r"""HTTP client for eRPC runtime health and metrics endpoints.

Provides a lightweight client to query eRPC's health endpoint (on the server
port) and Prometheus metrics endpoint (on the metrics port).

Examples:
    Quick health check::

        >>> client = ERPCClient("http://localhost:4000")
        >>> client.is_healthy
        True
        >>> status = client.health()
        >>> status.version
        '0.0.49'

    Fetch Prometheus metrics::

        >>> metrics = client.metrics()
        >>> metrics["erpc_requests_total{method=\"eth_call\"}"]
        42.0

"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import urlopen

from erpc.exceptions import ERPCHealthCheckError

_METRIC_LINE_RE = re.compile(r"^([a-zA-Z_:][a-zA-Z0-9_:{}\",=]*)\s+([\d.eE+-]+)$")
"""Regex matching a Prometheus exposition line: ``metric_name{labels} value``."""


@dataclass(frozen=True)
class HealthStatus:
    """Structured result from an eRPC health check.

    Attributes:
        status: Health status string (e.g. ``"ok"``).
        uptime: Process uptime in seconds.
        version: eRPC version string.

    """

    status: str
    uptime: float
    version: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HealthStatus:
        """Create a ``HealthStatus`` from a JSON-decoded dictionary.

        Missing fields are filled with sensible defaults so partial
        responses don't crash the client.

        Args:
            data: Decoded JSON body from the health endpoint.

        Returns:
            Populated ``HealthStatus`` instance.

        """
        return cls(
            status=str(data.get("status", "unknown")),
            uptime=float(data.get("uptime", 0.0)),
            version=str(data.get("version", "unknown")),
        )


class ERPCClient:
    """Lightweight HTTP client for eRPC runtime endpoints.

    Uses only :mod:`urllib` from the standard library — no extra dependencies.

    Args:
        base_url: Base URL of the eRPC server (e.g. ``http://localhost:4000``).
        metrics_port: Port for the Prometheus metrics endpoint. Defaults to ``4001``.
        timeout: HTTP request timeout in seconds. Defaults to ``5``.

    Examples:
        >>> client = ERPCClient("http://localhost:4000")
        >>> client.is_healthy
        True

    """

    def __init__(
        self,
        base_url: str,
        metrics_port: int = 4001,
        timeout: int = 5,
    ) -> None:
        """Initialize the client.

        Args:
            base_url: Base URL of the eRPC server (e.g. ``http://localhost:4000``).
            metrics_port: Port for the Prometheus metrics endpoint.
            timeout: HTTP request timeout in seconds.

        """
        self.base_url: str = base_url.rstrip("/")
        self.metrics_port: int = metrics_port
        self.timeout: int = timeout

    def health(self) -> HealthStatus:
        """Fetch structured health status from eRPC.

        Queries the server's root endpoint and parses the JSON response
        into a :class:`HealthStatus` dataclass.

        Returns:
            Parsed health status.

        Raises:
            ERPCHealthCheckError: On connection failure, timeout, or unparseable response.

        """
        url = self.base_url + "/"
        try:
            with urlopen(url, timeout=self.timeout) as resp:
                body = resp.read()
        except (URLError, OSError, TimeoutError) as exc:
            raise ERPCHealthCheckError(f"Health check failed for {url}: {exc}") from exc

        try:
            data: dict[str, Any] = json.loads(body)
        except (json.JSONDecodeError, ValueError) as exc:
            raise ERPCHealthCheckError(f"Failed to parse health response: {exc}") from exc

        return HealthStatus.from_dict(data)

    @property
    def is_healthy(self) -> bool:
        """Quick boolean health check.

        Returns:
            ``True`` if the health endpoint responds successfully, ``False`` otherwise.

        """
        try:
            self.health()
        except ERPCHealthCheckError:
            return False
        return True

    def metrics(self) -> dict[str, float]:
        """Fetch and parse Prometheus metrics from eRPC.

        Queries the metrics endpoint and returns a flat dictionary of
        metric names (with labels) to their float values.

        Returns:
            Mapping of metric name (with labels) to value.

        Raises:
            ERPCHealthCheckError: On connection failure or timeout.

        """
        parsed = urlparse(self.base_url)
        host = parsed.hostname or "127.0.0.1"
        url = f"http://{host}:{self.metrics_port}/metrics"

        try:
            with urlopen(url, timeout=self.timeout) as resp:
                body = resp.read()
        except (URLError, OSError, TimeoutError) as exc:
            raise ERPCHealthCheckError(f"Failed to fetch metrics from {url}: {exc}") from exc

        return self._parse_prometheus(body.decode("utf-8", errors="replace"))

    @staticmethod
    def _parse_prometheus(text: str) -> dict[str, float]:
        """Parse Prometheus exposition format into a flat dict.

        Args:
            text: Raw Prometheus metrics text.

        Returns:
            Mapping of metric name (with labels) to float value.

        """
        result: dict[str, float] = {}
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            match = _METRIC_LINE_RE.match(line)
            if match:
                result[match.group(1)] = float(match.group(2))
        return result
