"""Tests for eRPC server, metrics, and CORS configuration."""

from __future__ import annotations

import yaml

from erpc.config import ERPCConfig
from erpc.server import CORSConfig, MetricsConfig, ServerConfig


class TestServerConfigDefaults:
    """ServerConfig default values match eRPC defaults."""

    def test_default_host(self) -> None:
        config = ServerConfig()
        assert config.http_host == "127.0.0.1"

    def test_default_port(self) -> None:
        config = ServerConfig()
        assert config.http_port == 4000

    def test_default_max_timeout(self) -> None:
        config = ServerConfig()
        assert config.max_timeout == "60s"

    def test_default_gzip_disabled(self) -> None:
        config = ServerConfig()
        assert config.enable_gzip is False

    def test_default_listen_v6_disabled(self) -> None:
        config = ServerConfig()
        assert config.listen_v6 is False


class TestServerConfigCustom:
    """ServerConfig with custom values."""

    def test_custom_host_and_port(self) -> None:
        config = ServerConfig(http_host="0.0.0.0", http_port=8080)
        assert config.http_host == "0.0.0.0"
        assert config.http_port == 8080

    def test_custom_timeout(self) -> None:
        config = ServerConfig(max_timeout="120s")
        assert config.max_timeout == "120s"

    def test_enable_gzip(self) -> None:
        config = ServerConfig(enable_gzip=True)
        assert config.enable_gzip is True

    def test_listen_v6(self) -> None:
        config = ServerConfig(listen_v6=True)
        assert config.listen_v6 is True

    def test_to_dict_defaults(self) -> None:
        config = ServerConfig()
        d = config.to_dict()
        assert d == {
            "httpHost": "127.0.0.1",
            "httpPort": 4000,
            "maxTimeout": "60s",
        }

    def test_to_dict_all_options(self) -> None:
        config = ServerConfig(
            http_host="0.0.0.0",
            http_port=9000,
            max_timeout="30s",
            enable_gzip=True,
            listen_v6=True,
        )
        d = config.to_dict()
        assert d == {
            "httpHost": "0.0.0.0",
            "httpPort": 9000,
            "maxTimeout": "30s",
            "enableGzip": True,
            "listenV6": True,
        }


class TestMetricsConfigDefaults:
    """MetricsConfig default values."""

    def test_enabled_by_default(self) -> None:
        config = MetricsConfig()
        assert config.enabled is True

    def test_default_host(self) -> None:
        config = MetricsConfig()
        assert config.host == "127.0.0.1"

    def test_default_port(self) -> None:
        config = MetricsConfig()
        assert config.port == 4001

    def test_to_dict_defaults(self) -> None:
        config = MetricsConfig()
        assert config.to_dict() == {
            "enabled": True,
            "host": "127.0.0.1",
            "port": 4001,
        }


class TestMetricsConfigCustom:
    """MetricsConfig with custom values."""

    def test_disabled(self) -> None:
        config = MetricsConfig(enabled=False)
        assert config.enabled is False

    def test_disabled_to_dict(self) -> None:
        config = MetricsConfig(enabled=False)
        assert config.to_dict() == {"enabled": False}

    def test_custom_host_port(self) -> None:
        config = MetricsConfig(host="0.0.0.0", port=9090)
        d = config.to_dict()
        assert d["host"] == "0.0.0.0"
        assert d["port"] == 9090


