"""Tests for install improvements: auto-install, CLI, and top-level export."""

from pathlib import Path
from unittest.mock import patch

import pytest


class TestAutoInstallOnFindBinary:
    """Test that find_erpc_binary() auto-installs when binary is not found."""

    @patch("erpc.process.shutil.which", return_value=None)
    @patch("erpc.process.os.access", return_value=False)
    @patch("erpc.process.os.path.isfile", return_value=False)
    @patch("erpc.process.os.environ.get", return_value=None)
    def test_auto_install_called_when_not_found(
        self, mock_env, mock_isfile, mock_access, mock_which
    ):
        from erpc.process import find_erpc_binary

        mock_path = Path("/usr/local/bin/erpc")
        with patch("erpc.install.install_erpc", return_value=mock_path) as mock_install:
            result = find_erpc_binary()
            assert result == "/usr/local/bin/erpc"
            mock_install.assert_called_once()

    @patch("erpc.process.shutil.which", return_value=None)
    @patch("erpc.process.os.access", return_value=False)
    @patch("erpc.process.os.path.isfile", return_value=False)
    @patch("erpc.process.os.environ.get", return_value=None)
    def test_auto_install_failure_raises_erpc_not_found(
        self, mock_env, mock_isfile, mock_access, mock_which
    ):
        from erpc.exceptions import ERPCNotFound
        from erpc.process import find_erpc_binary

        with (
            patch("erpc.install.install_erpc", side_effect=RuntimeError("download failed")),
            pytest.raises(ERPCNotFound),
        ):
            find_erpc_binary()

    @patch("erpc.process.shutil.which", return_value="/usr/bin/erpc")
    @patch("erpc.process.os.access", return_value=False)
    @patch("erpc.process.os.path.isfile", return_value=False)
    @patch("erpc.process.os.environ.get", return_value=None)
    def test_no_auto_install_when_binary_in_path(
        self, mock_env, mock_isfile, mock_access, mock_which
    ):
        from erpc.process import find_erpc_binary

        with patch("erpc.install.install_erpc") as mock_install:
            result = find_erpc_binary()
            assert result == "/usr/bin/erpc"
            mock_install.assert_not_called()


class TestCLI:
    """Test python -m erpc CLI."""

    @patch("erpc.install.install_erpc", return_value=Path("/usr/local/bin/erpc"))
    def test_install_command(self, mock_install, capsys):
        from erpc.__main__ import main

        with patch("sys.argv", ["erpc", "install", "--dir", "/tmp"]):
            main()
        out = capsys.readouterr().out
        assert "Installed eRPC to" in out
        mock_install.assert_called_once_with(install_dir="/tmp")

    @patch("erpc.version.get_erpc_version", return_value="0.0.62")
    def test_version_command(self, mock_version, capsys):
        from erpc.__main__ import main

        with patch("sys.argv", ["erpc", "version"]):
            main()
        out = capsys.readouterr().out
        assert "eRPC 0.0.62" in out

    @patch("erpc.version.get_erpc_version", return_value=None)
    def test_version_not_found(self, mock_version):
        from erpc.__main__ import main

        with patch("sys.argv", ["erpc", "version"]), pytest.raises(SystemExit, match="1"):
            main()

    def test_no_command_shows_help(self):
        from erpc.__main__ import main

        with patch("sys.argv", ["erpc"]), pytest.raises(SystemExit, match="1"):
            main()


class TestTopLevelExport:
    """Test that install_erpc is exported from top-level package."""

    def test_import_install_erpc(self):
        from erpc import install_erpc

        assert callable(install_erpc)
