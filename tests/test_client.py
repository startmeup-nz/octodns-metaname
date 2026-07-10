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
from octodns_metaname.secrets import MissingSecret


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

    _secret_map = {
        "METANAME_ACCOUNT_REF": "acc-1",
        "METANAME_API_TOKEN": "token-1",
        "METANAME_CONTACT_NAME": "Test User",
        "METANAME_CONTACT_EMAIL": "test@example.com",
        "METANAME_CONTACT_ORG": "Test Org",
        "METANAME_CONTACT_PHONE_COUNTRY": "64",
        "METANAME_CONTACT_PHONE_AREA": "21",
        "METANAME_CONTACT_PHONE_LOCAL": "9876543",
        "METANAME_CONTACT_ADDRESS_LINE1": "123 Test Street",
        "METANAME_CONTACT_CITY": "Wellington",
        "METANAME_CONTACT_POSTAL_CODE": "6011",
        "METANAME_CONTACT_COUNTRY_CODE": "NZ",
    }
    for key, val in _secret_map.items():
        monkeypatch.setenv(key, val)

    def _get_secret(name):
        if name in _secret_map:
            return _secret_map[name]
        raise MissingSecret(name)

    monkeypatch.setattr("octodns_metaname.client.get_secret", _get_secret)


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


# -- Domain lifecycle tests -------------------------------------------


def test_check_domain(monkeypatch, secrets):
    client = make_client(secrets)
    calls = []

    def fake_rpc(method, params, *, request_id=1):
        calls.append((method, tuple(params)))
        return {"value": "available"}

    monkeypatch.setattr(client, "_rpc", fake_rpc)

    result = client.check_domain("example.com")
    assert calls == [("check_availability", ("example.com", None))]
    assert result == "available"


def test_check_domain_taken(monkeypatch, secrets):
    client = make_client(secrets)
    calls = []

    def fake_rpc(method, params, *, request_id=1):
        calls.append((method, tuple(params)))
        return {"value": "taken"}

    monkeypatch.setattr(client, "_rpc", fake_rpc)

    result = client.check_domain("example.com")
    assert result == "taken"


def test_check_domain_strips_trailing_dot(monkeypatch, secrets):
    client = make_client(secrets)
    calls = []

    def fake_rpc(method, params, *, request_id=1):
        calls.append((method, tuple(params)))
        return {"value": "available"}

    monkeypatch.setattr(client, "_rpc", fake_rpc)

    client.check_domain("example.com.")
    assert calls == [("check_availability", ("example.com", None))]


def test_register_domain_confirm_false_raises_valueerror(monkeypatch, secrets):
    client = make_client(secrets)
    with pytest.raises(ValueError, match="confirm=True"):
        client.register_domain("example.com")


def test_register_domain_domain_not_available_raises(monkeypatch, secrets):
    client = make_client(secrets)

    monkeypatch.setattr(client, "check_domain", lambda domain: "taken")

    with pytest.raises(MetanameError, match="not available for registration"):
        client.register_domain("example.com", confirm=True)


def test_register_domain_domain_available_implicit(monkeypatch, secrets):
    client = make_client(secrets)
    calls = []

    def fake_rpc(method, params, *, request_id=1):
        calls.append((method, tuple(params)))
        if method == "check_availability":
            return {"value": "available"}
        if method == "register_domain_name":
            return {"registered": True}
        raise AssertionError("Unexpected method")

    monkeypatch.setattr(client, "_rpc", fake_rpc)

    result = client.register_domain("example.com", confirm=True)

    assert len(calls) == 2
    assert calls[0] == ("check_availability", ("example.com", None))
    method, (domain, term, contacts, nameservers) = calls[1]
    assert method == "register_domain_name"
    assert domain == "example.com"
    assert term == 12
    assert set(contacts.keys()) == {"registrant", "admin", "technical"}
    assert nameservers is None
    assert result["status"] == "registered"


