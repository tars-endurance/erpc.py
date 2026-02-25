"""Tests for eRPC database/cache configuration."""

from __future__ import annotations

import pytest

from erpc.database import (
    CachePolicy,
    CompressionConfig,
    DatabaseConfig,
    DynamoDBConnector,
    MemoryConnector,
    PostgresConnector,
    RedisConnector,
    TLSConfig,
)


class TestTLSConfig:
    """TLS certificate configuration tests."""

    def test_construction(self) -> None:
        tls = TLSConfig(
            cert_file="/certs/client.crt",
            key_file="/certs/client.key",
            ca_file="/certs/ca.crt",
        )
        assert tls.cert_file == "/certs/client.crt"
        assert tls.key_file == "/certs/client.key"
        assert tls.ca_file == "/certs/ca.crt"

    def test_to_dict(self) -> None:
        tls = TLSConfig(cert_file="/c.crt", key_file="/c.key", ca_file="/ca.crt")
        expected = {
            "certFile": "/c.crt",
            "keyFile": "/c.key",
            "caFile": "/ca.crt",
        }
        assert tls.to_dict() == expected


class TestMemoryConnector:
    """Memory connector tests."""

    def test_construction(self) -> None:
        conn = MemoryConnector(id="mem1", max_items=50_000)
        assert conn.id == "mem1"
        assert conn.max_items == 50_000

    def test_to_dict(self) -> None:
        conn = MemoryConnector(id="mem1", max_items=10_000)
        result = conn.to_dict()
        assert result == {
            "id": "mem1",
            "driver": "memory",
            "memory": {"maxItems": 10_000},
        }


class TestRedisConnector:
    """Redis connector tests."""

    def test_construction_minimal(self) -> None:
        conn = RedisConnector(id="redis1", uri="redis://localhost:6379")
        assert conn.id == "redis1"
        assert conn.uri == "redis://localhost:6379"
        assert conn.tls is None
        assert conn.pool_size is None

    def test_construction_with_tls(self) -> None:
        tls = TLSConfig(cert_file="/c.crt", key_file="/c.key", ca_file="/ca.crt")
        conn = RedisConnector(
            id="redis-tls",
            uri="rediss://redis.example.com:6380",
            tls=tls,
            pool_size=20,
        )
        assert conn.tls is not None
        assert conn.pool_size == 20

    def test_to_dict_with_tls(self) -> None:
        tls = TLSConfig(cert_file="/c.crt", key_file="/c.key", ca_file="/ca.crt")
        conn = RedisConnector(id="r1", uri="rediss://host:6380", tls=tls, pool_size=10)
        result = conn.to_dict()
        assert result["driver"] == "redis"
        assert result["redis"]["uri"] == "rediss://host:6380"
        assert result["redis"]["tls"] == {
            "certFile": "/c.crt",
            "keyFile": "/c.key",
            "caFile": "/ca.crt",
        }
        assert result["redis"]["poolSize"] == 10

    def test_to_dict_minimal(self) -> None:
        conn = RedisConnector(id="r1", uri="redis://localhost:6379")
        result = conn.to_dict()
        assert "tls" not in result["redis"]
        assert "poolSize" not in result["redis"]


class TestPostgresConnector:
    """PostgreSQL connector tests."""

    def test_construction(self) -> None:
        conn = PostgresConnector(
            id="pg1",
            uri="postgres://user:pass@host:5432/db",
            table="rpc_cache",
        )
        assert conn.table == "rpc_cache"

    def test_to_dict(self) -> None:
        conn = PostgresConnector(id="pg1", uri="postgres://host/db", table="cache")
        result = conn.to_dict()
        assert result == {
            "id": "pg1",
            "driver": "postgresql",
            "postgresql": {
                "connectionUri": "postgres://host/db",
                "table": "cache",
            },
        }


class TestDynamoDBConnector:
    """DynamoDB connector tests."""

    def test_construction(self) -> None:
        conn = DynamoDBConnector(
            id="ddb1",
            table="erpc_cache",
            region="us-east-1",
            partition_key_name="pk",
            range_key_name="sk",
            ttl_attribute="ttl",
        )
        assert conn.region == "us-east-1"

    def test_to_dict(self) -> None:
        conn = DynamoDBConnector(
            id="ddb1",
            table="cache",
            region="eu-west-1",
            partition_key_name="pk",
            range_key_name="rk",
            ttl_attribute="expiry",
        )
        result = conn.to_dict()
        assert result == {
            "id": "ddb1",
            "driver": "dynamodb",
            "dynamodb": {
                "table": "cache",
                "region": "eu-west-1",
                "partitionKeyName": "pk",
                "rangeKeyName": "rk",
                "ttlAttribute": "expiry",
            },
        }


