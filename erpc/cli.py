"""Command-line interface for erpc.py.

Provides ``erpc-py`` CLI with subcommands for managing eRPC instances.
"""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
from pathlib import Path
from urllib.request import urlopen

from erpc import __version__
from erpc.config import ERPCConfig
from erpc.install import install_erpc
from erpc.process import find_erpc_binary
from erpc.version import get_erpc_version

PID_FILE = "/tmp/erpc-py.pid"
"""Default PID file path for process tracking."""

DEFAULT_HEALTH_URL = "http://127.0.0.1:4000/"
"""Default URL for health checks."""

DEFAULT_METRICS_URL = "http://127.0.0.1:4001/metrics"
"""Default URL for metrics endpoint."""


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the erpc-py CLI.

    Returns:
        Configured argument parser with all subcommands.

    """
    parser = argparse.ArgumentParser(
        prog="erpc-py",
        description="Python CLI for managing eRPC — fault-tolerant EVM RPC proxy",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # ── version ───────────────────────────────────────────────────────────
    version_parser = subparsers.add_parser("version", help="Show version information")
    version_parser.set_defaults(func=_cmd_version)

    # ── health ────────────────────────────────────────────────────────────
    health_parser = subparsers.add_parser("health", help="Check eRPC health status")
    health_parser.add_argument("--url", default=DEFAULT_HEALTH_URL, help="Health endpoint URL")
    health_parser.set_defaults(func=_cmd_health)

    # ── metrics ───────────────────────────────────────────────────────────
    metrics_parser = subparsers.add_parser("metrics", help="Display runtime metrics")
    metrics_parser.add_argument("--url", default=DEFAULT_METRICS_URL, help="Metrics endpoint URL")
    metrics_parser.set_defaults(func=_cmd_metrics)

    # ── config ────────────────────────────────────────────────────────────
    config_parser = subparsers.add_parser("config", help="Configuration management")
    config_sub = config_parser.add_subparsers(dest="config_command", required=True)

    gen_parser = config_sub.add_parser("generate", help="Generate eRPC config file")
    gen_parser.add_argument(
        "--chains", required=True, help="Comma-separated chain IDs (e.g., 1,137)"
    )
    gen_parser.add_argument("--upstreams", required=True, help="Comma-separated upstream URLs")
    gen_parser.add_argument("--output", help="Output file path (default: stdout)")
    gen_parser.set_defaults(func=_cmd_config_generate)

    # ── install ───────────────────────────────────────────────────────────
    install_parser = subparsers.add_parser("install", help="Install eRPC binary")
    install_parser.add_argument("--version", required=True, help="eRPC version to install")
    install_parser.add_argument("--dir", default="/usr/local/bin", help="Installation directory")
    install_parser.set_defaults(func=_cmd_install)

    # ── start ─────────────────────────────────────────────────────────────
    start_parser = subparsers.add_parser("start", help="Start eRPC with config")
    start_parser.add_argument("--config", required=True, help="Path to eRPC config file")
    start_parser.add_argument("--port", type=int, help="Override server port")
    start_parser.set_defaults(func=_cmd_start)

    # ── stop ──────────────────────────────────────────────────────────────
    stop_parser = subparsers.add_parser("stop", help="Gracefully stop eRPC")
    stop_parser.set_defaults(func=_cmd_stop)

    return parser


def _cmd_version(args: argparse.Namespace) -> int:
    """Handle the 'version' subcommand."""
    print(f"erpc-py {__version__}")
    erpc_ver = get_erpc_version()
    if erpc_ver:
        print(f"eRPC    {erpc_ver}")
    else:
        print("eRPC    not found")
    return 0


def _cmd_health(args: argparse.Namespace) -> int:
    """Handle the 'health' subcommand."""
    try:
        with urlopen(args.url, timeout=5):
            print(f"✓ eRPC is healthy ({args.url})")
            return 0
    except Exception:
        print(f"✗ eRPC is not reachable ({args.url})", file=sys.stderr)
        return 1


def _cmd_metrics(args: argparse.Namespace) -> int:
    """Handle the 'metrics' subcommand."""
    try:
        with urlopen(args.url, timeout=5) as resp:
            print(resp.read().decode(errors="replace"))
            return 0
    except Exception:
        print(f"✗ Could not fetch metrics ({args.url})", file=sys.stderr)
        return 1


def _cmd_config_generate(args: argparse.Namespace) -> int:
    """Handle the 'config generate' subcommand."""
    chain_ids = [int(c.strip()) for c in args.chains.split(",")]
    upstream_urls = [u.strip() for u in args.upstreams.split(",")]

    upstreams: dict[int, list[str]] = {}
    for i, chain_id in enumerate(chain_ids):
        url = upstream_urls[i] if i < len(upstream_urls) else upstream_urls[-1]
        upstreams[chain_id] = [url]

    config = ERPCConfig(upstreams=upstreams)
    yaml_content = config.to_yaml()

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(yaml_content)
        print(f"Config written to {output_path}")
    else:
        print(yaml_content, end="")

    return 0


def _cmd_install(args: argparse.Namespace) -> int:
    """Handle the 'install' subcommand."""
    try:
        path = install_erpc(version=args.version, install_dir=args.dir)
        print(f"✓ Installed eRPC {args.version} to {path}")
        return 0
    except Exception as e:
        print(f"✗ Installation failed: {e}", file=sys.stderr)
        return 1


def _cmd_start(args: argparse.Namespace) -> int:
    """Handle the 'start' subcommand."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"✗ Config file not found: {config_path}", file=sys.stderr)
        return 1

    try:
        binary = find_erpc_binary()
    except Exception as e:
        print(f"✗ {e}", file=sys.stderr)
        return 1

    cmd = [binary, str(config_path)]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    with open(PID_FILE, "w") as f:
        f.write(str(proc.pid))

    print(f"✓ eRPC started (PID {proc.pid})")
    return 0


def _cmd_stop(args: argparse.Namespace) -> int:
    """Handle the 'stop' subcommand."""
    pid_path = Path(PID_FILE)
    if not pid_path.exists():
        print("✗ No PID file found — is eRPC running?", file=sys.stderr)
        return 1

    pid = int(pid_path.read_text().strip())
    try:
        os.kill(pid, signal.SIGTERM)
        print(f"✓ Sent SIGTERM to eRPC (PID {pid})")
    except ProcessLookupError:
        print(f"✓ Process {pid} already stopped")
    except PermissionError:
        print(f"✗ Permission denied stopping PID {pid}", file=sys.stderr)
        return 1
    finally:
        pid_path.unlink(missing_ok=True)

    return 0


def main() -> None:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args()
    rc = args.func(args)
    sys.exit(rc)


if __name__ == "__main__":
    main()
