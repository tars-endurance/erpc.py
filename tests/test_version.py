"""Tests for eRPC version detection."""

from unittest.mock import patch

from erpc.version import get_erpc_version


def test_version_returns_none_when_binary_not_found():
    with patch("erpc.version.find_erpc_binary", side_effect=Exception("not found")):
        assert get_erpc_version() is None


def test_version_with_mock_binary():
    with patch("erpc.version.find_erpc_binary", return_value="/usr/bin/echo"):
        result = get_erpc_version()
        # echo prints its args, so we get "--version" back
        assert result is not None
