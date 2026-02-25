"""Tests for eRPC config generation."""

import yaml

from erpc.config import CacheConfig, ERPCConfig


def test_default_config():
    config = ERPCConfig(upstreams={1: ["https://eth.example.com"]})
    assert config.server_host == "127.0.0.1"
    assert config.server_port == 4000
    assert config.project_id == "py-erpc"


def test_health_url():
    config = ERPCConfig()
    assert config.health_url == "http://127.0.0.1:4000/"


def test_endpoint_url():
    config = ERPCConfig(project_id="test")
    assert config.endpoint_url(1) == "http://127.0.0.1:4000/test/evm/1"
    assert config.endpoint_url(137) == "http://127.0.0.1:4000/test/evm/137"


def test_to_yaml_structure():
    config = ERPCConfig(
        project_id="my-project",
        upstreams={
            1: ["https://eth-rpc-1.example.com", "https://eth-rpc-2.example.com"],
            137: ["https://polygon-rpc.example.com"],
        },
    )
    content = config.to_yaml()
    doc = yaml.safe_load(content)

    assert doc["logLevel"] == "warn"
    assert doc["server"]["httpHostV4"] == "127.0.0.1"
    assert doc["server"]["httpPort"] == 4000
    assert len(doc["projects"]) == 1

    project = doc["projects"][0]
    assert project["id"] == "my-project"
    assert len(project["networks"]) == 2


def test_to_yaml_upstreams():
    config = ERPCConfig(
        upstreams={1: ["https://rpc-1.example.com", "https://rpc-2.example.com"]},
    )
    doc = yaml.safe_load(config.to_yaml())
    project = doc["projects"][0]
    upstreams = project["upstreams"]

    assert len(upstreams) == 2
    assert upstreams[0]["endpoint"] == "https://rpc-1.example.com"
    assert upstreams[0]["evm"]["chainId"] == 1


def test_cache_config():
    config = ERPCConfig(
        upstreams={1: ["https://rpc.example.com"]},
        cache=CacheConfig(max_items=5000),
    )
    # cacheConfig is no longer emitted in the new schema;
    # cache is handled at the database level. Verify no crash.
    doc = yaml.safe_load(config.to_yaml())
    assert doc["projects"][0]["id"] == "py-erpc"


def test_cache_config_defaults():
    cache = CacheConfig()
    assert cache.max_items == 10_000
    assert cache.method_ttls == {}


def test_no_cache_config_when_zero_items():
    config = ERPCConfig(
        upstreams={1: ["https://rpc.example.com"]},
        cache=CacheConfig(max_items=0),
    )
    doc = yaml.safe_load(config.to_yaml())
    assert "cacheConfig" not in doc["projects"][0]


def test_method_ttl_overrides():
    config = ERPCConfig(
        upstreams={1: ["https://rpc.example.com"]},
        cache=CacheConfig(
            method_ttls={"eth_call": 0, "eth_getLogs": 2},
        ),
    )
    doc = yaml.safe_load(config.to_yaml())

    # Policies now live under top-level database.evmJsonRpcCache
    assert "database" in doc
    cache_section = doc["database"]["evmJsonRpcCache"]
    policies = cache_section["policies"]

    # 2 default policies + 2 method overrides
    assert len(policies) == 4

    eth_call_policy = next(p for p in policies if p["method"] == "eth_call")
    assert eth_call_policy["ttl"] == "0s"

    eth_logs_policy = next(p for p in policies if p["method"] == "eth_getLogs")
    assert eth_logs_policy["ttl"] == "2s"


def test_write_to_path(tmp_path):
    config = ERPCConfig(upstreams={1: ["https://rpc.example.com"]})
    path = config.write(tmp_path / "erpc.yaml")
    assert path.exists()
    doc = yaml.safe_load(path.read_text())
    assert doc["projects"][0]["id"] == "py-erpc"


def test_write_to_nested_path(tmp_path):
    config = ERPCConfig(upstreams={1: ["https://rpc.example.com"]})
    path = config.write(tmp_path / "sub" / "dir" / "erpc.yaml")
    assert path.exists()


def test_write_to_temp():
    config = ERPCConfig(upstreams={1: ["https://rpc.example.com"]})
    path = config.write()
    assert path.exists()
    assert path.suffix == ".yaml"
    path.unlink()  # cleanup