def test_register_domain_custom_contacts_and_nameservers(monkeypatch, secrets):
    client = make_client(secrets)
    calls = []

    def fake_rpc(method, params, *, request_id=1):
        calls.append((method, tuple(params)))
        if method == "check_availability":
            return {"value": "available"}
        if method == "register_domain_name":
            return {"registered": True}
        raise AssertionError("Unexpected method")

    monkeypatch.setattr(client, "_rpc", fake_rpc)

    custom_contacts = {"registrant": {"name": "Test User"}}
    custom_ns = ["ns1.example.com", "ns2.example.com"]

    result = client.register_domain(
        "example.com",
        confirm=True,
        term=24,
        contacts=custom_contacts,
        nameservers=custom_ns,
    )

    _, (domain, term, contacts, nameservers) = calls[1]
    assert term == 24
    assert contacts == custom_contacts
    assert nameservers == custom_ns
    assert result["status"] == "registered"


def test_register_domain_check_returns_no_available_key(monkeypatch, secrets):
    """When check_domain returns anything other than 'available',
    the safe-by-default guardrail blocks registration."""
    client = make_client(secrets)

    monkeypatch.setattr(client, "check_domain", lambda domain, **kw: "unknown_status")

    with pytest.raises(MetanameError, match="not available for registration"):
        client.register_domain("example.com", confirm=True)


def test_register_domain_check_returns_nested_availability(monkeypatch, secrets):
    """When check_domain returns a non-'available' string,
    the guardrail blocks registration."""
    client = make_client(secrets)

    monkeypatch.setattr(client, "check_domain", lambda domain, **kw: "some_future_status")

    with pytest.raises(MetanameError, match="not available for registration"):
        client.register_domain("example.com", confirm=True)


def test_register_domain_invalid_term(monkeypatch, secrets):
    client = make_client(secrets)
    for bad in (0, -1, "12", 0.5, None):
        with pytest.raises(ValueError, match="term must be a positive integer"):
            client.register_domain("example.com", confirm=True, term=bad)


def test_list_domains(monkeypatch, secrets):
    client = make_client(secrets)
    calls = []

    def fake_rpc(method, params, *, request_id=1):
        calls.append((method, tuple(params)))
        return [
            {"name": "example.com", "status": "active"},
            {"name": "test.nz", "status": "active"},
        ]

    monkeypatch.setattr(client, "_rpc", fake_rpc)

    domains = client.list_domains()
    assert calls == [("domain_names", ())]
    assert len(domains) == 2
    assert domains[0]["name"] == "example.com"


def test_list_domains_non_list_result(monkeypatch, secrets):
    client = make_client(secrets)

    def fake_rpc(_method, _params, *, request_id=1):
        return {"count": 0}

    monkeypatch.setattr(client, "_rpc", fake_rpc)

    domains = client.list_domains()
    assert domains == []


def test_registration_contacts_structure(monkeypatch, secrets):
    client = make_client(secrets)
    contacts = client._registration_contacts()

    assert set(contacts.keys()) == {"registrant", "admin", "technical"}
    for role in ("registrant", "admin", "technical"):
        assert "name" in contacts[role]
        assert "email_address" in contacts[role]
        assert "postal_address" in contacts[role]
        assert "phone_number" in contacts[role]


def test_default_contact_missing_email_raises(monkeypatch, secrets):
    """When METANAME_CONTACT_EMAIL is not set, _default_contact raises
    MissingSecret rather than falling back to a placeholder."""
    monkeypatch.delenv("METANAME_CONTACT_EMAIL", raising=False)

    def raise_missing(name):
        if name == "METANAME_CONTACT_EMAIL":
            raise MissingSecret("not set")
        if name not in _secret_map:
            raise MissingSecret(name)
        return _secret_map[name]

    _secret_map = {
        "METANAME_ACCOUNT_REF": "acc-1",
        "METANAME_API_TOKEN": "token-1",
        "METANAME_CONTACT_NAME": "Test User",
        "METANAME_CONTACT_ORG": "Test Org",
        "METANAME_CONTACT_PHONE_COUNTRY": "64",
        "METANAME_CONTACT_PHONE_AREA": "21",
        "METANAME_CONTACT_PHONE_LOCAL": "9876543",
        "METANAME_CONTACT_ADDRESS_LINE1": "123 Test Street",
        "METANAME_CONTACT_CITY": "Wellington",
        "METANAME_CONTACT_POSTAL_CODE": "6011",
        "METANAME_CONTACT_COUNTRY_CODE": "NZ",
    }

    monkeypatch.setattr("octodns_metaname.client.get_secret", raise_missing)

    client = make_client(secrets)
    with pytest.raises(MissingSecret, match="METANAME_CONTACT_EMAIL"):
        client._default_contact()
