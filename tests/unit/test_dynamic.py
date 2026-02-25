"""Tests for erpc.dynamic module."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, PropertyMock

import pytest

from erpc.config import ERPCConfig
from erpc.dynamic import (
    ConfigDiff,
    _clone_config_with_upstreams,
    _diff_configs,
    add_upstream,
    atomic_write_config,
    remove_upstream,
    update_config,
)
from erpc.exceptions import ERPCNotRunning

if TYPE_CHECKING:
    from pathlib import Path

# ---------------------------------------------------------------------------
# ConfigDiff
# ---------------------------------------------------------------------------


class TestConfigDiff:
    def test_no_changes(self):
        diff = ConfigDiff()
        assert not diff.has_changes
        assert str(diff) == "No changes"

    def test_has_changes_added_upstreams(self):
        diff = ConfigDiff(added_upstreams={137: ["https://polygon.example.com"]})
        assert diff.has_changes
        assert "Added chains: 137" in str(diff)

    def test_has_changes_removed_upstreams(self):
        diff = ConfigDiff(removed_upstreams={1: ["https://eth.example.com"]})
        assert diff.has_changes
        assert "Removed chains: 1" in str(diff)

    def test_has_changes_added_endpoints(self):
        diff = ConfigDiff(added_endpoints={1: ["https://new.example.com"]})
        assert diff.has_changes
        assert "Added endpoints on chain 1" in str(diff)

    def test_has_changes_removed_endpoints(self):
        diff = ConfigDiff(removed_endpoints={1: ["https://old.example.com"]})
        assert diff.has_changes
        assert "Removed endpoints on chain 1" in str(diff)

    def test_has_changes_changed_fields(self):
        diff = ConfigDiff(changed_fields=["log_level"])
        assert diff.has_changes
        assert "Changed fields: log_level" in str(diff)


# ---------------------------------------------------------------------------
# _diff_configs
# ---------------------------------------------------------------------------


class TestDiffConfigs:
    def test_identical(self):
        c = ERPCConfig(upstreams={1: ["https://eth.example.com"]})
        diff = _diff_configs(c, c)
        assert not diff.has_changes

    def test_added_chain(self):
        old = ERPCConfig(upstreams={1: ["https://eth.example.com"]})
        new = ERPCConfig(
            upstreams={1: ["https://eth.example.com"], 137: ["https://polygon.example.com"]}
        )
        diff = _diff_configs(old, new)
        assert 137 in diff.added_upstreams

    def test_removed_chain(self):
        old = ERPCConfig(
            upstreams={1: ["https://eth.example.com"], 137: ["https://polygon.example.com"]}
        )
        new = ERPCConfig(upstreams={1: ["https://eth.example.com"]})
        diff = _diff_configs(old, new)
        assert 137 in diff.removed_upstreams

    def test_added_endpoint(self):
        old = ERPCConfig(upstreams={1: ["https://a.example.com"]})
        new = ERPCConfig(upstreams={1: ["https://a.example.com", "https://b.example.com"]})
        diff = _diff_configs(old, new)
        assert 1 in diff.added_endpoints
        assert "https://b.example.com" in diff.added_endpoints[1]

    def test_removed_endpoint(self):
        old = ERPCConfig(upstreams={1: ["https://a.example.com", "https://b.example.com"]})
        new = ERPCConfig(upstreams={1: ["https://a.example.com"]})
        diff = _diff_configs(old, new)
        assert 1 in diff.removed_endpoints

    def test_changed_scalar(self):
        old = ERPCConfig(log_level="warn")
        new = ERPCConfig(log_level="debug")
        diff = _diff_configs(old, new)
        assert "log_level" in diff.changed_fields


# ---------------------------------------------------------------------------
# atomic_write_config
# ---------------------------------------------------------------------------


class TestAtomicWriteConfig:
    def test_writes_file(self, tmp_path: Path):
        config = ERPCConfig(upstreams={1: ["https://eth.example.com"]})
        out = atomic_write_config(config, tmp_path / "erpc.yaml")
        assert out.exists()
        content = out.read_text()
        assert "py-erpc" in content

    def test_creates_parent_dirs(self, tmp_path: Path):
        config = ERPCConfig()
        out = atomic_write_config(config, tmp_path / "sub" / "dir" / "erpc.yaml")
        assert out.exists()


# ---------------------------------------------------------------------------
# _clone_config_with_upstreams
# ---------------------------------------------------------------------------


class TestCloneConfig:
    def test_clone_changes_upstreams(self):
        original = ERPCConfig(upstreams={1: ["https://eth.example.com"]}, log_level="debug")
        new_upstreams = {137: ["https://polygon.example.com"]}
        cloned = _clone_config_with_upstreams(original, new_upstreams)
        assert cloned.upstreams == new_upstreams
        assert cloned.log_level == "debug"


# ---------------------------------------------------------------------------
# update_config / add_upstream / remove_upstream
# ---------------------------------------------------------------------------


def _mock_process(config: ERPCConfig, running: bool = True) -> MagicMock:
    proc = MagicMock()
    type(proc).is_running = PropertyMock(return_value=running)
    proc.config = config
    proc.stop = MagicMock()
    proc.start = MagicMock()
    return proc


class TestUpdateConfig:
    def test_updates_running_process(self):
        old = ERPCConfig(upstreams={1: ["https://eth.example.com"]})
        new = ERPCConfig(
            upstreams={1: ["https://eth.example.com"], 137: ["https://polygon.example.com"]}
        )
        proc = _mock_process(old)
        diff = update_config(proc, new)
        assert diff.has_changes
        proc.stop.assert_called_once()
        proc.start.assert_called_once()

    def test_raises_when_not_running(self):
        proc = _mock_process(ERPCConfig(), running=False)
        with pytest.raises(ERPCNotRunning):
            update_config(proc, ERPCConfig())


class TestAddUpstream:
    def test_add_new_chain(self):
        config = ERPCConfig(upstreams={1: ["https://eth.example.com"]})
        proc = _mock_process(config)
        diff = add_upstream(proc, 137, "https://polygon.example.com")
        assert diff.has_changes

    def test_add_to_existing_chain(self):
        config = ERPCConfig(upstreams={1: ["https://a.example.com"]})
        proc = _mock_process(config)
        diff = add_upstream(proc, 1, "https://b.example.com")
        assert diff.has_changes


class TestRemoveUpstream:
    def test_remove_endpoint(self):
        config = ERPCConfig(upstreams={1: ["https://a.example.com", "https://b.example.com"]})
        proc = _mock_process(config)
        diff = remove_upstream(proc, 1, "https://a.example.com")
        assert diff.has_changes

    def test_remove_last_endpoint_removes_chain(self):
        config = ERPCConfig(upstreams={1: ["https://a.example.com"]})
        proc = _mock_process(config)
        diff = remove_upstream(proc, 1, "https://a.example.com")
        assert diff.has_changes

    def test_remove_nonexistent_chain(self):
        config = ERPCConfig(upstreams={1: ["https://a.example.com"]})
        proc = _mock_process(config)
        with pytest.raises(ValueError, match="not found"):
            remove_upstream(proc, 999, "https://x.example.com")

    def test_remove_nonexistent_endpoint(self):
        config = ERPCConfig(upstreams={1: ["https://a.example.com"]})
        proc = _mock_process(config)
        with pytest.raises(ValueError, match="not found"):
            remove_upstream(proc, 1, "https://x.example.com")
