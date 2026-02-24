"""Tests for eRPC version detection."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

from erpc.version import get_erpc_version


class TestGetErpcVersion:
    def test_parses_version_output(self) -> None:
        """Parses version from 'erpc version X.Y.Z' format."""
        mock_result = MagicMock()
        mock_result.stdout = "erpc version 0.0.62\n"
        mock_result.stderr = ""

        with (
            patch("erpc.version.find_erpc_binary", return_value="/usr/local/bin/erpc"),
            patch("subprocess.run", return_value=mock_result),
        ):
            assert get_erpc_version() == "0.0.62"

    def test_parses_bare_version(self) -> None:
        """Parses bare version string without prefix."""
        mock_result = MagicMock()
        mock_result.stdout = "0.0.62\n"
        mock_result.stderr = ""

        with (
            patch("erpc.version.find_erpc_binary", return_value="/usr/local/bin/erpc"),
            patch("subprocess.run", return_value=mock_result),
        ):
            assert get_erpc_version() == "0.0.62"

    def test_parses_v_prefix(self) -> None:
        """Strips 'v' prefix from version."""
        mock_result = MagicMock()
        mock_result.stdout = "v0.0.62\n"
        mock_result.stderr = ""

        with (
            patch("erpc.version.find_erpc_binary", return_value="/usr/local/bin/erpc"),
            patch("subprocess.run", return_value=mock_result),
        ):
            assert get_erpc_version() == "0.0.62"

    def test_returns_none_when_binary_not_found(self) -> None:
        with patch("erpc.version.find_erpc_binary", side_effect=Exception("not found")):
            assert get_erpc_version() is None

    def test_returns_none_on_timeout(self) -> None:
        with (
            patch("erpc.version.find_erpc_binary", return_value="/usr/local/bin/erpc"),
            patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="erpc", timeout=5)),
        ):
            assert get_erpc_version() is None

    def test_returns_none_on_empty_output(self) -> None:
        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.stderr = ""

        with (
            patch("erpc.version.find_erpc_binary", return_value="/usr/local/bin/erpc"),
            patch("subprocess.run", return_value=mock_result),
        ):
            assert get_erpc_version() is None

    def test_uses_stderr_fallback(self) -> None:
        """Falls back to stderr when stdout is empty."""
        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.stderr = "erpc version 0.0.62\n"

        with (
            patch("erpc.version.find_erpc_binary", return_value="/usr/local/bin/erpc"),
            patch("subprocess.run", return_value=mock_result),
        ):
            assert get_erpc_version() == "0.0.62"
