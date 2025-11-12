"""Unit tests for the Metaname JSON-RPC client helpers."""

import json
from typing import Any

import pytest

from octodns_metaname.client import (
    MetanameAPIError,
    MetanameClient,
    MetanameError,
    ZoneRecord,
)


class DummyResponse:
    """Minimal stand-in for ``requests.Response`` used in client tests."""

    def __init__(self, *, status: int = 200, payload: Any = None) -> None:
        self.status_code = status
        self._payload = payload or {"jsonrpc": "2.0", "result": {"ok": True}, "id": 1}
        if isinstance(self._payload, Exception):
            self.text = "error"
        else:
            self.text = json.dumps(self._payload)

    def json(self) -> Any:
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


@pytest.fixture
def secrets(monkeypatch):
    """Ensure required secrets env vars resolve during tests."""

    monkeypatch.setenv("METANAME_ACCOUNT_REF", "acc-1")
    monkeypatch.setenv("METANAME_API_TOKEN", "token-1")
    monkeypatch.setattr(
        "octodns_metaname.client.get_secret",
        lambda name: {"METANAME_ACCOUNT_REF": "acc-1", "METANAME_API_TOKEN": "token-1"}[name],
    )


def make_client(secrets) -> MetanameClient:  # type: ignore[valid-type]
    return MetanameClient(base_url="https://example.invalid/api")


def test_rpc_success(monkeypatch, secrets):
    """A successful RPC returns the parsed ``result`` payload."""

    response = DummyResponse(payload={"jsonrpc": "2.0", "result": {"balance": 123}, "id": 1})
    monkeypatch.setattr("octodns_metaname.client.requests.post", lambda *_, **__: response)

    client = make_client(secrets)
    result = client._rpc("account_balance", [])

    assert result == {"balance": 123}


def test_rpc_http_error(monkeypatch, secrets):
    """Non-200 responses raise ``MetanameError``."""

    response = DummyResponse(status=500, payload={"error": "oops"})
    monkeypatch.setattr("octodns_metaname.client.requests.post", lambda *_, **__: response)

    client = make_client(secrets)
    with pytest.raises(MetanameError):
        client._rpc("account_balance", [])


def test_rpc_api_error(monkeypatch, secrets):
    """API error payloads surface as ``MetanameAPIError`` with code info."""

    response = DummyResponse(
        payload={
            "jsonrpc": "2.0",
            "error": {"code": 123, "message": "Domain not found"},
            "id": 1,
        }
    )
    monkeypatch.setattr("octodns_metaname.client.requests.post", lambda *_, **__: response)

    client = make_client(secrets)
    with pytest.raises(MetanameAPIError) as excinfo:
        client._rpc("dns_zone", ["example.com"])

    assert excinfo.value.code == 123


def test_rpc_invalid_json(monkeypatch, secrets):
    """Garbage JSON is treated as a generic client error."""

    payload = json.JSONDecodeError("bad", "{}", 0)
    response = DummyResponse(payload=payload)
    monkeypatch.setattr("octodns_metaname.client.requests.post", lambda *_, **__: response)

    client = make_client(secrets)
    with pytest.raises(MetanameError):
        client._rpc("dns_zone", ["example.com"])


def test_iter_zone_records_pagination(monkeypatch, secrets):
    """Chunked iteration yields records and advances offsets as expected."""

    client = make_client(secrets)
    calls = []

    def fake_rpc(method, params, *, request_id=1):
        calls.append((method, tuple(params)))
        if method == "dns_zone_chunk":
            domain, page_size, offset = params
            if offset == 0:
                return [
                    {"reference": "rec-1", "name": "@", "type": "A", "data": "1.2.3.4", "ttl": 60}
                ]
            return []
        raise AssertionError("Unexpected method")

    monkeypatch.setattr(client, "_rpc", fake_rpc)

    records = list(client.iter_zone_records("example.com.", page_size=100))

    assert calls == [("dns_zone_chunk", ("example.com", 100, 0))]
    assert len(records) == 1
    assert isinstance(records[0], ZoneRecord)
    assert records[0].data == "1.2.3.4"
