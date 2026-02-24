"""eRPC database and cache configuration.

Provides dataclasses for configuring eRPC's caching layer, including
multiple storage backends (memory, Redis, PostgreSQL, DynamoDB),
cache policies with finality awareness, and compression settings.

Examples:
    >>> from erpc.database import DatabaseConfig, MemoryConnector, CachePolicy
    >>> db = DatabaseConfig(
    ...     connectors=[MemoryConnector(id="mem", max_items=10_000)],
    ...     policies=[CachePolicy(connector="mem", ttl="30s")],
    ... )
    >>> db.to_dict()["connectors"][0]["driver"]
    'memory'

"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


class Connector(Protocol):
    """Protocol for database connector types."""

    id: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize connector to eRPC config dict."""
        ...  # pragma: no cover


@dataclass
class TLSConfig:
    """TLS certificate configuration for secure connections.

    Args:
        cert_file: Path to the client certificate file.
        key_file: Path to the client key file.
        ca_file: Path to the CA certificate file.

    """

    cert_file: str
    key_file: str
    ca_file: str

    def to_dict(self) -> dict[str, str]:
        """Serialize to eRPC config dict.

        Returns:
            Dict with camelCase keys matching eRPC YAML schema.

        """
        return {
            "certFile": self.cert_file,
            "keyFile": self.key_file,
            "caFile": self.ca_file,
        }


@dataclass
class MemoryConnector:
    """In-memory cache connector.

    Args:
        id: Unique connector identifier referenced by cache policies.
        max_items: Maximum number of items to store in memory.

    Examples:
        >>> conn = MemoryConnector(id="mem1", max_items=10_000)
        >>> conn.to_dict()["driver"]
        'memory'

    """

    id: str
    max_items: int

    def to_dict(self) -> dict[str, Any]:
        """Serialize to eRPC config dict.

        Returns:
            Dict with driver and memory configuration.

        """
        return {
            "id": self.id,
            "driver": "memory",
            "memory": {"maxItems": self.max_items},
        }


@dataclass
class RedisConnector:
    """Redis cache connector.

    Args:
        id: Unique connector identifier referenced by cache policies.
        uri: Redis connection URI (e.g., ``redis://localhost:6379``).
        tls: Optional TLS configuration for secure connections.
        pool_size: Optional connection pool size.

    Examples:
        >>> conn = RedisConnector(id="redis1", uri="redis://localhost:6379")
        >>> conn.to_dict()["driver"]
        'redis'

    """

    id: str
    uri: str
    tls: TLSConfig | None = None
    pool_size: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to eRPC config dict.

        Returns:
            Dict with driver and redis configuration.

        """
        redis_conf: dict[str, Any] = {"uri": self.uri}
        if self.tls is not None:
            redis_conf["tls"] = self.tls.to_dict()
        if self.pool_size is not None:
            redis_conf["poolSize"] = self.pool_size
        return {
            "id": self.id,
            "driver": "redis",
            "redis": redis_conf,
        }


@dataclass
class PostgresConnector:
    """PostgreSQL cache connector.

    Args:
        id: Unique connector identifier referenced by cache policies.
        uri: PostgreSQL connection URI.
        table: Table name for cache storage.

    Examples:
        >>> conn = PostgresConnector(id="pg1", uri="postgres://host/db", table="cache")
        >>> conn.to_dict()["driver"]
        'postgresql'

    """

    id: str
    uri: str
    table: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize to eRPC config dict.

        Returns:
            Dict with driver and postgresql configuration.

        """
        return {
            "id": self.id,
            "driver": "postgresql",
            "postgresql": {"connectionUri": self.uri, "table": self.table},
        }


