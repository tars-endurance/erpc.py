"""Tests for erpc.errors module."""

import pytest

from erpc.errors import ErrorInfo, parse_rpc_error


class TestParseRpcError:
    """Test cases for parse_rpc_error function."""

    def test_timeout_error_basic(self):
        """Test parsing a basic timeout error."""
        error_dict = {"code": -32603, "message": "http request handling timeout"}
        result = parse_rpc_error(error_dict)

        assert result.error_type == "timeout"
        assert result.is_transient is True
        assert "timeout" in result.human_message.lower()
        assert "-32603" in result.human_message
        assert result.raw_code == -32603
        assert result.raw_message == "http request handling timeout"

    def test_timeout_error_with_duration(self):
        """Test parsing a timeout error with duration information."""
        error_dict = {"code": -32603, "message": "request timed out after 30s"}
        result = parse_rpc_error(error_dict)

        assert result.error_type == "timeout"
        assert result.is_transient is True
        assert "after 30s" in result.human_message
        assert result.raw_code == -32603

    def test_timeout_error_deadline_variant(self):
        """Test parsing timeout error with deadline keyword."""
        error_dict = {"code": -32603, "message": "deadline exceeded"}
        result = parse_rpc_error(error_dict)

        assert result.error_type == "timeout"
        assert result.is_transient is True
        assert "timeout" in result.human_message.lower()

    def test_rate_limit_error(self):
        """Test parsing rate limit errors."""
        error_dict = {"code": -32000, "message": "rate limit exceeded"}
        result = parse_rpc_error(error_dict)

        assert result.error_type == "rate_limit"
        assert result.is_transient is True
        assert "rate limit" in result.human_message.lower()
        assert result.raw_code == -32000

    def test_rate_limit_too_many_requests(self):
        """Test parsing 'too many requests' as rate limit."""
        error_dict = {"code": -32000, "message": "too many requests"}
        result = parse_rpc_error(error_dict)

        assert result.error_type == "rate_limit"
        assert result.is_transient is True
        assert "rate limit" in result.human_message.lower()

    def test_connection_refused_error(self):
        """Test parsing connection refused errors."""
        error_dict = {"code": -32603, "message": "connection refused"}
        result = parse_rpc_error(error_dict)

        assert result.error_type == "connection"
        assert result.is_transient is True
        assert "connection failed" in result.human_message.lower()
        assert "unreachable" in result.human_message.lower()

    def test_connection_failed_error(self):
        """Test parsing connection failed errors."""
        error_dict = {"code": -32603, "message": "connection failed to upstream"}
        result = parse_rpc_error(error_dict)

        assert result.error_type == "connection"
        assert result.is_transient is True
        assert "connection failed" in result.human_message.lower()

    def test_unauthorized_error(self):
        """Test parsing unauthorized errors."""
        error_dict = {"code": -32001, "message": "unauthorized access"}
        result = parse_rpc_error(error_dict)

        assert result.error_type == "unauthorized"
        assert result.is_transient is False
        assert "authentication failed" in result.human_message.lower()
        assert "api keys" in result.human_message.lower()

    def test_resource_error(self):
        """Test parsing resource exhaustion errors."""
        error_dict = {"code": -32002, "message": "resource exhausted"}
        result = parse_rpc_error(error_dict)

        assert result.error_type == "resource"
        assert result.is_transient is True
        assert "resource limit" in result.human_message.lower()

    def test_parse_error_invalid_json(self):
        """Test parsing JSON-RPC parse errors."""
        error_dict = {"code": -32700, "message": "parse error: invalid json"}
        result = parse_rpc_error(error_dict)

        assert result.error_type == "parse"
        assert result.is_transient is False
        assert "request error" in result.human_message.lower()

    def test_parse_error_invalid_request(self):
        """Test parsing invalid request errors."""
        error_dict = {"code": -32600, "message": "invalid request"}
        result = parse_rpc_error(error_dict)

        assert result.error_type == "parse"
        assert result.is_transient is False

    def test_parse_error_method_not_found(self):
        """Test parsing method not found errors."""
        error_dict = {"code": -32601, "message": "method not found"}
        result = parse_rpc_error(error_dict)

        assert result.error_type == "parse"
        assert result.is_transient is False

    def test_parse_error_invalid_params(self):
        """Test parsing invalid params errors."""
        error_dict = {"code": -32602, "message": "invalid params"}
        result = parse_rpc_error(error_dict)

        assert result.error_type == "parse"
        assert result.is_transient is False

    def test_internal_error_generic(self):
        """Test parsing generic internal errors."""
        error_dict = {"code": -32603, "message": "internal server error"}
        result = parse_rpc_error(error_dict)

        assert result.error_type == "internal"
        assert result.is_transient is False
        assert "internal error" in result.human_message.lower()

    def test_server_error_generic(self):
        """Test parsing generic server errors."""
        error_dict = {"code": -32000, "message": "server error occurred"}
        result = parse_rpc_error(error_dict)

        assert result.error_type == "server"
        assert result.is_transient is False
        assert "server error" in result.human_message.lower()

    def test_unknown_error_code(self):
        """Test parsing unknown error codes."""
        error_dict = {"code": -50000, "message": "custom error"}
        result = parse_rpc_error(error_dict)

        assert result.error_type == "unknown"
        assert result.is_transient is False
        assert "unknown error" in result.human_message.lower()
        assert result.raw_code == -50000

    def test_missing_code_field(self):
        """Test handling missing code field."""
        error_dict = {"message": "some error"}
        result = parse_rpc_error(error_dict)

        assert result.error_type == "unknown"
        assert result.raw_code == 0

    def test_missing_message_field(self):
        """Test handling missing message field."""
        error_dict = {"code": -32603}
        result = parse_rpc_error(error_dict)

        assert result.error_type == "internal"
        assert result.raw_message == ""

    def test_empty_error_dict(self):
        """Test handling completely empty error dict."""
        error_dict = {}
        result = parse_rpc_error(error_dict)

        assert result.error_type == "unknown"
        assert result.raw_code == 0
        assert result.raw_message == ""

    def test_case_insensitive_matching(self):
        """Test that message matching is case insensitive."""
        error_dict = {"code": -32603, "message": "HTTP REQUEST HANDLING TIMEOUT"}
        result = parse_rpc_error(error_dict)

        assert result.error_type == "timeout"
        assert result.is_transient is True

    def test_partial_keyword_matching(self):
        """Test that partial keyword matching works."""
        error_dict = {"code": -32000, "message": "rate limiting active"}
        result = parse_rpc_error(error_dict)

        assert result.error_type == "rate_limit"
        assert result.is_transient is True

    def test_duration_extraction_variations(self):
        """Test duration extraction from various formats."""
        test_cases = [
            ("timeout after 5s", "5s"),
            ("request timed out after 30.5s", "30.5s"),
            ("deadline exceeded after 10 seconds", "10s"),
            ("timeout 2.5 sec", "2.5s"),
        ]

        for message, expected_duration in test_cases:
            error_dict = {"code": -32603, "message": message}
            result = parse_rpc_error(error_dict)
            assert expected_duration in result.human_message

    def test_error_info_immutability(self):
        """Test that ErrorInfo objects are immutable."""
        error_dict = {"code": -32603, "message": "timeout"}
        result = parse_rpc_error(error_dict)

        # This should raise an exception since the dataclass is frozen
        with pytest.raises(AttributeError):
            result.error_type = "different_type"


