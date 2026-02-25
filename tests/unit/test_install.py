"""Tests for eRPC binary installation."""

from __future__ import annotations

import hashlib
import stat
from pathlib import Path
from unittest.mock import patch

import pytest

from erpc.exceptions import ERPCError
from erpc.install import (
    PLATFORM_MAP,
    fetch_checksums,
    get_platform_binary_name,
    install_erpc,
    verify_checksum,
)


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

    def test_windows_amd64(self) -> None:
        with (
            patch("platform.system", return_value="Windows"),
            patch("platform.machine", return_value="AMD64"),
        ):
            assert get_platform_binary_name() == "erpc_windows_x86_64.exe"

    def test_unsupported_platform(self) -> None:
        with (
            patch("platform.system", return_value="FreeBSD"),
            patch("platform.machine", return_value="x86_64"),
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
            patch("erpc.install.fetch_checksums", side_effect=Exception("offline")),
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
            patch("erpc.install.fetch_checksums", return_value={}),
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
            patch("erpc.install.fetch_checksums", return_value={}),
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
            patch("erpc.install.fetch_checksums", side_effect=Exception("offline")),
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
            patch("erpc.install.fetch_checksums", return_value={}),
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


class TestFetchChecksums:
    """Tests for checksums.txt parsing."""

    def test_parse_checksums_txt(self) -> None:
        """Parse standard checksums.txt format."""
        content = (
            "72108e2a968dbd123  erpc_linux_x86_64\n"
            "775b33793c879d456  erpc_darwin_x86_64\n"
            "e17cbaa6f15461789  erpc_darwin_arm64\n"
        )
        with patch("erpc.install.urllib.request.urlopen") as mock_open:
            mock_resp = mock_open.return_value.__enter__.return_value
            mock_resp.read.return_value = content.encode()
            result = fetch_checksums("0.0.62")

        assert result == {
            "erpc_linux_x86_64": "72108e2a968dbd123",
            "erpc_darwin_x86_64": "775b33793c879d456",
            "erpc_darwin_arm64": "e17cbaa6f15461789",
        }

    def test_empty_checksums(self) -> None:
        """Handle empty checksums.txt gracefully."""
        with patch("erpc.install.urllib.request.urlopen") as mock_open:
            mock_resp = mock_open.return_value.__enter__.return_value
            mock_resp.read.return_value = b""
            result = fetch_checksums("0.0.62")
        assert result == {}


class TestAutoChecksum:
    """Tests for auto-checksum verification in install_erpc."""

    def test_auto_fetches_and_verifies(self, tmp_path: Path) -> None:
        """install_erpc auto-fetches checksums and verifies."""
        binary_content = b"real-binary"
        expected_hash = hashlib.sha256(binary_content).hexdigest()

        with (
            patch("erpc.install.get_platform_binary_name", return_value="erpc_linux_x86_64"),
            patch("erpc.install.urllib.request.urlretrieve") as mock_retrieve,
            patch(
                "erpc.install.fetch_checksums",
                return_value={"erpc_linux_x86_64": expected_hash},
            ),
        ):

            def fake_retrieve(url: str, filename: str) -> tuple[str, None]:
                Path(filename).write_bytes(binary_content)
                return (filename, None)

            mock_retrieve.side_effect = fake_retrieve
            result = install_erpc("0.0.62", install_dir=str(tmp_path))
            assert result.exists()

    def test_auto_checksum_mismatch_deletes(self, tmp_path: Path) -> None:
        """Auto-fetched checksum mismatch deletes the binary."""
        with (
            patch("erpc.install.get_platform_binary_name", return_value="erpc_linux_x86_64"),
            patch("erpc.install.urllib.request.urlretrieve") as mock_retrieve,
            patch(
                "erpc.install.fetch_checksums",
                return_value={"erpc_linux_x86_64": "0" * 64},
            ),
        ):

            def fake_retrieve(url: str, filename: str) -> tuple[str, None]:
                Path(filename).write_bytes(b"tampered-binary")
                return (filename, None)

            mock_retrieve.side_effect = fake_retrieve

            with pytest.raises(ERPCError, match="Checksum mismatch"):
                install_erpc("0.0.62", install_dir=str(tmp_path))
            assert not (tmp_path / "erpc").exists()

    def test_fetch_failure_continues(self, tmp_path: Path) -> None:
        """If checksums.txt can't be fetched, install continues without verification."""
        with (
            patch("erpc.install.get_platform_binary_name", return_value="erpc_linux_x86_64"),
            patch("erpc.install.urllib.request.urlretrieve") as mock_retrieve,
            patch("erpc.install.fetch_checksums", side_effect=Exception("network error")),
        ):

            def fake_retrieve(url: str, filename: str) -> tuple[str, None]:
                Path(filename).write_bytes(b"binary")
                return (filename, None)

            mock_retrieve.side_effect = fake_retrieve
            result = install_erpc("0.0.62", install_dir=str(tmp_path))
            assert result.exists()

    def test_explicit_checksum_overrides_auto(self, tmp_path: Path) -> None:
        """Explicit checksum parameter takes precedence over auto-fetch."""
        binary_content = b"my-binary"
        correct_hash = hashlib.sha256(binary_content).hexdigest()

        with (
            patch("erpc.install.get_platform_binary_name", return_value="erpc_linux_x86_64"),
            patch("erpc.install.urllib.request.urlretrieve") as mock_retrieve,
            patch("erpc.install.fetch_checksums") as mock_fetch,
        ):

            def fake_retrieve(url: str, filename: str) -> tuple[str, None]:
                Path(filename).write_bytes(binary_content)
                return (filename, None)

            mock_retrieve.side_effect = fake_retrieve
            result = install_erpc("0.0.62", install_dir=str(tmp_path), checksum=correct_hash)
            assert result.exists()
            # fetch_checksums should NOT be called when explicit checksum given
            mock_fetch.assert_not_called()


class TestPlatformArtifactNames:
    """Verify PLATFORM_MAP artifact names exist in the actual GitHub release."""

    @pytest.mark.parametrize(
        "artifact_name",
        list(PLATFORM_MAP.values()),
        ids=list(PLATFORM_MAP.values()),
    )
    def test_artifact_exists_in_release(self, artifact_name: str) -> None:
        """Each artifact in PLATFORM_MAP must exist in the pinned eRPC release."""
        import urllib.request

        from erpc import ERPC_VERSION
        from erpc.install import GITHUB_RELEASES_URL

        url = f"{GITHUB_RELEASES_URL}/{ERPC_VERSION}/{artifact_name}"
        req = urllib.request.Request(url, method="HEAD")
        # GitHub redirects to the CDN; follow redirects
        try:
            resp = urllib.request.urlopen(req, timeout=10)
            assert resp.status == 200, f"Expected 200 for {url}, got {resp.status}"
        except urllib.error.HTTPError as e:
            pytest.fail(f"Artifact {artifact_name!r} not found at {url}: {e}")
