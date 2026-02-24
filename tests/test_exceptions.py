"""Tests for erpc.py exception hierarchy."""

from erpc.exceptions import (
    ERPCError,
    ERPCHealthCheckError,
    ERPCNotFound,
    ERPCNotRunning,
    ERPCStartupError,
)


def test_exception_hierarchy():
    assert issubclass(ERPCNotFound, ERPCError)
    assert issubclass(ERPCNotRunning, ERPCError)
    assert issubclass(ERPCStartupError, ERPCError)
    assert issubclass(ERPCHealthCheckError, ERPCError)
    assert issubclass(ERPCError, Exception)


def test_exception_messages():
    err = ERPCNotFound("not found")
    assert str(err) == "not found"

    err = ERPCStartupError("failed")
    assert str(err) == "failed"
