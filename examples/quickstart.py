#!/usr/bin/env python3
"""Quick start example — proxy Ethereum mainnet through eRPC.

Uses a free public RPC endpoint with default settings.
eRPC binary must be installed (``pip install erpc-py && erpc install``
or ``from erpc import install_erpc; install_erpc()``).

Usage:
    python examples/quickstart.py
"""

from __future__ import annotations

import json
import urllib.request

from erpc import ERPC_VERSION, ERPCConfig, ERPCProcess


def jsonrpc(url: str, method: str, params: list | None = None) -> dict:
    """Send a JSON-RPC request and return the result."""
    payload = json.dumps(
        {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or [],
            "id": 1,
        }
    ).encode()
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def main() -> None:
    """Run the quickstart example — proxy Ethereum mainnet through eRPC."""
    print(f"erpc.py — targeting eRPC v{ERPC_VERSION}\n")

    # Start eRPC proxying Ethereum mainnet via a free public endpoint
    config = ERPCConfig(
        upstreams={1: ["https://eth.llamarpc.com"]},
        server_port=4400,
        metrics_port=4401,
    )
    with ERPCProcess(config=config) as erpc:
        url = erpc.endpoint_url(1)
        print(f"✓ eRPC running — proxying chain 1 at {url}")
        print(f"  Health: {erpc.config.health_url}")
        print()

        # Query latest block number
        result = jsonrpc(url, "eth_blockNumber")
        block_hex = result["result"]
        block_num = int(block_hex, 16)
        print(f"  eth_blockNumber: {block_hex} ({block_num:,})")

        # Query chain ID
        result = jsonrpc(url, "eth_chainId")
        chain_id = int(result["result"], 16)
        print(f"  eth_chainId:     {chain_id}")

        # Query gas price
        result = jsonrpc(url, "eth_gasPrice")
        gas_wei = int(result["result"], 16)
        gas_gwei = gas_wei / 1e9
        print(f"  eth_gasPrice:    {gas_gwei:.2f} gwei")

        print("\n✓ All queries proxied successfully through eRPC")


if __name__ == "__main__":
    main()
