"""eRPC version detection."""

from __future__ import annotations

import subprocess

from erpc.process import find_erpc_binary


def get_erpc_version(binary_path: str | None = None) -> str | None:
    """Get the installed eRPC version string.

    Args:
        binary_path: Explicit path to the eRPC binary. Auto-detected if ``None``.

    Returns:
        Version string, or ``None`` if the binary is not found or version
        cannot be determined.

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
        return result.stdout.strip() or result.stderr.strip() or None
    except Exception:
        return None
