"""Tests for eRPC binary installation."""

from unittest.mock import patch

import pytest

from erpc.exceptions import ERPCError
from erpc.install import get_platform_binary_name


class TestGetPlatformBinaryName:
    def test_linux_amd64(self):
        with (
            patch("platform.system", return_value="Linux"),
            patch("platform.machine", return_value="x86_64"),
        ):
            assert get_platform_binary_name() == "erpc_linux_amd64"

    def test_linux_arm64(self):
        with (
            patch("platform.system", return_value="Linux"),
            patch("platform.machine", return_value="aarch64"),
        ):
            assert get_platform_binary_name() == "erpc_linux_arm64"

    def test_darwin_amd64(self):
        with (
            patch("platform.system", return_value="Darwin"),
            patch("platform.machine", return_value="x86_64"),
        ):
            assert get_platform_binary_name() == "erpc_darwin_amd64"

    def test_darwin_arm64(self):
        with (
            patch("platform.system", return_value="Darwin"),
            patch("platform.machine", return_value="arm64"),
        ):
            assert get_platform_binary_name() == "erpc_darwin_arm64"

    def test_unsupported_platform(self):
        with (
            patch("platform.system", return_value="Windows"),
            patch("platform.machine", return_value="AMD64"),
            pytest.raises(ERPCError, match="Unsupported platform"),
        ):
            get_platform_binary_name()