@dataclass
class DynamoDBConnector:
    """AWS DynamoDB cache connector.

    Args:
        id: Unique connector identifier referenced by cache policies.
        table: DynamoDB table name.
        region: AWS region (e.g., ``us-east-1``).
        partition_key_name: Name of the partition key attribute.
        range_key_name: Name of the range/sort key attribute.
        ttl_attribute: Name of the TTL attribute for automatic expiration.

    Examples:
        >>> conn = DynamoDBConnector(
        ...     id="ddb1",
        ...     table="cache",
        ...     region="us-east-1",
        ...     partition_key_name="pk",
        ...     range_key_name="sk",
        ...     ttl_attribute="ttl",
        ... )
        >>> conn.to_dict()["driver"]
        'dynamodb'

    """

    id: str
    table: str
    region: str
    partition_key_name: str
    range_key_name: str
    ttl_attribute: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize to eRPC config dict.

        Returns:
            Dict with driver and dynamodb configuration.

        """
        return {
            "id": self.id,
            "driver": "dynamodb",
            "dynamodb": {
                "table": self.table,
                "region": self.region,
                "partitionKeyName": self.partition_key_name,
                "rangeKeyName": self.range_key_name,
                "ttlAttribute": self.ttl_attribute,
            },
        }


@dataclass
class CompressionConfig:
    """Cache compression configuration.

    Args:
        algorithm: Compression algorithm (e.g., ``zstd``, ``gzip``).
        level: Compression level (e.g., ``default``, ``fast``, ``best``).
        threshold: Minimum item size in bytes before compression is applied.

    Examples:
        >>> comp = CompressionConfig()
        >>> comp.algorithm
        'zstd'

    """

    algorithm: str = "zstd"
    level: str = "default"
    threshold: int = 1024

    def to_dict(self) -> dict[str, Any]:
        """Serialize to eRPC config dict.

        Returns:
            Dict with compression settings.

        """
        return {
            "algorithm": self.algorithm,
            "level": self.level,
            "threshold": self.threshold,
        }


@dataclass
class CachePolicy:
    """Cache policy rule with finality awareness.

    Defines caching behavior for specific methods, networks, and
    finality states.

    Args:
        connector: ID of the connector to use for this policy.
        ttl: Time-to-live duration string (e.g., ``30s``, ``1h``).
        network: Optional network filter (e.g., ``evm:1``).
        method: Optional RPC method filter (e.g., ``eth_getBlockByNumber``).
        finality: Optional finality state filter. One of ``finalized``,
            ``unfinalized``, ``realtime``, or ``unknown``.
        empty: Optional empty response handling. One of ``ignore``,
            ``allow``, or ``only``.
        min_item_size: Optional minimum item size in bytes to cache.
        max_item_size: Optional maximum item size in bytes to cache.

    Examples:
        >>> policy = CachePolicy(connector="mem1", ttl="30s", finality="finalized")
        >>> policy.to_dict()["finality"]
        'finalized'

    """

    connector: str
    ttl: str
    network: str | None = None
    method: str | None = None
    finality: str | None = None
    empty: str | None = None
    min_item_size: int | None = None
    max_item_size: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to eRPC config dict.

        Returns:
            Dict with only non-None fields, using camelCase keys.

        """
        result: dict[str, Any] = {
            "connector": self.connector,
            "ttl": self.ttl,
        }
        if self.network is not None:
            result["network"] = self.network
        if self.method is not None:
            result["method"] = self.method
        if self.finality is not None:
            result["finality"] = self.finality
        if self.empty is not None:
            result["empty"] = self.empty
        if self.min_item_size is not None:
            result["minItemSize"] = self.min_item_size
        if self.max_item_size is not None:
            result["maxItemSize"] = self.max_item_size
        return result


ConnectorType = MemoryConnector | RedisConnector | PostgresConnector | DynamoDBConnector


@dataclass
class DatabaseConfig:
    """Top-level database/cache configuration for eRPC.

    Composes connectors, cache policies, and optional compression into
    the ``database`` section of an eRPC config.

    Args:
        connectors: List of storage backend connectors.
        policies: List of cache policy rules.
        compression: Optional compression configuration.

    Examples:
        >>> db = DatabaseConfig(
        ...     connectors=[MemoryConnector(id="mem", max_items=10_000)],
        ...     policies=[CachePolicy(connector="mem", ttl="30s")],
        ... )
        >>> len(db.to_dict()["connectors"])
        1

    """

    connectors: list[ConnectorType] = field(default_factory=list)
    policies: list[CachePolicy] = field(default_factory=list)
    compression: CompressionConfig | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to eRPC config dict.

        Returns:
            Dict suitable for inclusion in eRPC YAML under
            the ``database`` key.

        """
        result: dict[str, Any] = {
            "connectors": [c.to_dict() for c in self.connectors],
            "policies": [p.to_dict() for p in self.policies],
        }
        if self.compression is not None:
            result["compression"] = self.compression.to_dict()
        return result
