"""eRPC version detection."""

from __future__ import annotations

import subprocess
from typing import Optional

from erpc.process import find_erpc_binary


def get_erpc_version(binary_path: Optional[str] = None) -> Optional[str]:
    """Get the installed eRPC version string.

    Returns None if the binary is not found or version cannot be determined.
    """
    try:
        binary = find_erpc_binary(binary_path)
        result = subprocess.run(
            [binary, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip() or result.stderr.strip() or None
    except Exception:
        return None
