"""eRPC binary installation helpers.

Inspired by `py-geth <https://github.com/ethereum/py-geth>`_'s install module.
Handles cross-platform binary download from GitHub releases with optional
SHA256 checksum verification.
"""

from __future__ import annotations

import hashlib
import logging
import platform
import stat
import urllib.request
from pathlib import Path

from erpc.exceptions import ERPCError

logger = logging.getLogger(__name__)

GITHUB_RELEASES_URL = "https://github.com/erpc/erpc/releases/download"
"""Base URL for eRPC GitHub release artifacts."""

PLATFORM_MAP: dict[tuple[str, str], str] = {
    ("Linux", "x86_64"): "erpc_linux_amd64",
    ("Linux", "aarch64"): "erpc_linux_arm64",
    ("Darwin", "x86_64"): "erpc_darwin_amd64",
    ("Darwin", "arm64"): "erpc_darwin_arm64",
}
"""Mapping of ``(system, machine)`` to release artifact names."""


def get_platform_binary_name() -> str:
    """Get the eRPC binary artifact name for the current platform.

    Returns:
        Artifact filename for the current OS and architecture.

    Raises:
        ERPCError: If the current platform is not supported.

    Examples:
        >>> get_platform_binary_name()  # On Linux x86_64
        'erpc_linux_amd64'

    """
    key = (platform.system(), platform.machine())
    if key not in PLATFORM_MAP:
        raise ERPCError(
            f"Unsupported platform: {platform.system()} {platform.machine()}. "
            f"Supported: {', '.join(f'{s}/{m}' for s, m in PLATFORM_MAP)}"
        )
    return PLATFORM_MAP[key]


def verify_checksum(path: Path, expected_sha256: str) -> None:
    """Verify the SHA256 checksum of a file.

    Args:
        path: Path to the file to verify.
        expected_sha256: Expected lowercase hex-encoded SHA256 digest.

    Raises:
        ERPCError: If the checksum does not match.

    Examples:
        >>> verify_checksum(Path("/usr/local/bin/erpc"), "abc123...")

    """
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    actual = sha256.hexdigest()
    if actual != expected_sha256:
        raise ERPCError(f"Checksum mismatch for {path}: expected {expected_sha256}, got {actual}")


def install_erpc(
    version: str,
    install_dir: str = "/usr/local/bin",
    binary_name: str = "erpc",
    checksum: str | None = None,
) -> Path:
    """Download and install eRPC binary from GitHub releases.

    Args:
        version: Release version tag (e.g., ``"0.0.62"``).
        install_dir: Directory to install the binary. Created if it doesn't exist.
        binary_name: Name for the installed binary.
        checksum: Optional SHA256 hex digest for verification.

    Returns:
        Path to the installed binary.

    Raises:
        ERPCError: If the platform is unsupported or checksum verification fails.

    Examples:
        >>> install_erpc("0.0.62")
        PosixPath('/usr/local/bin/erpc')

        >>> install_erpc("0.0.62", checksum="abc123...")
        PosixPath('/usr/local/bin/erpc')

    """
    artifact = get_platform_binary_name()
    url = f"{GITHUB_RELEASES_URL}/{version}/{artifact}"
    dest_dir = Path(install_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / binary_name

    logger.info("Downloading eRPC %s from %s", version, url)
    urllib.request.urlretrieve(url, str(dest))

    if checksum is not None:
        verify_checksum(dest, checksum)

    # Make executable
    dest.chmod(dest.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    logger.info("Installed eRPC %s to %s", version, dest)
    return dest
