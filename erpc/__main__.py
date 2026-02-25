"""CLI entry point for erpc-py: ``python -m erpc install``."""

import argparse
import sys


def main() -> None:
    """Run the erpc-py CLI."""
    parser = argparse.ArgumentParser(prog="python -m erpc", description="erpc-py CLI")
    sub = parser.add_subparsers(dest="command")

    install_parser = sub.add_parser("install", help="Download and install the eRPC binary")
    install_parser.add_argument("--version", help="eRPC version to install")
    install_parser.add_argument("--dir", default="/usr/local/bin", help="Installation directory")

    sub.add_parser("version", help="Show installed eRPC binary version")

    args = parser.parse_args()

    if args.command == "install":
        from erpc.install import install_erpc

        kwargs = {}
        if args.version:
            kwargs["version"] = args.version
        if args.dir:
            kwargs["install_dir"] = args.dir
        path = install_erpc(**kwargs)
        print(f"Installed eRPC to {path}")
    elif args.command == "version":
        from erpc.version import get_erpc_version

        v = get_erpc_version()
        if v:
            print(f"eRPC {v}")
        else:
            print("eRPC binary not found", file=sys.stderr)
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
