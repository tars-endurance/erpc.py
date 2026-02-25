"""Tests for eRPC binary installation."""

from __future__ import annotations

import hashlib
import stat
from pathlib import Path
from unittest.mock import patch

import pytest

from erpc.exceptions import ERPCError
from erpc.install import get_platform_binary_name, install_erpc, verify_checksum


class TestGetPlatformBinaryName:
    def test_linux_amd64(self) -> None:
        with (
            patch("platform.system", return_value="Linux"),
            patch("platform.machine", return_value="x86_64"),
        ):
            assert get_platform_binary_name() == "erpc_linux_x86_64"

    def test_linux_arm64(self) -> None:
        with (
            patch("platform.system", return_value="Linux"),
            patch("platform.machine", return_value="aarch64"),
        ):
            assert get_platform_binary_name() == "erpc_linux_arm64"

    def test_darwin_amd64(self) -> None:
        with (
            patch("platform.system", return_value="Darwin"),
            patch("platform.machine", return_value="x86_64"),
        ):
            assert get_platform_binary_name() == "erpc_darwin_x86_64"

    def test_darwin_arm64(self) -> None:
        with (
            patch("platform.system", return_value="Darwin"),
            patch("platform.machine", return_value="arm64"),
        ):
            assert get_platform_binary_name() == "erpc_darwin_arm64"

    def test_unsupported_platform(self) -> None:
        with (
            patch("platform.system", return_value="Windows"),
            patch("platform.machine", return_value="AMD64"),
            pytest.raises(ERPCError, match="Unsupported platform"),
        ):
            get_platform_binary_name()

    def test_unsupported_architecture(self) -> None:
        with (
            patch("platform.system", return_value="Linux"),
            patch("platform.machine", return_value="mips"),
            pytest.raises(ERPCError, match="Unsupported platform"),
        ):
            get_platform_binary_name()


class TestInstallErpc:
    def test_downloads_binary(self, tmp_path: Path) -> None:
        """Verify download URL construction and executable permissions."""
        with (
            patch("erpc.install.get_platform_binary_name", return_value="erpc_linux_x86_64"),
            patch("erpc.install.urllib.request.urlretrieve") as mock_retrieve,
        ):
            # urlretrieve writes a file; simulate by creating it in the callback
            dest = tmp_path / "erpc"

            def fake_retrieve(url: str, filename: str) -> tuple[str, None]:
                Path(filename).write_bytes(b"fake-binary")
                return (filename, None)

            mock_retrieve.side_effect = fake_retrieve

            result = install_erpc("0.0.62", install_dir=str(tmp_path))

            assert result == dest
            mock_retrieve.assert_called_once_with(
                "https://github.com/erpc/erpc/releases/download/0.0.62/erpc_linux_x86_64",
                str(dest),
            )
            # Check executable bit is set
            mode = dest.stat().st_mode
            assert mode & stat.S_IEXEC

    def test_with_checksum(self, tmp_path: Path) -> None:
        """Verify checksum validation succeeds with correct hash."""
        binary_content = b"real-erpc-binary-content"
        expected_hash = hashlib.sha256(binary_content).hexdigest()

        with (
            patch("erpc.install.get_platform_binary_name", return_value="erpc_linux_x86_64"),
            patch("erpc.install.urllib.request.urlretrieve") as mock_retrieve,
        ):

            def fake_retrieve(url: str, filename: str) -> tuple[str, None]:
                Path(filename).write_bytes(binary_content)
                return (filename, None)

            mock_retrieve.side_effect = fake_retrieve

            result = install_erpc("0.0.62", install_dir=str(tmp_path), checksum=expected_hash)
            assert result.exists()

    def test_checksum_mismatch(self, tmp_path: Path) -> None:
        """Raises ERPCError when checksum doesn't match."""
        with (
            patch("erpc.install.get_platform_binary_name", return_value="erpc_linux_x86_64"),
            patch("erpc.install.urllib.request.urlretrieve") as mock_retrieve,
        ):

            def fake_retrieve(url: str, filename: str) -> tuple[str, None]:
                Path(filename).write_bytes(b"some-content")
                return (filename, None)

            mock_retrieve.side_effect = fake_retrieve

            with pytest.raises(ERPCError, match="Checksum mismatch"):
                install_erpc(
                    "0.0.62",
                    install_dir=str(tmp_path),
                    checksum="0000000000000000000000000000000000000000000000000000000000000000",
                )

    def test_creates_directory(self, tmp_path: Path) -> None:
        """Creates install_dir if it doesn't exist."""
        nested = tmp_path / "deep" / "nested" / "dir"
        assert not nested.exists()

        with (
            patch("erpc.install.get_platform_binary_name", return_value="erpc_linux_x86_64"),
            patch("erpc.install.urllib.request.urlretrieve") as mock_retrieve,
        ):

            def fake_retrieve(url: str, filename: str) -> tuple[str, None]:
                Path(filename).write_bytes(b"binary")
                return (filename, None)

            mock_retrieve.side_effect = fake_retrieve

            result = install_erpc("0.0.62", install_dir=str(nested))
            assert nested.exists()
            assert result.exists()

    def test_cleans_up_on_checksum_failure(self, tmp_path: Path) -> None:
        """Removes downloaded file when checksum verification fails."""
        with (
            patch("erpc.install.get_platform_binary_name", return_value="erpc_linux_x86_64"),
            patch("erpc.install.urllib.request.urlretrieve") as mock_retrieve,
        ):

            def fake_retrieve(url: str, filename: str) -> tuple[str, None]:
                Path(filename).write_bytes(b"bad-content")
                return (filename, None)

            mock_retrieve.side_effect = fake_retrieve
            dest = tmp_path / "erpc"

            with pytest.raises(ERPCError, match="Checksum mismatch"):
                install_erpc(
                    "0.0.62",
                    install_dir=str(tmp_path),
                    checksum="0" * 64,
                )
            assert not dest.exists(), "Bad binary should be cleaned up"


class TestVerifyChecksum:
    def test_valid_checksum(self, tmp_path: Path) -> None:
        f = tmp_path / "file.bin"
        content = b"hello world"
        f.write_bytes(content)
        expected = hashlib.sha256(content).hexdigest()
        # Should not raise
        verify_checksum(f, expected)

    def test_uppercase_checksum(self, tmp_path: Path) -> None:
        """Accepts uppercase hex digest."""
        f = tmp_path / "file.bin"
        content = b"hello world"
        f.write_bytes(content)
        expected = hashlib.sha256(content).hexdigest().upper()
        # Should not raise
        verify_checksum(f, expected)

    def test_invalid_checksum(self, tmp_path: Path) -> None:
        f = tmp_path / "file.bin"
        f.write_bytes(b"hello world")
        with pytest.raises(ERPCError, match="Checksum mismatch"):
            verify_checksum(f, "bad" * 16)
