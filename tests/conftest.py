"""Pytest fixtures and VCR configuration for Metaname integration tests.

Cassettes are recorded against the Metaname **test** API
(https://test.metaname.net/api/1.1).  Credentials are read from the
environment — they are *never* committed.
"""

import json
import os

import pytest

from octodns_metaname.client import TEST_API_URL, MetanameClient

CASSETTE_DIR = os.path.join(os.path.dirname(__file__), "cassettes")


def _scrub_credentials(request):
    """Replace account-ref and API-key in recorded JSON-RPC bodies."""
    try:
        body = json.loads(request.body.decode("utf-8"))
    except Exception:
        return request
    params = body.get("params")
    if isinstance(params, list) and len(params) >= 2:
        params[0] = "REDACTED_ACCOUNT_REF"
        params[1] = "REDACTED_API_KEY"
        request.body = json.dumps(body).encode("utf-8")
    return request


def _jsonrpc_body_matcher(r1, r2):
    """Match two JSON-RPC requests by comparing their ``method`` and
    ``params`` **after** credential scrubbing so that the comparison is
    insensitive to whether real or dummy credentials were used."""
    try:
        b1 = json.loads(r1.body.decode("utf-8"))
        b2 = json.loads(r2.body.decode("utf-8"))
    except Exception:
        return False
    params1 = list(b1.get("params", []))
    params2 = list(b2.get("params", []))
    if len(params1) >= 2:
        params1[0] = params1[1] = "CLEAN"
    if len(params2) >= 2:
        params2[0] = params2[1] = "CLEAN"
    return b1.get("method") == b2.get("method") and params1 == params2


def _get_vcr():
    """Lazy-init the VCR instance (avoids importing vcr at module level so
    unit tests don't need vcrpy installed)."""
    import vcr

    v = vcr.VCR(
        cassette_library_dir=CASSETTE_DIR,
        record_mode="once",
        match_on=["method", "scheme", "host", "port", "path"],
        before_record_request=_scrub_credentials,
        filter_headers=["authorization"],
    )
    v.register_matcher("jsonrpc-body", _jsonrpc_body_matcher)
    v.match_on = ["method", "scheme", "host", "port", "path", "jsonrpc-body"]
    return v


@pytest.fixture(scope="class", autouse=True)
def _vcr_cassette(request):
    """Auto-use: wrap every test class in a VCR cassette.

    The cassette is named after the test class (e.g.
    ``TestMetanameIntegration.yaml``).
    """
    cls = request.node.getparent(pytest.Class)
    if cls is None:
        yield
        return
    name = cls.name
    with _get_vcr().use_cassette(f"{name}.yaml") as cassette:
        yield cassette


@pytest.fixture(scope="session")
def live_credentials():
    """Return (account_ref, api_token) or dummy values for cassette replay.

    When env vars are present we record/re-record; when absent we fall
    back to placeholders so VCR can replay from the cassette (the
    cassette's scrubbed params are ignored during replay).
    """
    ref = os.getenv("METANAME_ACCOUNT_REF")
    token = os.getenv("METANAME_API_TOKEN")
    if ref and token:
        return ref, token
    has_cassette = os.path.exists(
        os.path.join(CASSETTE_DIR, "TestMetanameIntegration.yaml")
    )
    if has_cassette:
        return ("FAKE_REF", "FAKE_TOKEN")
    pytest.skip(
        "No METANAME_ACCOUNT_REF / METANAME_API_TOKEN and no cassette "
        "to replay — set env vars to record"
    )


_CONTACT_ENV_VARS = [
    "METANAME_CONTACT_NAME",
    "METANAME_CONTACT_EMAIL",
    "METANAME_CONTACT_PHONE_COUNTRY",
    "METANAME_CONTACT_PHONE_AREA",
    "METANAME_CONTACT_PHONE_LOCAL",
    "METANAME_CONTACT_ADDRESS_LINE1",
    "METANAME_CONTACT_CITY",
    "METANAME_CONTACT_POSTAL_CODE",
    "METANAME_CONTACT_COUNTRY_CODE",
]


@pytest.fixture
def test_client(live_credentials, monkeypatch):
    """MetanameClient pointed at the test API with live credentials.

    Also patches required contact env vars from the environment so that
    registration tests can build valid contacts without hardcoding
    account-specific values.
    """
    ref, token = live_credentials
    monkeypatch.setenv("METANAME_ACCOUNT_REF", ref)
    monkeypatch.setenv("METANAME_API_TOKEN", token)
    for name in _CONTACT_ENV_VARS:
        value = os.getenv(name)
        if value:
            monkeypatch.setenv(name, value)
    return MetanameClient(base_url=TEST_API_URL)
