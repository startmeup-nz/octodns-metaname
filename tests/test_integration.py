"""Integration tests against the Metaname **test** API.

These tests use ``vcrpy`` to record/replay HTTP interactions.  The first
run records cassettes under ``tests/cassettes/``.  Subsequent runs replay
them offline — no API call is made and no credit is spent.

Credentials are resolved from ``METANAME_ACCOUNT_REF`` /
``METANAME_API_TOKEN`` or their ``*_REF`` counterparts through the configured
provider resolver. Credential values are scrubbed from recorded cassettes.

Markers
-------
``registration`` — excluded by default; run explicitly to register a
real (throw-away) domain on the test system.
"""

import pytest

from octodns_metaname.client import MetanameClient, MetanameError

_FIXED_TEST_DOMAIN = "metaname-regtest-permanent.nz"


class TestMetanameIntegration:
    """Happy-path integration tests against the live test API."""

    def test_account_balance(self, test_client: MetanameClient) -> None:
        """Verify authentication works and the balance is returned as a
        string (per the API docs ``account_balance`` returns a String,
        which ``_rpc`` wraps in ``{"value": ...}``)."""
        result = test_client.ping()
        assert isinstance(result, dict)
        assert "value" in result
        balance = result["value"]
        assert isinstance(balance, str)
        assert float(balance) > 0

    def test_check_availability_taken(
        self, test_client: MetanameClient
    ) -> None:
        """``check_availability`` for a domain we know is registered returns
        the string ``"taken"``."""
        result = test_client.check_domain("google.com")
        assert result == "taken"

    def test_check_availability_available(
        self, test_client: MetanameClient
    ) -> None:
        """``check_availability`` for a nonsense domain returns
        ``"available"``."""
        result = test_client.check_domain("octodns-test-nonexistent.nz")
        assert result == "available"

    def test_list_domains(self, test_client: MetanameClient) -> None:
        """``domain_names`` returns a list of domain objects."""
        domains = test_client.list_domains()
        assert isinstance(domains, list)
        if domains:
            first = domains[0]
            assert isinstance(first, dict)
            assert "name" in first
            assert "status" in first

    def test_price_nz_registration(self, test_client: MetanameClient) -> None:
        """``price`` for a .nz registration at 12 months returns a numeric
        string."""
        result = test_client._rpc(
            "price", ["example.nz", 12, False]
        )
        assert isinstance(result, dict)
        assert "value" in result
        assert float(result["value"]) > 0

    def test_price_nz_renewal(self, test_client: MetanameClient) -> None:
        """``price`` for a .nz renewal matches registration price."""
        reg = test_client._rpc("price", ["example.nz", 12, False])
        renewal = test_client._rpc("price", ["example.nz", 12, True])
        assert reg == renewal

    def test_price_invalid_term_raises(
        self, test_client: MetanameClient
    ) -> None:
        """A term outside the supported range raises a MetanameAPIError."""
        with pytest.raises(MetanameError, match="Invalid term"):

            test_client._rpc("price", ["example.com", 1, False])

    # -- registration (expensive — explicitly opt in) -------------------

    @pytest.mark.registration
    def test_register_nz_domain(self, test_client: MetanameClient) -> None:
        """End-to-end: register a throw-away .nz domain with term=1 on
        the test system, then verify it appears in ``list_domains``.

        WARNING: this spends real credit against the test account balance.
        Uses a **fixed** domain name (``octodns-regtest-permanent.nz``)
        so the cassette can be recorded once and replayed offline.  If the
        domain already exists from a prior recording, the ``check_domain``
        / ``register_domain`` calls in the cassette will replay the
        recorded response regardless — no new registration occurs.
        """
        # Pre-flight check (validating our client, not the API)
        availability = test_client.check_domain(_FIXED_TEST_DOMAIN)

        # If the domain is already registered (from a previous test run)
        # we can still verify it appears in list_domains.
        if availability != "available":
            names = [
                d["name"]
                for d in test_client.list_domains()
                if d["name"] == _FIXED_TEST_DOMAIN
            ]
            assert len(names) == 1, (
                f"Expected {_FIXED_TEST_DOMAIN} to exist in list_domains()"
            )
            return

        result = test_client.register_domain(
            _FIXED_TEST_DOMAIN, confirm=True, term=12
        )
        assert result["status"] == "registered"

        # Verify domain appears in account listing
        names = [
            d["name"]
            for d in test_client.list_domains()
            if d["name"] == _FIXED_TEST_DOMAIN
        ]
        assert len(names) == 1, (
            f"Domain {_FIXED_TEST_DOMAIN} not found in list_domains()"
        )
