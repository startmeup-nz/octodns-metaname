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
    address_line1: str = "123 Test Street"
    address_line2: Optional[str] = None
    city: str = "Wellington"
    region: Optional[str] = None
    postal_code: str = "6011"
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

        payload = {
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

    @staticmethod
    def _default_contact() -> Contact:
        try:
            email = get_secret("METANAME_CONTACT_EMAIL")
        except MissingSecret:
            email = os.getenv("METANAME_CONTACT_EMAIL", "dns-ops@example.com")

        name = (
            _get_env_or_secret("METANAME_CONTACT_NAME", default="Metaname DNS Contact")
            or "Metaname DNS Contact"
        )
        org = _get_env_or_secret("METANAME_CONTACT_ORG")
        phone_country = (
            _get_env_or_secret("METANAME_CONTACT_PHONE_COUNTRY", default="64") or "64"
        )
        phone_area = _get_env_or_secret("METANAME_CONTACT_PHONE_AREA")
        phone_local = (
            _get_env_or_secret("METANAME_CONTACT_PHONE_LOCAL", default="2345678") or "2345678"
        )

        return Contact(
            name=name,
            email=email,
            organisation=org,
            phone_country_code=phone_country,
            phone_area_code=phone_area,
            phone_local_number=phone_local,
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