def test_custom_ports():
    config = ERPCConfig(server_port=8080, metrics_port=8081)
    doc = yaml.safe_load(config.to_yaml())
    assert doc["server"]["httpPort"] == 8080
    assert doc["metrics"]["port"] == 8081


# --- Database cache config tests ---


def test_no_database_without_cache():
    """ERPCConfig without method_ttls should not emit database section."""
    config = ERPCConfig(upstreams={1: ["https://rpc.example.com"]})
    doc = yaml.safe_load(config.to_yaml())
    assert "database" not in doc


def test_database_auto_generated_from_method_ttls():
    """method_ttls should auto-generate top-level database with evmJsonRpcCache."""
    config = ERPCConfig(
        upstreams={1: ["https://rpc.example.com"]},
        cache=CacheConfig(max_items=100_000, method_ttls={"eth_call": 0}),
    )
    doc = yaml.safe_load(config.to_yaml())
    assert "database" in doc
    cache_section = doc["database"]["evmJsonRpcCache"]

    # Connector
    connectors = cache_section["connectors"]
    assert len(connectors) == 1
    assert connectors[0]["id"] == "memory-cache"
    assert connectors[0]["driver"] == "memory"
    assert connectors[0]["memory"]["maxItems"] == 100_000

    # Default policies
    policies = cache_section["policies"]
    finalized = next(p for p in policies if p["finality"] == "finalized" and p["method"] == "*")
    assert str(finalized["ttl"]) == "0"

    unfinalized = next(
        p for p in policies if p["finality"] == "unfinalized" and p["method"] == "*"
    )
    assert unfinalized["ttl"] == "5s"


def test_method_ttl_zero_produces_0s():
    """TTL=0 should emit ttl: 0s for the method override."""
    config = ERPCConfig(
        upstreams={1: ["https://rpc.example.com"]},
        cache=CacheConfig(method_ttls={"eth_call": 0}),
    )
    doc = yaml.safe_load(config.to_yaml())
    policies = doc["database"]["evmJsonRpcCache"]["policies"]
    eth_call = next(p for p in policies if p["method"] == "eth_call")
    assert eth_call["ttl"] == "0s"
    assert eth_call["finality"] == "unfinalized"


def test_explicit_database_overrides_auto():
    """Explicit DatabaseConfig should take precedence over auto-generation."""
    from erpc.database import CachePolicy as DBCachePolicy
    from erpc.database import DatabaseConfig, MemoryConnector

    db = DatabaseConfig(
        connectors=[MemoryConnector(id="custom", max_items=5000)],
        policies=[DBCachePolicy(connector="custom", ttl="60s", finality="finalized")],
    )
    config = ERPCConfig(
        upstreams={1: ["https://rpc.example.com"]},
        cache=CacheConfig(method_ttls={"eth_call": 0}),
        database=db,
    )
    doc = yaml.safe_load(config.to_yaml())
    connectors = doc["database"]["evmJsonRpcCache"]["connectors"]
    assert connectors[0]["id"] == "custom"


def test_database_not_under_project():
    """database should be at top level, not under projects."""
    config = ERPCConfig(
        upstreams={1: ["https://rpc.example.com"]},
        cache=CacheConfig(method_ttls={"eth_call": 0}),
    )
    doc = yaml.safe_load(config.to_yaml())
    assert "database" not in doc["projects"][0]
    assert "database" in doc


def test_database_round_trip():
    """Generate YAML with database, parse back, verify structure."""
    config = ERPCConfig(
        upstreams={1: ["https://rpc.example.com"]},
        cache=CacheConfig(max_items=50_000, method_ttls={"eth_getBalance": 10}),
    )
    yaml_str = config.to_yaml()
    doc = yaml.safe_load(yaml_str)

    db = doc["database"]["evmJsonRpcCache"]
    assert len(db["connectors"]) == 1
    assert len(db["policies"]) == 3  # 2 defaults + 1 override
    assert db["connectors"][0]["memory"]["maxItems"] == 50_000

    override = next(p for p in db["policies"] if p["method"] == "eth_getBalance")
    assert override["ttl"] == "10s"
