"""Error parsing and classification utilities for eRPC upstream responses.

This module provides utilities to parse and classify JSON-RPC errors returned
by eRPC, making them more human-readable and actionable for developers.

Examples:
    Parse a raw eRPC error response::

        >>> error_dict = {'code': -32603, 'message': 'http request handling timeout'}
        >>> result = parse_rpc_error(error_dict)
        >>> result.error_type
        'timeout'
        >>> result.is_transient
        True
        >>> result.human_message
        'eRPC upstream timeout: request timed out (code: -32603)'

"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ErrorInfo:
    """Structured information about a parsed RPC error.

    Attributes:
        error_type: Classification of the error (timeout, rate_limit, connection, etc.).
        is_transient: Whether this error is likely temporary and can be retried.
        human_message: Human-readable description of the error.
        raw_code: Original JSON-RPC error code.
        raw_message: Original error message from the upstream.

    """

    error_type: str
    is_transient: bool
    human_message: str
    raw_code: int
    raw_message: str


def parse_rpc_error(error_dict: dict[str, Any]) -> ErrorInfo:
    """Parse and classify a JSON-RPC error from eRPC.

    Analyzes the error code and message to determine the error type,
    whether it's transient, and creates a human-readable message.

    Args:
        error_dict: JSON-RPC error object with 'code' and 'message' fields.

    Returns:
        Structured error information with classification and human-readable message.

    Examples:
        >>> parse_rpc_error({"code": -32603, "message": "timeout"})
        ErrorInfo(error_type='timeout', is_transient=True, ...)

    """
    code = error_dict.get("code", 0)
    raw_message = error_dict.get("message", "")
    message = raw_message.lower()

    # Classify the error based on code and message patterns
    if code == -32603:
        if any(keyword in message for keyword in ["timeout", "timed out", "deadline"]):
            return _build_timeout_error(code, raw_message)
        elif "connection" in message and ("refused" in message or "failed" in message):
            return _build_connection_error(code, raw_message)
        else:
            return _build_internal_error(code, raw_message)

    elif code == -32000:
        if any(keyword in message for keyword in ["rate limit", "too many", "throttle"]):
            return _build_rate_limit_error(code, raw_message)
        else:
            return _build_server_error(code, raw_message)

    elif code == -32001:
        return _build_unauthorized_error(code, raw_message)

    elif code == -32002:
        return _build_resource_error(code, raw_message)

    elif code in (-32700, -32600, -32601, -32602):
        return _build_parse_error(code, raw_message)

    else:
        return _build_unknown_error(code, raw_message)


def _build_timeout_error(code: int, message: str) -> ErrorInfo:
    """Build error info for timeout errors."""
    # Try to extract timeout duration from message
    duration_match = re.search(r"(\d+\.?\d*)\s*(?:s|sec|second)", message)
    duration_str = f" after {duration_match.group(1)}s" if duration_match else ""

    human_msg = f"eRPC upstream timeout: request timed out{duration_str} (code: {code})"

    return ErrorInfo(
        error_type="timeout",
        is_transient=True,
        human_message=human_msg,
        raw_code=code,
        raw_message=message,
    )


def _build_rate_limit_error(code: int, message: str) -> ErrorInfo:
    """Build error info for rate limit errors."""
    # Truncate very long messages for readability
    display_msg = message[:100] + "..." if len(message) > 100 else message
    human_msg = f"eRPC rate limit exceeded: {display_msg} (code: {code})"

    return ErrorInfo(
        error_type="rate_limit",
        is_transient=True,
        human_message=human_msg,
        raw_code=code,
        raw_message=message,
    )


def _build_connection_error(code: int, message: str) -> ErrorInfo:
    """Build error info for connection errors."""
    human_msg = f"eRPC connection failed: upstream unreachable (code: {code})"

    return ErrorInfo(
        error_type="connection",
        is_transient=True,
        human_message=human_msg,
        raw_code=code,
        raw_message=message,
    )


def _build_internal_error(code: int, message: str) -> ErrorInfo:
    """Build error info for internal server errors."""
    # Truncate very long messages for readability
    display_msg = message[:100] + "..." if len(message) > 100 else message
    human_msg = f"eRPC internal error: {display_msg} (code: {code})"

    return ErrorInfo(
        error_type="internal",
        is_transient=False,
        human_message=human_msg,
        raw_code=code,
        raw_message=message,
    )


def _build_server_error(code: int, message: str) -> ErrorInfo:
    """Build error info for general server errors."""
    # Truncate very long messages for readability
    display_msg = message[:100] + "..." if len(message) > 100 else message
    human_msg = f"eRPC server error: {display_msg} (code: {code})"

    return ErrorInfo(
        error_type="server",
        is_transient=False,
        human_message=human_msg,
        raw_code=code,
        raw_message=message,
    )


def _build_unauthorized_error(code: int, message: str) -> ErrorInfo:
    """Build error info for unauthorized errors."""
    human_msg = f"eRPC authentication failed: check API keys or permissions (code: {code})"

    return ErrorInfo(
        error_type="unauthorized",
        is_transient=False,
        human_message=human_msg,
        raw_code=code,
        raw_message=message,
    )


def _build_resource_error(code: int, message: str) -> ErrorInfo:
    """Build error info for resource exhaustion errors."""
    # Truncate very long messages for readability
    display_msg = message[:100] + "..." if len(message) > 100 else message
    human_msg = f"eRPC resource limit: {display_msg} (code: {code})"

    return ErrorInfo(
        error_type="resource",
        is_transient=True,
        human_message=human_msg,
        raw_code=code,
        raw_message=message,
    )


def _build_parse_error(code: int, message: str) -> ErrorInfo:
    """Build error info for JSON-RPC parse/method errors."""
    # Truncate very long messages for readability
    display_msg = message[:100] + "..." if len(message) > 100 else message
    human_msg = f"eRPC request error: {display_msg} (code: {code})"

    return ErrorInfo(
        error_type="parse",
        is_transient=False,
        human_message=human_msg,
        raw_code=code,
        raw_message=message,
    )


def _build_unknown_error(code: int, message: str) -> ErrorInfo:
    """Build error info for unknown error codes."""
    # Truncate very long messages for readability
    display_msg = message[:100] + "..." if len(message) > 100 else message
    human_msg = f"eRPC unknown error: {display_msg} (code: {code})"

    return ErrorInfo(
        error_type="unknown",
        is_transient=False,
        human_message=human_msg,
        raw_code=code,
        raw_message=message,
    )


__all__ = ["ErrorInfo", "parse_rpc_error"]
