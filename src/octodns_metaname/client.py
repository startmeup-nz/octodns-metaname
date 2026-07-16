"""Thin wrapper around the Metaname JSON-RPC API used by OctoDNS."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Iterator, Optional, Union, cast

import requests

from .secrets import MissingSecret, get_secret

TEST_API_URL = "https://test.metaname.net/api/1.1"
PROD_API_URL = "https://metaname.net/api/1.1"


@dataclass
class Contact:
    """Contact details used when provisioning domains via the API."""

    name: str
    email: str
    phone_country_code: str
    phone_area_code: Optional[str]
    phone_local_number: str
    organisation: Optional[str] = None
    address_line1: str = ""
    address_line2: Optional[str] = None
    city: str = ""
    region: Optional[str] = None
    postal_code: str = ""
    country_code: str = "NZ"

    def to_payload(self) -> Dict[str, Any]:
        """Serialise the contact into the structure expected by Metaname."""

        return {
            "name": self.name,
            "email_address": self.email,
            "organisation_name": self.organisation,
            "postal_address": {
                "line1": self.address_line1,
                "line2": self.address_line2,
                "city": self.city,
                "region": self.region,
                "postal_code": self.postal_code,
                "country_code": self.country_code,
            },
            "phone_number": {
                "country_code": self.phone_country_code,
                "area_code": self.phone_area_code,
                "local_number": self.phone_local_number,
            },
            "fax_number": None,
        }


@dataclass
class ZoneRecord:
    """Representation of a DNS record as returned by the Metaname API."""

    reference: Optional[str]
    name: str
    rtype: str
    data: str
    ttl: int
    aux: Optional[int] = None

    @classmethod
    def from_api(cls, payload: Dict[str, Any]) -> "ZoneRecord":
        """Construct a zone record from an API payload."""

        return cls(
            reference=payload.get("reference"),
            name=payload.get("name") or "@",
            rtype=payload["type"].upper(),
            data=payload.get("data", ""),
            ttl=int(payload.get("ttl", 3600)),
            aux=payload.get("aux"),
        )

    def to_api_payload(self) -> Dict[str, Any]:
        """Serialise the record into the JSON-RPC payload schema."""

        payload: Dict[str, Any] = {
            "name": self.name,
            "type": self.rtype,
            "data": self.data,
            "ttl": self.ttl,
        }
        if self.aux is not None:
            payload["aux"] = self.aux
        return payload


class MetanameError(RuntimeError):
    """Generic error for Metaname client failures."""


class MetanameAPIError(MetanameError):
    """Raised when the remote API reports an error."""

    def __init__(self, message: str, *, code: Optional[int] = None, payload: Any = None) -> None:
        self.code = code
        self.payload = payload
        if code is not None:
            message = f"{message} (code {code})"
        super().__init__(message)


class MetanameClient:
    """Convenience wrapper around Metaname's JSON-RPC 2.0 endpoints."""

    def __init__(self, *, base_url: str = TEST_API_URL, timeout: float = 10.0) -> None:
        """
        Parameters
        ----------
        base_url:
            Target API URL. Defaults to the Metaname test endpoint.
        timeout:
            Timeout (seconds) applied to HTTP requests.
        """

        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.account_ref = get_secret("METANAME_ACCOUNT_REF")
        self.api_key = get_secret("METANAME_API_TOKEN")

    def _rpc(self, method: str, params: list[Any], *, request_id: int = 1) -> Any:
        """Call a JSON-RPC method and return the parsed ``result`` payload."""

        payload: dict[str, Any] = {
            "jsonrpc": "2.0",
            "method": method,
            "params": [self.account_ref, self.api_key, *params],
            "id": request_id,
        }
        try:
            response = requests.post(self.base_url, json=payload, timeout=self.timeout)
        except requests.RequestException as exc:  # pragma: no cover
            raise MetanameError(f"Request to Metaname failed: {exc}") from exc
        if response.status_code != 200:
            raise MetanameError(f"Metaname returned HTTP {response.status_code}: {response.text}")
        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            raise MetanameError("Metaname response was not valid JSON") from exc
        error = data.get("error")
        if error:
            raise MetanameAPIError(
                error.get("message", "Metaname API error"),
                code=error.get("code"),
                payload=error.get("data"),
            )
        if "result" not in data:
            raise MetanameError("Metaname API response missing 'result'")
        result = data["result"]
        if result is None:
            return {}
        if not isinstance(result, dict) and not isinstance(result, list):
            return {"value": result}
        return result

    def ping(self) -> Dict[str, Any]:
        """Check authentication by querying the account balance."""

        response = self._rpc("account_balance", [])
        return cast(Dict[str, Any], response)

    def list_zone_records(
        self, domain: str, *, page_size: Optional[int] = None
    ) -> list[ZoneRecord]:
        """
        Retrieve all DNS records for ``domain``.

        Parameters
        ----------
        domain:
            Fully-qualified domain (may end with a trailing dot).
        page_size:
            When provided, fetch records in chunks using ``dns_zone_chunk``.
        """

        return list(self.iter_zone_records(domain, page_size=page_size))

    def iter_zone_records(
        self, domain: str, *, page_size: Optional[int] = None
    ) -> Iterator[ZoneRecord]:
        """Yield DNS records for ``domain`` optionally using pagination."""

        domain = _strip_trailing_dot(domain)
        if page_size:
            offset = 0
            while True:
                records = self._rpc("dns_zone_chunk", [domain, page_size, offset])
                if not records:
                    break
                for item in records:
                    yield ZoneRecord.from_api(item)
                offset += len(records)
                if len(records) < page_size:
                    break
            return

        records = self._rpc("dns_zone", [domain])
        if isinstance(records, dict):
            records = records.get("records", [])
        for item in records or []:
            yield ZoneRecord.from_api(item)

    def create_zone_record(
        self, domain: str, record: Union[ZoneRecord, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Create a DNS record within ``domain``."""

        domain = _strip_trailing_dot(domain)
        payload = record.to_api_payload() if isinstance(record, ZoneRecord) else dict(record)
        response = self._rpc("create_dns_record", [domain, payload])
        return cast(Dict[str, Any], response)

    def update_zone_record(
        self,
        domain: str,
        reference: str,
        record: Union[ZoneRecord, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Update an existing record identified by ``reference``."""

        domain = _strip_trailing_dot(domain)
        payload = record.to_api_payload() if isinstance(record, ZoneRecord) else dict(record)
        response = self._rpc("update_dns_record", [domain, reference, payload])
        return cast(Dict[str, Any], response)

    def delete_zone_record(self, domain: str, reference: str) -> Dict[str, Any]:
        """Delete a record from ``domain`` by ``reference``."""

        domain = _strip_trailing_dot(domain)
        response = self._rpc("delete_dns_record", [domain, reference])
        return cast(Dict[str, Any], response)

    # -- Domain lifecycle ----------------------------------------------

    def list_domains(self) -> list[Dict[str, Any]]:
        """Return the domains registered under this account.

        Uses Metaname's ``domain_names`` method, which reports every domain the
        authenticated account owns (name, status, registration dates, name
        servers and contacts).
        """

        result = self._rpc("domain_names", [])
        if isinstance(result, list):
            return cast("list[Dict[str, Any]]", result)
        # Metaname's domain_names may return a non-list payload (e.g. an empty
        # dict) when no domains exist under the account.  Treat that as an
        # empty list rather than raising for a missing-account edge case.
        return []

    def check_domain(self, domain: str, *, source_ip: Optional[str] = None) -> str:
        """Check domain availability via Metaname.

        Calls ``check_availability`` and returns one of:

        - ``"available"`` — the domain can be registered
        - ``"taken"`` — the domain is already registered

        Metaname may introduce more-specific status strings in future; any
        string other than ``"available"`` means the domain cannot be
        registered.

        Parameters
        ----------
        domain:
            Domain name to check (trailing dot is stripped).
        source_ip:
            IP address of the system making the request.  Pass the web
            client IP when acting on behalf of a customer.  ``None`` is
            fine for batch / system-originated checks.
        """

        domain = _strip_trailing_dot(domain)
        result = self._rpc("check_availability", [domain, source_ip])
        # _rpc wraps scalar results in {"value": ...}
        if isinstance(result, dict) and "value" in result:
            return str(result["value"])
        return str(result)

    def register_domain(
        self,
        domain: str,
        *,
        term: int = 12,
        confirm: bool = False,
        contacts: Optional[Dict[str, Any]] = None,
        nameservers: Optional[list[str]] = None,
    ) -> Dict[str, Any]:
        """Register ``domain`` via Metaname's ``register_domain_name`` method.

        ``confirm`` must be set to ``True`` — registration consumes test credit
        on the test API or incurs a real charge on the production API, so the
        guardrail prevents accidental calls from automation or agent workflows.

        Internally calls :meth:`check_domain` and raises :class:`MetanameError`
        unless the API explicitly returns ``"available"``.  This is a
        **safe-by-default** guardrail — any other string (including new
        statuses Metaname may introduce in future) is treated as *not
        available* to avoid spending money on unintended registrations.

        Parameters
        ----------
        domain:
            Domain name to register (trailing dot is stripped).
        term:
            Registration term in months. Must be a positive integer.
            For most non-NZ TLDs Metaname only accepts 12-month increments
            (12, 24, 36 … 120).  For ``.nz`` names 1–120 months is
            accepted.  See https://metaname.net/api/1.1/doc#Registration_terms
            for the full registry-level rules.  This method validates the
            value is an integer ≥ 1 but does not enforce specific increments.
        confirm:
            Safety guardrail — must be ``True``.
        contacts:
            Contact block keyed by role (``registrant``, ``admin``,
            ``technical``). When ``None``, built from
            :meth:`_default_contact`.
        nameservers:
            Optional list of name server hostnames.  When ``None``, a JSON
            ``null`` is sent to the API, which Metaname interprets as *use
            Metaname hosted DNS* — this is the documented default behaviour.
        """

        if not confirm:
            raise ValueError(
                "register_domain() requires confirm=True. "
                "Registration consumes test credit or incurs a production charge."
            )

        if not isinstance(term, int) or term < 1:
            raise ValueError(
                f"term must be a positive integer, got {term!r}. "
                "Check Metaname's current pricing for accepted term lengths."
            )

        domain = _strip_trailing_dot(domain)
        check = self.check_domain(domain)
        if check != "available":
            raise MetanameError(
                f"Domain '{domain}' is not available for registration "
                f"(check_availability returned {check!r})."
            )

        if contacts is None:
            contacts = self._registration_contacts()
        result = self._rpc(
            "register_domain_name", [domain, term, contacts, nameservers]
        )
        return {"domain": domain, "status": "registered", "result": result}

    def _registration_contacts(self) -> Dict[str, Any]:
        """Build the registrant/admin/technical contact block for registration."""

        payload = self._default_contact().to_payload()
        return {role: payload for role in ("registrant", "admin", "technical")}

    @staticmethod
    def _default_contact() -> Contact:
        name = _resolve_required_secret("METANAME_CONTACT_NAME")
        email = _resolve_required_secret("METANAME_CONTACT_EMAIL")
        phone_country = _resolve_required_secret("METANAME_CONTACT_PHONE_COUNTRY")
        phone_area = _resolve_required_secret("METANAME_CONTACT_PHONE_AREA")
        phone_local = _resolve_required_secret("METANAME_CONTACT_PHONE_LOCAL")
        address_line1 = _resolve_required_secret("METANAME_CONTACT_ADDRESS_LINE1")
        city = _resolve_required_secret("METANAME_CONTACT_CITY")
        postal_code = _resolve_required_secret("METANAME_CONTACT_POSTAL_CODE")
        country_code = _resolve_required_secret("METANAME_CONTACT_COUNTRY_CODE")

        org = _get_env_or_secret("METANAME_CONTACT_ORG")
        address_line2 = _get_env_or_secret("METANAME_CONTACT_ADDRESS_LINE2")
        region = _get_env_or_secret("METANAME_CONTACT_REGION")

        return Contact(
            name=name,
            email=email,
            organisation=org,
            phone_country_code=phone_country,
            phone_area_code=phone_area,
            phone_local_number=phone_local,
            address_line1=address_line1,
            address_line2=address_line2,
            city=city,
            region=region,
            postal_code=postal_code,
            country_code=country_code,
        )


def _strip_trailing_dot(domain: str) -> str:
    """Return ``domain`` without a trailing dot."""

    return domain[:-1] if domain.endswith(".") else domain


def _get_env_or_secret(name: str, default: Optional[str] = None) -> Optional[str]:
    """Resolve ``name`` via 1Password with an environment-variable fallback."""

    try:
        return get_secret(name)
    except MissingSecret:
        return os.getenv(name, default)


def _resolve_required_secret(name: str) -> str:
    """Return the value of ``name`` from secrets or env, or raise MissingSecret.

    Used for contact fields that must be explicitly configured before a
    domain registration can proceed — no baked-in defaults.
    """

    try:
        value = get_secret(name)
    except MissingSecret:
        value = os.getenv(name) or ""
    if not value:
        raise MissingSecret(
            f"{name} is required for domain registration — "
            "set the env var or configure a secret resolver"
        )
    return value
