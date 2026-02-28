"""Tests for error parsing functionality in errors module."""

from erpc.errors import ErrorInfo, parse_rpc_error


class TestLegacyCompatibility:
    """Test that legacy error parsing still works with the new implementation."""

    def test_basic_timeout_error(self):
        """Test parsing a basic timeout error."""
        error_dict = {"code": -32603, "message": "Request timed out"}
        result = parse_rpc_error(error_dict)

        assert isinstance(result, ErrorInfo)
        assert result.error_type == "timeout"
        assert result.is_transient is True
        assert "timeout" in result.human_message.lower()
        assert result.raw_code == -32603

    def test_rate_limit_error(self):
        """Test parsing rate limit errors."""
        error_dict = {"code": -32000, "message": "rate limit exceeded"}
        result = parse_rpc_error(error_dict)

        assert result.error_type == "rate_limit"
        assert result.is_transient is True
        assert "rate limit" in result.human_message.lower()

    def test_connection_error(self):
        """Test parsing connection errors."""
        error_dict = {"code": -32603, "message": "connection refused"}
        result = parse_rpc_error(error_dict)

        assert result.error_type == "connection"
        assert result.is_transient is True
        assert "connection" in result.human_message.lower()

    def test_parse_error(self):
        """Test parsing JSON-RPC parse errors."""
        error_dict = {"code": -32700, "message": "parse error"}
        result = parse_rpc_error(error_dict)

        assert result.error_type == "parse"
        assert result.is_transient is False
        assert "request error" in result.human_message.lower()

    def test_unknown_error(self):
        """Test parsing unknown error codes."""
        error_dict = {"code": -50000, "message": "custom error"}
        result = parse_rpc_error(error_dict)

        assert result.error_type == "unknown"
        assert result.is_transient is False
        assert "unknown error" in result.human_message.lower()

    def test_empty_error_dict(self):
        """Test handling of empty or malformed error dicts."""
        result = parse_rpc_error({})

        assert result.error_type == "unknown"
        assert result.raw_code == 0
        assert result.raw_message == ""
        assert "unknown error" in result.human_message.lower()

    def test_error_info_immutability(self):
        """Test that ErrorInfo objects are frozen/immutable."""
        error_dict = {"code": -32603, "message": "timeout"}
        result = parse_rpc_error(error_dict)

        # This should raise an exception since the dataclass is frozen
        try:
            result.error_type = "different_type"
            raise AssertionError("Expected AttributeError for frozen dataclass")
        except AttributeError:
            pass  # Expected behavior


class TestTransientErrorClassification:
    """Test that transient/permanent classification works correctly."""

    def test_transient_error_types(self):
        """Test errors that should be classified as transient."""
        transient_cases = [
            {"code": -32603, "message": "timeout"},
            {"code": -32603, "message": "connection refused"},
            {"code": -32000, "message": "rate limit exceeded"},
            {"code": -32002, "message": "resource exhausted"},
        ]

        for error_dict in transient_cases:
            result = parse_rpc_error(error_dict)
            assert result.is_transient is True, f"Expected transient for {error_dict}"

    def test_permanent_error_types(self):
        """Test errors that should be classified as permanent."""
        permanent_cases = [
            {"code": -32700, "message": "parse error"},
            {"code": -32600, "message": "invalid request"},
            {"code": -32001, "message": "unauthorized"},
            {"code": -32603, "message": "internal server error"},
            {"code": -50000, "message": "unknown error"},
        ]

        for error_dict in permanent_cases:
            result = parse_rpc_error(error_dict)
            assert result.is_transient is False, f"Expected permanent for {error_dict}"


class TestHumanReadableMessages:
    """Test that human-readable messages are properly formatted."""

    def test_message_contains_code(self):
        """Test that human messages include the error code."""
        error_dict = {"code": -32603, "message": "timeout"}
        result = parse_rpc_error(error_dict)

        assert f"(code: {error_dict['code']})" in result.human_message

    def test_message_starts_with_erpc(self):
        """Test that all messages start with 'eRPC'."""
        test_cases = [
            {"code": -32603, "message": "timeout"},
            {"code": -32000, "message": "rate limit"},
            {"code": -32001, "message": "unauthorized"},
        ]

        for error_dict in test_cases:
            result = parse_rpc_error(error_dict)
            assert result.human_message.startswith("eRPC")

    def test_duration_extraction(self):
        """Test that timeout durations are extracted from messages."""
        error_dict = {"code": -32603, "message": "request timed out after 30s"}
        result = parse_rpc_error(error_dict)

        assert "after 30s" in result.human_message
