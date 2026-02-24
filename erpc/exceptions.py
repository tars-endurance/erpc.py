"""erpc.py exception hierarchy."""


class ERPCError(Exception):
    """Base exception for erpc.py."""


class ERPCNotFound(ERPCError):
    """eRPC binary not found on PATH or at specified location."""


class ERPCNotRunning(ERPCError):
    """Operation requires a running eRPC process."""


class ERPCStartupError(ERPCError):
    """eRPC process failed to start."""


class ERPCHealthCheckError(ERPCError):
    """eRPC health check failed or timed out."""


class ERPCConfigError(ERPCError):
    """Invalid or malformed eRPC configuration."""
