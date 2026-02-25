"""Mock JSON-RPC upstream server for integration testing.

Provides a configurable HTTP server that responds to Ethereum JSON-RPC
requests with canned responses. Supports error injection, latency
simulation, and availability toggling.

Examples:
    Context manager usage::

        with MockUpstream(port=9545) as upstream:
            # upstream.url is "http://127.0.0.1:9545"
            upstream.set_error("eth_blockNumber", code=-32000, message="fail")
            upstream.set_latency(2.0)

"""

from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

# ── Canned Responses ──────────────────────────────────────────────────────────

CANNED_RESPONSES: dict[str, Any] = {
    "eth_blockNumber": "0x1234567",
    "eth_chainId": "0x1",
    "eth_getBlockByNumber": {
        "number": "0x1234567",
        "hash": "0xabc123",
        "parentHash": "0x000000",
        "timestamp": "0x60000000",
        "transactions": [],
    },
}
"""Default canned responses keyed by JSON-RPC method name."""


# ── Request Handler ───────────────────────────────────────────────────────────


class _MockHandler(BaseHTTPRequestHandler):
    """HTTP request handler that responds to JSON-RPC requests."""

    server: _MockHTTPServer  # type: ignore[assignment]

    def do_POST(self) -> None:
        """Handle POST requests with JSON-RPC payloads."""
        state = self.server.state

        if not state.available:
            self.send_error(503, "Service Unavailable")
            return

        if state.latency > 0:
            time.sleep(state.latency)

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        try:
            request = json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            self.send_error(400, "Invalid JSON")
            return

        method: str = request.get("method", "")
        request_id = request.get("id", 1)
        state.request_log.append(request)

        # Check for injected errors first.
        if method in state.errors:
            err = state.errors[method]
            response: dict[str, Any] = {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": err["code"], "message": err["message"]},
            }
        elif method in state.responses:
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": state.responses[method],
            }
        else:
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"},
            }

        payload = json.dumps(response).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress default stderr logging."""


# ── Server State ──────────────────────────────────────────────────────────────


class _ServerState:
    """Mutable shared state for the mock server."""

    def __init__(self) -> None:
        self.responses: dict[str, Any] = dict(CANNED_RESPONSES)
        self.errors: dict[str, dict[str, Any]] = {}
        self.latency: float = 0.0
        self.available: bool = True
        self.request_log: list[dict[str, Any]] = []


class _MockHTTPServer(HTTPServer):
    """HTTPServer subclass that carries mutable state."""

    state: _ServerState


# ── Public API ────────────────────────────────────────────────────────────────


class MockUpstream:
    """A configurable mock JSON-RPC upstream server.

    Args:
        host: Bind address.
        port: Listen port.

    Examples:
        >>> with MockUpstream(port=9545) as mock:
        ...     print(mock.url)
        http://127.0.0.1:9545

    """

    def __init__(self, host: str = "127.0.0.1", port: int = 9545) -> None:
        self.host = host
        self.port = port
        self._state = _ServerState()
        self._server: _MockHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def url(self) -> str:
        """Base URL of the mock server."""
        return f"http://{self.host}:{self.port}"

    @property
    def request_log(self) -> list[dict[str, Any]]:
        """All JSON-RPC requests received by the mock server."""
        return self._state.request_log

    def set_response(self, method: str, result: Any) -> None:
        """Override the canned response for a specific method.

        Args:
            method: JSON-RPC method name.
            result: Result value to return.

        """
        self._state.responses[method] = result

    def set_error(self, method: str, *, code: int = -32000, message: str = "error") -> None:
        """Inject an error response for a specific method.

        Args:
            method: JSON-RPC method name.
            code: JSON-RPC error code.
            message: Error message.

        """
        self._state.errors[method] = {"code": code, "message": message}

    def clear_error(self, method: str) -> None:
        """Remove an injected error for a method.

        Args:
            method: JSON-RPC method name.

        """
        self._state.errors.pop(method, None)

    def set_latency(self, seconds: float) -> None:
        """Add artificial latency to all responses.

        Args:
            seconds: Delay in seconds before responding.

        """
        self._state.latency = seconds

    def set_available(self, available: bool) -> None:
        """Toggle server availability.

        Args:
            available: If ``False``, server returns 503 for all requests.

        """
        self._state.available = available

    def start(self) -> None:
        """Start the mock server in a background thread."""
        self._server = _MockHTTPServer((self.host, self.port), _MockHandler)
        self._server.state = self._state
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Shut down the mock server."""
        if self._server:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None

    def __enter__(self) -> MockUpstream:
        """Start the server on context entry."""
        self.start()
        return self

    def __exit__(self, *args: object) -> None:
        """Stop the server on context exit."""
        self.stop()
