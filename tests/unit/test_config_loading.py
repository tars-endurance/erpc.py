"""Tests for loading and validating existing eRPC YAML configs."""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

import pytest
import yaml

from erpc.config import ERPCConfig
from erpc.exceptions import ERPCConfigError

if TYPE_CHECKING:
    from pathlib import Path

# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture()
def minimal_yaml(tmp_path: Path) -> Path:
    """Write a minimal valid erpc.yaml and return its path."""
    doc = {
        "logLevel": "warn",
        "server": {"httpHost": "127.0.0.1", "httpPort": 4000, "maxTimeout": "60s"},
        "metrics": {"enabled": True, "host": "127.0.0.1", "port": 4001},
        "projects": [
            {
                "id": "my-project",
                "networks": [],
            }
        ],
    }
    path = tmp_path / "erpc.yaml"
    path.write_text(yaml.dump(doc, sort_keys=False))
    return path


@pytest.fixture()
def full_yaml(tmp_path: Path) -> Path:
    """Write a full-featured erpc.yaml and return its path."""
    doc = {
        "logLevel": "debug",
        "server": {"httpHost": "0.0.0.0", "httpPort": 8080, "maxTimeout": "120s"},
        "metrics": {"enabled": True, "host": "0.0.0.0", "port": 9090},
        "projects": [
            {
                "id": "full-project",
                "cacheConfig": {
                    "connectors": [
                        {
                            "id": "memory-cache",
                            "driver": "memory",
                            "memory": {"maxItems": 5000},
                        }
                    ]
                },
                "networks": [
                    {
                        "architecture": "evm",
                        "evm": {"chainId": 1},
                        "upstreams": [
                            {"id": "upstream-1-0", "endpoint": "https://eth.example.com"},
                            {"id": "upstream-1-1", "endpoint": "https://eth2.example.com"},
                        ],
                    },
                    {
                        "architecture": "evm",
                        "evm": {"chainId": 137},
                        "upstreams": [
                            {"id": "upstream-137-0", "endpoint": "https://poly.example.com"},
                        ],
                    },
                ],
            }
        ],
    }
    path = tmp_path / "erpc.yaml"
    path.write_text(yaml.dump(doc, sort_keys=False))
    return path


# ── Loading tests ────────────────────────────────────────────────────────────


class TestFromYaml:
    """Tests for ERPCConfig.from_yaml()."""

    def test_from_yaml_minimal(self, minimal_yaml: Path) -> None:
        """Load a minimal erpc.yaml and get an ERPCConfig back."""
        config = ERPCConfig.from_yaml(minimal_yaml)
        assert isinstance(config, ERPCConfig)
        assert config.project_id == "my-project"
        assert config.log_level == "warn"
        assert config.server_host == "127.0.0.1"
        assert config.server_port == 4000

    def test_from_yaml_with_upstreams(self, full_yaml: Path) -> None:
        """Parse upstreams from YAML correctly."""
        config = ERPCConfig.from_yaml(full_yaml)
        assert 1 in config.upstreams
        assert 137 in config.upstreams
        assert config.upstreams[1] == [
            "https://eth.example.com",
            "https://eth2.example.com",
        ]
        assert config.upstreams[137] == ["https://poly.example.com"]

    def test_from_yaml_with_cache(self, full_yaml: Path) -> None:
        """Parse cache config from YAML."""
        config = ERPCConfig.from_yaml(full_yaml)
        assert config.cache.max_items == 5000

    def test_from_yaml_with_networks(self, full_yaml: Path) -> None:
        """Parse network-level config — project has correct network count."""
        config = ERPCConfig.from_yaml(full_yaml)
        assert len(config.upstreams) == 2
        assert config.server_host == "0.0.0.0"
        assert config.server_port == 8080
        assert config.metrics_host == "0.0.0.0"
        assert config.metrics_port == 9090

    def test_from_yaml_nonexistent_file(self, tmp_path: Path) -> None:
        """Raises FileNotFoundError for missing files."""
        with pytest.raises(FileNotFoundError):
            ERPCConfig.from_yaml(tmp_path / "nope.yaml")

    def test_from_yaml_invalid_yaml(self, tmp_path: Path) -> None:
        """Raises ERPCConfigError on malformed YAML."""
        bad = tmp_path / "bad.yaml"
        bad.write_text(":\n  - :\n    {{invalid")
        with pytest.raises(ERPCConfigError):
            ERPCConfig.from_yaml(bad)

    def test_from_yaml_missing_projects(self, tmp_path: Path) -> None:
        """Raises ERPCConfigError when 'projects' key is absent."""
        path = tmp_path / "no-projects.yaml"
        path.write_text(yaml.dump({"logLevel": "info"}))
        with pytest.raises(ERPCConfigError, match="projects"):
            ERPCConfig.from_yaml(path)

    def test_from_yaml_non_mapping(self, tmp_path: Path) -> None:
        """Raises ERPCConfigError when YAML root is not a mapping."""
        path = tmp_path / "list.yaml"
        path.write_text("- item1\n- item2\n")
        with pytest.raises(ERPCConfigError, match="Expected YAML mapping"):
            ERPCConfig.from_yaml(path)


