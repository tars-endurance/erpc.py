"""Tests for the erpc CLI module."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, mock_open, patch

import yaml

if TYPE_CHECKING:
    import pytest

from erpc import __version__
from erpc.cli import build_parser


def _run_cli(*args: str) -> tuple[int, str, str]:
    """Run the CLI via subprocess and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        [sys.executable, "-m", "erpc.cli", *args],
        capture_output=True,
        text=True,
        timeout=10,
    )
    return result.returncode, result.stdout, result.stderr


class TestParser:
    """Tests for argparse parser construction."""

    def test_build_parser_returns_parser(self) -> None:
        parser = build_parser()
        assert parser.prog == "erpc-py"

    def test_no_subcommand_shows_help(self) -> None:
        rc, _stdout, _stderr = _run_cli()
        assert rc != 0

    def test_invalid_subcommand_shows_error(self) -> None:
        rc, _stdout, _stderr = _run_cli("nonexistent")
        assert rc != 0


class TestVersionCommand:
    """Tests for the 'version' subcommand."""

    def test_version_outputs_py_erpc_version(self) -> None:
        rc, stdout, _stderr = _run_cli("version")
        assert rc == 0
        assert __version__ in stdout

    @patch("erpc.cli.get_erpc_version", return_value="0.0.62")
    def test_version_shows_erpc_version(self, mock_ver: MagicMock) -> None:
        rc, stdout, _stderr = _run_cli("version")
        assert rc == 0
        assert __version__ in stdout


class TestHealthCommand:
    """Tests for the 'health' subcommand."""

    @patch("erpc.cli.urlopen")
    def test_health_healthy(self, mock_urlopen: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        parser = build_parser()
        args = parser.parse_args(["health", "--url", "http://localhost:4000"])
        rc = args.func(args)
        assert rc == 0

    @patch("erpc.cli.urlopen", side_effect=Exception("Connection refused"))
    def test_health_unhealthy(self, mock_urlopen: MagicMock) -> None:
        parser = build_parser()
        args = parser.parse_args(["health", "--url", "http://localhost:4000"])
        rc = args.func(args)
        assert rc == 1


class TestMetricsCommand:
    """Tests for the 'metrics' subcommand."""

    @patch("erpc.cli.urlopen")
    def test_metrics_success(self, mock_urlopen: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.read.return_value = b"# HELP erpc_requests_total\nerpc_requests_total 42\n"
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        parser = build_parser()
        args = parser.parse_args(["metrics", "--url", "http://localhost:4001/metrics"])
        rc = args.func(args)
        assert rc == 0

    @patch("erpc.cli.urlopen", side_effect=Exception("Connection refused"))
    def test_metrics_failure(self, mock_urlopen: MagicMock) -> None:
        parser = build_parser()
        args = parser.parse_args(["metrics", "--url", "http://localhost:4001/metrics"])
        rc = args.func(args)
        assert rc == 1


class TestConfigGenerateCommand:
    """Tests for the 'config generate' subcommand."""

    def test_config_generate_stdout(self, capsys: pytest.CaptureFixture[str]) -> None:
        parser = build_parser()
        args = parser.parse_args(
            [
                "config",
                "generate",
                "--chains",
                "1,137",
                "--upstreams",
                "https://eth.example.com,https://polygon.example.com",
            ]
        )
        rc = args.func(args)
        assert rc == 0
        captured = capsys.readouterr()
        doc = yaml.safe_load(captured.out)
        assert "projects" in doc

    def test_config_generate_to_file(self, tmp_path: Path) -> None:
        outfile = tmp_path / "erpc.yaml"
        parser = build_parser()
        args = parser.parse_args(
            [
                "config",
                "generate",
                "--chains",
                "1",
                "--upstreams",
                "https://eth.example.com",
                "--output",
                str(outfile),
            ]
        )
        rc = args.func(args)
        assert rc == 0
        assert outfile.exists()
        doc = yaml.safe_load(outfile.read_text())
        assert "projects" in doc


class TestInstallCommand:
    """Tests for the 'install' subcommand."""

    @patch("erpc.cli.install_erpc")
    def test_install_calls_install_erpc(self, mock_install: MagicMock) -> None:
        mock_install.return_value = Path("/usr/local/bin/erpc")
        parser = build_parser()
        args = parser.parse_args(["install", "--version", "0.0.62"])
        rc = args.func(args)
        assert rc == 0
        mock_install.assert_called_once_with(version="0.0.62", install_dir="/usr/local/bin")

    @patch("erpc.cli.install_erpc")
    def test_install_custom_dir(self, mock_install: MagicMock) -> None:
        mock_install.return_value = Path("/opt/bin/erpc")
        parser = build_parser()
        args = parser.parse_args(["install", "--version", "0.0.62", "--dir", "/opt/bin"])
        rc = args.func(args)
        assert rc == 0
        mock_install.assert_called_once_with(version="0.0.62", install_dir="/opt/bin")


class TestStartCommand:
    """Tests for the 'start' subcommand."""

    @patch("erpc.cli.subprocess.Popen")
    @patch("erpc.cli.find_erpc_binary", return_value="/usr/local/bin/erpc")
    def test_start_with_config(
        self, mock_find: MagicMock, mock_popen: MagicMock, tmp_path: Path
    ) -> None:
        config_file = tmp_path / "erpc.yaml"
        config_file.write_text("logLevel: warn\n")
        mock_proc = MagicMock()
        mock_proc.pid = 12345
        mock_popen.return_value = mock_proc

        parser = build_parser()
        args = parser.parse_args(["start", "--config", str(config_file)])
        with patch("builtins.open", mock_open()):
            rc = args.func(args)
        assert rc == 0

    def test_start_missing_config_file(self, tmp_path: Path) -> None:
        parser = build_parser()
        args = parser.parse_args(["start", "--config", str(tmp_path / "nope.yaml")])
        rc = args.func(args)
        assert rc == 1


class TestStopCommand:
    """Tests for the 'stop' subcommand."""

    def test_stop_reads_pid_file(self, tmp_path: Path) -> None:
        pid_file = tmp_path / "erpc-py.pid"
        pid_file.write_text("99999")

        parser = build_parser()
        args = parser.parse_args(["stop"])

        with patch("erpc.cli.PID_FILE", str(pid_file)), patch("os.kill") as mock_kill:
            mock_kill.side_effect = ProcessLookupError
            rc = args.func(args)
        # Process not found is still a clean exit
        assert rc == 0

    def test_stop_no_pid_file(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["stop"])
        with patch("erpc.cli.PID_FILE", "/tmp/nonexistent-erpc-test.pid"):
            rc = args.func(args)
        assert rc == 1