class TestCompressionConfig:
    """Compression configuration tests."""

    def test_defaults(self) -> None:
        comp = CompressionConfig()
        assert comp.algorithm == "zstd"
        assert comp.level == "default"
        assert comp.threshold == 1024

    def test_custom(self) -> None:
        comp = CompressionConfig(algorithm="gzip", level="best", threshold=512)
        assert comp.algorithm == "gzip"

    def test_to_dict(self) -> None:
        comp = CompressionConfig()
        assert comp.to_dict() == {
            "algorithm": "zstd",
            "level": "default",
            "threshold": 1024,
        }


class TestCachePolicy:
    """Cache policy tests."""

    @pytest.mark.parametrize(
        "finality",
        ["finalized", "unfinalized", "realtime", "unknown"],
    )
    def test_finality_states(self, finality: str) -> None:
        policy = CachePolicy(connector="mem1", ttl="30s", finality=finality)
        assert policy.finality == finality

    @pytest.mark.parametrize("empty", ["ignore", "allow", "only"])
    def test_empty_states(self, empty: str) -> None:
        policy = CachePolicy(connector="mem1", ttl="10s", empty=empty)
        assert policy.empty == empty

    def test_minimal_to_dict(self) -> None:
        policy = CachePolicy(connector="mem1", ttl="60s")
        result = policy.to_dict()
        assert result == {"connector": "mem1", "ttl": "60s"}

    def test_full_to_dict(self) -> None:
        policy = CachePolicy(
            connector="redis1",
            ttl="300s",
            network="evm:1",
            method="eth_getBlockByNumber",
            finality="finalized",
            empty="ignore",
            min_item_size=100,
            max_item_size=1_000_000,
        )
        result = policy.to_dict()
        assert result == {
            "connector": "redis1",
            "ttl": "300s",
            "network": "evm:1",
            "method": "eth_getBlockByNumber",
            "finality": "finalized",
            "empty": "ignore",
            "minItemSize": 100,
            "maxItemSize": 1_000_000,
        }


class TestDatabaseConfig:
    """DatabaseConfig composition tests."""

    def test_multiple_connectors_and_policies(self) -> None:
        mem = MemoryConnector(id="mem1", max_items=10_000)
        redis = RedisConnector(id="redis1", uri="redis://localhost:6379")
        policy1 = CachePolicy(connector="mem1", ttl="30s", finality="realtime")
        policy2 = CachePolicy(connector="redis1", ttl="3600s", finality="finalized")
        db = DatabaseConfig(connectors=[mem, redis], policies=[policy1, policy2])
        assert len(db.connectors) == 2
        assert len(db.policies) == 2

    def test_with_compression(self) -> None:
        db = DatabaseConfig(
            connectors=[MemoryConnector(id="m", max_items=1000)],
            policies=[CachePolicy(connector="m", ttl="10s")],
            compression=CompressionConfig(),
        )
        assert db.compression is not None

    def test_to_dict(self) -> None:
        mem = MemoryConnector(id="mem1", max_items=5000)
        policy = CachePolicy(connector="mem1", ttl="60s", finality="unfinalized")
        comp = CompressionConfig(algorithm="zstd", level="fast", threshold=2048)
        db = DatabaseConfig(connectors=[mem], policies=[policy], compression=comp)
        result = db.to_dict()
        assert result == {
            "connectors": [
                {
                    "id": "mem1",
                    "driver": "memory",
                    "memory": {"maxItems": 5000},
                },
            ],
            "policies": [
                {
                    "connector": "mem1",
                    "ttl": "60s",
                    "finality": "unfinalized",
                },
            ],
            "compression": {
                "algorithm": "zstd",
                "level": "fast",
                "threshold": 2048,
            },
        }

    def test_to_dict_no_compression(self) -> None:
        db = DatabaseConfig(
            connectors=[MemoryConnector(id="m", max_items=100)],
            policies=[CachePolicy(connector="m", ttl="5s")],
        )
        result = db.to_dict()
        assert "compression" not in result


class TestERPCConfigIntegration:
    """Integration with ERPCConfig."""

    def test_erpc_config_with_database(self) -> None:
        from erpc.config import ERPCConfig

        db = DatabaseConfig(
            connectors=[MemoryConnector(id="mem", max_items=10_000)],
            policies=[CachePolicy(connector="mem", ttl="30s", finality="finalized")],
        )
        config = ERPCConfig(
            upstreams={1: ["https://eth.llamarpc.com"]},
            database=db,
        )
        yaml_str = config.to_yaml()
        assert "connectors" in yaml_str
        assert "mem" in yaml_str
