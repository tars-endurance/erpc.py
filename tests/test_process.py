"""Tests for eRPC process management."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from erpc.exceptions import ERPCNotFound, ERPCNotRunning, ERPCStartupError
from erpc.process import ERPCProcess, find_erpc_binary


class TestFindBinary:
    def test_explicit_path(self, tmp_path):
        binary = tmp_path / "erpc"
        binary.write_text("#!/bin/bash")
        binary.chmod(0o755)
        assert find_erpc_binary(str(binary)) == str(binary)

    def test_env_var(self, tmp_path, monkeypatch):
        binary = tmp_path / "erpc"
        binary.write_text("#!/bin/bash")
        binary.chmod(0o755)
        monkeypatch.setenv("ERPC_BINARY", str(binary))
        assert find_erpc_binary() == str(binary)

    def test_not_found(self, monkeypatch):
        monkeypatch.delenv("ERPC_BINARY", raising=False)
        with patch("shutil.which", return_value=None), \
             patch("os.path.isfile", return_value=False):
            with pytest.raises(ERPCNotFound):
                find_erpc_binary("/nonexistent/erpc")

    def test_which_fallback(self, monkeypatch):
        monkeypatch.delenv("ERPC_BINARY", raising=False)
        with patch("shutil.which", return_value="/usr/bin/erpc"), \
             patch("os.path.isfile", return_value=False):
            assert find_erpc_binary() == "/usr/bin/erpc"


class TestERPCProcess:
    def test_requires_config_or_upstreams(self):
        with pytest.raises(ValueError, match="Provide either"):
            ERPCProcess()

    def test_upstreams_shortcut(self, tmp_path):
        binary = tmp_path / "erpc"
        binary.write_text("#!/bin/bash")
        binary.chmod(0o755)
        proc = ERPCProcess(
            upstreams={1: ["https://rpc.example.com"]},
            binary_path=str(binary),
        )
        assert proc.config.upstreams[1] == ["https://rpc.example.com"]

    def test_endpoint_url(self, tmp_path):
        binary = tmp_path / "erpc"
        binary.write_text("#!/bin/bash")
        binary.chmod(0o755)
        proc = ERPCProcess(
            upstreams={1: ["https://rpc.example.com"]},
            binary_path=str(binary),
        )
        assert "evm/1" in proc.endpoint_url(1)

    def test_not_running_initially(self, tmp_path):
        binary = tmp_path / "erpc"
        binary.write_text("#!/bin/bash")
        binary.chmod(0o755)
        proc = ERPCProcess(
            upstreams={1: ["https://rpc.example.com"]},
            binary_path=str(binary),
        )
        assert not proc.is_running
        assert proc.pid is None

    def test_stop_when_not_running(self, tmp_path):
        binary = tmp_path / "erpc"
        binary.write_text("#!/bin/bash")
        binary.chmod(0o755)
        proc = ERPCProcess(
            upstreams={1: ["https://rpc.example.com"]},
            binary_path=str(binary),
        )
        with pytest.raises(ERPCNotRunning):
            proc.stop()