# ── Dict loading tests ──────────────────────────────────────────────────────


class TestFromDict:
    """Tests for ERPCConfig.from_dict()."""

    def test_from_dict(self) -> None:
        """Construct ERPCConfig from a plain dictionary."""
        data = {
            "logLevel": "info",
            "server": {"httpHost": "0.0.0.0", "httpPort": 9000},
            "projects": [
                {
                    "id": "dict-project",
                    "networks": [
                        {
                            "architecture": "evm",
                            "evm": {"chainId": 42},
                            "upstreams": [{"id": "u-0", "endpoint": "https://rpc.example.com"}],
                        }
                    ],
                }
            ],
        }
        config = ERPCConfig.from_dict(data)
        assert config.project_id == "dict-project"
        assert config.server_host == "0.0.0.0"
        assert config.server_port == 9000
        assert config.upstreams[42] == ["https://rpc.example.com"]

    def test_from_dict_invalid(self) -> None:
        """Raises ERPCConfigError on bad structure (no projects)."""
        with pytest.raises(ERPCConfigError):
            ERPCConfig.from_dict({"logLevel": "info"})


# ── Round-trip test ──────────────────────────────────────────────────────────


class TestRoundTrip:
    """Tests for round-trip fidelity: load → write → load."""

    def test_round_trip(self, full_yaml: Path, tmp_path: Path) -> None:
        """Load YAML → ERPCConfig → write YAML → load again → assert equal."""
        original = ERPCConfig.from_yaml(full_yaml)
        out_path = tmp_path / "roundtrip.yaml"
        original.write(out_path)

        reloaded = ERPCConfig.from_yaml(out_path)
        assert reloaded.project_id == original.project_id
        assert reloaded.upstreams == original.upstreams
        assert reloaded.server_host == original.server_host
        assert reloaded.server_port == original.server_port
        assert reloaded.metrics_host == original.metrics_host
        assert reloaded.metrics_port == original.metrics_port
        assert reloaded.log_level == original.log_level
        assert reloaded.cache.max_items == original.cache.max_items


# ── Validation tests ─────────────────────────────────────────────────────────


class TestValidation:
    """Tests for ERPCConfig.validate()."""

    def test_validate_config(self, full_yaml: Path) -> None:
        """Valid config passes validation without error."""
        config = ERPCConfig.from_yaml(full_yaml)
        config.validate()  # should not raise

    def test_validate_empty_upstreams_warning(self, minimal_yaml: Path) -> None:
        """Empty upstreams emits a warning but does not error."""
        config = ERPCConfig.from_yaml(minimal_yaml)
        assert config.upstreams == {}
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            config.validate()
            upstream_warnings = [x for x in w if "upstream" in str(x.message).lower()]
            assert len(upstream_warnings) == 1
