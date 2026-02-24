"""eRPC version detection.

Detects the version of an installed eRPC binary by parsing its
``--version`` output.
"""

from __future__ import annotations

import re
import subprocess

from erpc.process import find_erpc_binary

_VERSION_PATTERN = re.compile(r"v?(\d+\.\d+\.\d+(?:[a-zA-Z0-9._+-]*))")
"""Regex to extract a semver-like version from eRPC output."""


def _parse_version(raw: str) -> str | None:
    """Extract a clean version string from raw eRPC output.

    Handles formats like ``"erpc version 0.0.62"``, ``"v0.0.62"``,
    or bare ``"0.0.62"``.

    Args:
        raw: Raw output string from the eRPC binary.

    Returns:
        Cleaned version string, or ``None`` if no version found.

    """
    match = _VERSION_PATTERN.search(raw)
    return match.group(1) if match else None


def get_erpc_version(binary_path: str | None = None) -> str | None:
    """Get the installed eRPC version string.

    Args:
        binary_path: Explicit path to the eRPC binary. Auto-detected if ``None``.

    Returns:
        Version string (e.g., ``"0.0.62"``), or ``None`` if the binary is
        not found or version cannot be determined.

    Examples:
        >>> get_erpc_version()
        '0.0.62'

        >>> get_erpc_version("/custom/path/erpc")
        '0.0.62'

    """
    try:
        binary = find_erpc_binary(binary_path)
        result = subprocess.run(
            [binary, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        output = result.stdout.strip() or result.stderr.strip()
        if not output:
            return None
        return _parse_version(output)
    except Exception:
        return None
