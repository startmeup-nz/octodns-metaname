"""Unit tests for the secret resolution utilities."""

import os

import pytest

from octodns_metaname import secrets


def teardown_function():
    """Reset resolver state and env vars between tests."""

    secrets.clear_secret_resolver()
    for key in list(os.environ):
        if key.startswith("TEST_SECRET"):
            os.environ.pop(key, None)
    os.environ.pop("OCTODNS_METANAME_SECRET_RESOLVER", None)


def test_get_secret_direct_env():
    os.environ["TEST_SECRET"] = "value"
    assert secrets.get_secret("TEST_SECRET") == "value"


def test_get_secret_missing_raises():
    with pytest.raises(secrets.MissingSecret):
        secrets.get_secret("TEST_SECRET")


def test_get_secret_reference_without_resolver():
    os.environ["TEST_SECRET_REF"] = "ref-value"
    with pytest.raises(secrets.MissingSecret):
        secrets.get_secret("TEST_SECRET")


def test_get_secret_with_registered_resolver():
    os.environ["TEST_SECRET_REF"] = "ref-value"

    def resolver(name: str, reference: str | None):
        if reference == "ref-value":
            return "resolved"
        return None

    secrets.set_secret_resolver(resolver)
    assert secrets.get_secret("TEST_SECRET") == "resolved"


def test_get_secret_with_env_loader():
    os.environ["TEST_SECRET_REF"] = "ref-env"
    os.environ["OCTODNS_METANAME_SECRET_RESOLVER"] = "octodns_metaname.testing_resolver:resolver"
    assert secrets.get_secret("TEST_SECRET") == "resolved-from-env"


def test_get_secret_with_op_opsdevnz_resolver(monkeypatch):
    import op_opsdevnz

    os.environ["TEST_SECRET_REF"] = "op://Vault/Item/Field"
    os.environ["OCTODNS_METANAME_SECRET_RESOLVER"] = (
        "octodns_metaname.op_opsdevnz_hooks:resolve"
    )

    def fake_resolve_secret(**kwargs):
        assert kwargs["secret_ref"] == "op://Vault/Item/Field"
        assert kwargs["env_override"] == "TEST_SECRET"
        return type("Resolution", (), {"value": "resolved-by-op-opsdevnz"})()

    monkeypatch.setattr(op_opsdevnz, "resolve_secret", fake_resolve_secret)
    assert secrets.get_secret("TEST_SECRET") == "resolved-by-op-opsdevnz"