class TestErrorInfo:
    """Test cases for ErrorInfo dataclass."""

    def test_error_info_creation(self):
        """Test creating ErrorInfo instances."""
        info = ErrorInfo(
            error_type="timeout",
            is_transient=True,
            human_message="Request timed out",
            raw_code=-32603,
            raw_message="timeout",
        )

        assert info.error_type == "timeout"
        assert info.is_transient is True
        assert info.human_message == "Request timed out"
        assert info.raw_code == -32603
        assert info.raw_message == "timeout"

    def test_error_info_equality(self):
        """Test ErrorInfo equality comparison."""
        info1 = ErrorInfo("timeout", True, "msg", -32603, "raw")
        info2 = ErrorInfo("timeout", True, "msg", -32603, "raw")
        info3 = ErrorInfo("rate_limit", True, "msg", -32000, "raw")

        assert info1 == info2
        assert info1 != info3

    def test_error_info_repr(self):
        """Test ErrorInfo string representation."""
        info = ErrorInfo("timeout", True, "msg", -32603, "raw")
        repr_str = repr(info)

        assert "ErrorInfo" in repr_str
        assert "timeout" in repr_str
        assert "True" in repr_str


class TestTransiencyClassification:
    """Test cases specifically for transient vs permanent error classification."""

    def test_transient_errors(self):
        """Test that appropriate errors are classified as transient."""
        transient_cases = [
            {"code": -32603, "message": "timeout"},
            {"code": -32603, "message": "connection refused"},
            {"code": -32603, "message": "connection failed"},
            {"code": -32000, "message": "rate limit exceeded"},
            {"code": -32000, "message": "too many requests"},
            {"code": -32002, "message": "resource exhausted"},
        ]

        for error_dict in transient_cases:
            result = parse_rpc_error(error_dict)
            assert result.is_transient is True, f"Expected transient for {error_dict}"

    def test_permanent_errors(self):
        """Test that appropriate errors are classified as permanent."""
        permanent_cases = [
            {"code": -32603, "message": "internal server error"},
            {"code": -32000, "message": "server error"},
            {"code": -32001, "message": "unauthorized"},
            {"code": -32700, "message": "parse error"},
            {"code": -32600, "message": "invalid request"},
            {"code": -32601, "message": "method not found"},
            {"code": -32602, "message": "invalid params"},
            {"code": -50000, "message": "unknown error"},
        ]

        for error_dict in permanent_cases:
            result = parse_rpc_error(error_dict)
            assert result.is_transient is False, f"Expected permanent for {error_dict}"


class TestHumanReadableFormatting:
    """Test cases for human-readable error message formatting."""

    def test_consistent_formatting(self):
        """Test that all error messages follow consistent formatting."""
        test_cases = [
            {"code": -32603, "message": "timeout"},
            {"code": -32000, "message": "rate limit"},
            {"code": -32001, "message": "unauthorized"},
            {"code": -32002, "message": "resource exhausted"},
        ]

        for error_dict in test_cases:
            result = parse_rpc_error(error_dict)
            # All messages should start with "eRPC"
            assert result.human_message.startswith("eRPC")
            # All messages should include the error code
            assert f"(code: {error_dict['code']})" in result.human_message

    def test_message_length_reasonable(self):
        """Test that error messages are reasonably sized."""
        error_dict = {"code": -32603, "message": "x" * 1000}  # Very long message
        result = parse_rpc_error(error_dict)

        # Message should be reasonable length (not just pass through the entire raw message)
        assert len(result.human_message) < 200

    def test_special_characters_handled(self):
        """Test that special characters in messages are handled properly."""
        error_dict = {"code": -32603, "message": 'timeout with "quotes" and newlines\n'}
        result = parse_rpc_error(error_dict)

        # Should not crash and should produce valid output
        assert result.error_type == "timeout"
        assert isinstance(result.human_message, str)
        assert len(result.human_message) > 0
