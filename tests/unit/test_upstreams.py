"""Tests for erpc.upstreams module."""

from erpc.upstreams import UpstreamConfig


class TestUpstreamConfig:
    """Tests for UpstreamConfig dataclass."""

    def test_defaults(self):
        uc = UpstreamConfig()
        assert uc.id == ""
        assert uc.endpoint == ""
        assert uc.type == "evm"
        assert uc.to_dict() == {}

    def test_full_config(self):
        uc = UpstreamConfig(
            id="my-upstream",
            endpoint="https://rpc.example.com",
            type="evm+alchemy",
            vendor_name="alchemy",
            allowed_methods=["eth_call"],
            ignored_methods=["eth_mining"],
            failsafe={"timeout": "5s"},
            json_rpc={"batchMaxSize": 10},
        )
        d = uc.to_dict()
        assert d["id"] == "my-upstream"
        assert d["endpoint"] == "https://rpc.example.com"
        assert d["type"] == "evm+alchemy"
        assert d["vendorName"] == "alchemy"
        assert d["allowMethods"] == ["eth_call"]
        assert d["ignoreMethods"] == ["eth_mining"]
        assert d["failsafe"] == {"timeout": "5s"}
        assert d["jsonRpc"] == {"batchMaxSize": 10}

    def test_partial_config(self):
        uc = UpstreamConfig(id="u1", endpoint="https://rpc.example.com")
        d = uc.to_dict()
        assert d == {"id": "u1", "endpoint": "https://rpc.example.com"}
        assert "type" not in d  # default evm is omitted

    def test_evm_type_omitted(self):
        uc = UpstreamConfig(type="evm")
        assert "type" not in uc.to_dict()
