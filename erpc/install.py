"""eRPC binary installation helpers.

Inspired by `py-geth <https://github.com/ethereum/py-geth>`_'s install module.
"""

from __future__ import annotations

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

    """
    key = (platform.system(), platform.machine())
    if key not in PLATFORM_MAP:
        raise ERPCError(f"Unsupported platform: {platform.system()} {platform.machine()}")
    return PLATFORM_MAP[key]


def install_erpc(
    version: str,
    install_dir: str = "/usr/local/bin",
    binary_name: str = "erpc",
) -> Path:
    """Download and install eRPC binary from GitHub releases.

    Args:
        version: Release version tag (e.g., ``"0.0.62"``).
        install_dir: Directory to install the binary.
        binary_name: Name for the installed binary.

    Returns:
        Path to the installed binary.

    """
    artifact = get_platform_binary_name()
    url = f"{GITHUB_RELEASES_URL}/{version}/{artifact}"
    dest = Path(install_dir) / binary_name

    logger.info("Downloading eRPC %s from %s", version, url)
    urllib.request.urlretrieve(url, str(dest))

    # Make executable
    dest.chmod(dest.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    logger.info("Installed eRPC %s to %s", version, dest)
    return dest