class TestCORSConfig:
    """CORSConfig tests."""

    def test_defaults_disabled(self) -> None:
        """CORS is effectively disabled by default (empty origins)."""
        config = CORSConfig()
        assert config.allowed_origins == []
        assert config.allowed_methods == []
        assert config.allowed_headers == []
        assert config.allow_credentials is False
        assert config.max_age == 0

    def test_to_dict_defaults_empty(self) -> None:
        """Default CORSConfig serializes to empty dict (omitted)."""
        config = CORSConfig()
        assert config.to_dict() == {}

    def test_custom_origins(self) -> None:
        config = CORSConfig(allowed_origins=["https://example.com", "https://app.io"])
        d = config.to_dict()
        assert d["allowedOrigins"] == ["https://example.com", "https://app.io"]

    def test_full_cors(self) -> None:
        config = CORSConfig(
            allowed_origins=["*"],
            allowed_methods=["GET", "POST"],
            allowed_headers=["Content-Type", "Authorization"],
            allow_credentials=True,
            max_age=3600,
        )
        d = config.to_dict()
        assert d == {
            "allowedOrigins": ["*"],
            "allowedMethods": ["GET", "POST"],
            "allowedHeaders": ["Content-Type", "Authorization"],
            "allowCredentials": True,
            "maxAge": 3600,
        }


class TestERPCConfigServerIntegration:
    """ServerConfig/MetricsConfig/CORSConfig integrate with ERPCConfig."""

    def test_backward_compat_simple_fields(self) -> None:
        """Legacy server_host/server_port still work."""
        config = ERPCConfig(server_host="10.0.0.1", server_port=5000)
        doc = yaml.safe_load(config.to_yaml())
        assert doc["server"]["httpHost"] == "10.0.0.1"
        assert doc["server"]["httpPort"] == 5000

    def test_server_config_overrides_simple_fields(self) -> None:
        """Full ServerConfig takes precedence over simple fields."""
        config = ERPCConfig(
            server_host="10.0.0.1",
            server_port=5000,
            server=ServerConfig(http_host="0.0.0.0", http_port=9000),
        )
        doc = yaml.safe_load(config.to_yaml())
        assert doc["server"]["httpHost"] == "0.0.0.0"
        assert doc["server"]["httpPort"] == 9000

    def test_metrics_config_overrides_simple_fields(self) -> None:
        """Full MetricsConfig takes precedence over simple fields."""
        config = ERPCConfig(
            metrics_host="10.0.0.1",
            metrics_port=9999,
            metrics=MetricsConfig(host="0.0.0.0", port=8080),
        )
        doc = yaml.safe_load(config.to_yaml())
        assert doc["metrics"]["host"] == "0.0.0.0"
        assert doc["metrics"]["port"] == 8080

    def test_metrics_disabled(self) -> None:
        """Disabled metrics only emits enabled: false."""
        config = ERPCConfig(metrics=MetricsConfig(enabled=False))
        doc = yaml.safe_load(config.to_yaml())
        assert doc["metrics"] == {"enabled": False}

    def test_cors_in_server_section(self) -> None:
        """CORS config appears in server section when set."""
        config = ERPCConfig(
            server=ServerConfig(
                cors=CORSConfig(allowed_origins=["*"]),
            ),
        )
        doc = yaml.safe_load(config.to_yaml())
        assert doc["server"]["cors"]["allowedOrigins"] == ["*"]

    def test_no_cors_when_default(self) -> None:
        """No cors key in YAML when CORSConfig is default."""
        config = ERPCConfig(server=ServerConfig())
        doc = yaml.safe_load(config.to_yaml())
        assert "cors" not in doc["server"]

    def test_health_url_uses_server_config(self) -> None:
        """health_url reflects ServerConfig values."""
        config = ERPCConfig(
            server=ServerConfig(http_host="0.0.0.0", http_port=9000),
        )
        assert config.health_url == "http://0.0.0.0:9000/"

    def test_endpoint_url_uses_server_config(self) -> None:
        """endpoint_url reflects ServerConfig values."""
        config = ERPCConfig(
            server=ServerConfig(http_host="0.0.0.0", http_port=9000),
        )
        assert config.endpoint_url(1) == "http://0.0.0.0:9000/py-erpc/evm/1"

    def test_server_gzip_in_yaml(self) -> None:
        """enableGzip appears in YAML when set."""
        config = ERPCConfig(server=ServerConfig(enable_gzip=True))
        doc = yaml.safe_load(config.to_yaml())
        assert doc["server"]["enableGzip"] is True
