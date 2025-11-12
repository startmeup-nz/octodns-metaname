"""OctoDNS provider implementation backed by the Metaname API."""

import logging
import time
from typing import Any, Callable, Dict, Iterable, Optional, Tuple

from .client import (
    TEST_API_URL,
    MetanameAPIError,
    MetanameClient,
    MetanameError,
    ZoneRecord,
    _strip_trailing_dot,
)

__all__ = [
    "MetanameAPIError",
    "MetanameClient",
    "MetanameError",
    "MetanameProvider",
    "TEST_API_URL",
    "ZoneRecord",
]

try:  # pragma: no cover - exercised when octodns is installed
    from octodns.provider.base import BaseProvider  # type: ignore
    from octodns.record import Record as OctoDNSRecord  # type: ignore
except ImportError:  # pragma: no cover - default in test environment

    class BaseProvider:  # type: ignore
        """Fallback shim used when OctoDNS is not available locally."""

        def __init__(self, id: str, *_, **__):  # noqa: D401 - simple shim
            self.id = id
            self.log = logging.getLogger(f"octodns.provider.{id}")

    class OctoDNSRecord:  # type: ignore
        @staticmethod
        def new(*_, **__):  # noqa: D401
            raise RuntimeError(
                "octodns is required to construct records; install the 'octodns' extra"
            )


__version__ = "0.1.0"


def _ensure_trailing_dot(value: str) -> str:
    if not value:
        return value
    return value if value.endswith(".") else f"{value}."


def _normalize_value(value: Any) -> Any:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped
    return value


def _escape_txt(value: str) -> str:
    return value.replace(";", r"\;")


def _unescape_txt(value: str) -> str:
    return value.replace(r"\;", ";")


class MetanameProvider(BaseProvider):
    """OctoDNS provider that proxies calls through :class:`MetanameClient`."""

    log = logging.getLogger("octodns_metaname.MetanameProvider")
    SUPPORTS_GEO = False
    SUPPORTS_DYNAMIC = False
    SUPPORTS = {"A", "AAAA", "CNAME", "MX", "NS", "TXT", "CAA"}

    def __init__(
        self,
        id: str,
        *,
        client: Optional[MetanameClient] = None,
        base_url: Optional[str] = None,
        retries: int = 3,
        retry_backoff: float = 1.0,
        sleep: Callable[[float], None] = time.sleep,
        record_factory: Optional[Callable[..., Any]] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(id, **kwargs)
        self.client = client or MetanameClient(base_url=base_url or TEST_API_URL)
        self.retries = max(1, retries)
        self.retry_backoff = max(0.0, retry_backoff)
        self._sleep = sleep
        self._record_factory = record_factory or OctoDNSRecord.new
        self._zone_cache: Dict[str, Dict[Tuple[str, str, str, Optional[int]], ZoneRecord]] = {}

    # -- OctoDNS hooks -------------------------------------------------

    def populate(self, zone: Any, target: bool = False, lenient: bool = False) -> bool:
        domain = _strip_trailing_dot(getattr(zone, "name", ""))
        if not domain:
            raise ValueError("Zone name is required for populate")

        try:
            records = self._with_retries(self.client.list_zone_records, domain)
        except MetanameError as exc:
            if "Domain name not found" in str(exc):
                self.log.info("Metaname returned missing domain for %s; treating as empty", domain)
                records = []
            else:
                raise
        cache: Dict[Tuple[str, str, str, Optional[int]], ZoneRecord] = {}
        added = False

        aggregated: Dict[Tuple[str, str, Optional[int]], Dict[str, Any]] = {}

        for record in records:
            cache[self._cache_key(record)] = record
            data = self._metaname_to_octodns(record)
            if not data:
                continue
            if "value" in data:
                normalized = _normalize_value(data["value"])
                if normalized in (None, ""):
                    self.log.warning(
                        "Skipping record %s (%s) with empty value from Metaname",
                        record.name,
                        record.rtype,
                    )
                    continue
                data["value"] = normalized
            if "values" in data:
                cleaned = []
                for item in data["values"]:
                    normalized = _normalize_value(item)
                    if normalized in (None, ""):
                        continue
                    cleaned.append(normalized)
                if not cleaned:
                    self.log.warning(
                        "Skipping record %s (%s) with empty values list from Metaname",
                        record.name,
                        record.rtype,
                    )
                    continue
                data["values"] = cleaned
            owner = (record.name or "").rstrip(".")
            if not owner or owner == "@":
                owner = ""
            elif owner == domain:
                owner = ""
            elif owner.endswith(f".{domain}"):
                owner = owner[: -(len(domain) + 1)]
            rtype = data.get("type", record.rtype)
            ttl = data.get("ttl")
            key = (owner, rtype, ttl)

            existing = aggregated.get(key)
            if existing:
                if "values" in data:
                    existing_values = existing.setdefault("values", [])
                    for item in data.get("values", []):
                        if item not in existing_values:
                            existing_values.append(item)
                if "value" in data:
                    existing["value"] = data["value"]
            else:
                aggregated[key] = dict(data)

        for (owner, _rtype, _ttl), record_data in aggregated.items():
            if "value" in record_data:
                normalized = _normalize_value(record_data["value"])
                if normalized in (None, ""):
                    self.log.warning(
                        "Skipping aggregated record %s (%s) with empty value",
                        owner or "@",
                        record_data.get("type"),
                    )
                    continue
                record_data["value"] = normalized
            if "values" in record_data:
                cleaned = []
                for item in record_data["values"]:
                    normalized = _normalize_value(item)
                    if normalized in (None, ""):
                        continue
                    cleaned.append(normalized)
                if not cleaned:
                    self.log.warning(
                        "Skipping aggregated record %s (%s) with empty values list",
                        owner or "@",
                        record_data.get("type"),
                    )
                    continue
                record_data["values"] = cleaned
            if "value" not in record_data and "values" not in record_data:
                self.log.warning(
                    "Skipping aggregated record %s (%s) with no value payload",
                    owner or "@",
                    record_data.get("type"),
                )
                continue
            created = self._record_factory(zone, owner, record_data, source=self)
            zone.add_record(created, lenient=lenient)
            added = True

        self._zone_cache[domain] = cache
        return added

    def apply(self, plan: Any) -> bool:
        changes = getattr(plan, "changes", [])
        if not changes:
            return False

        desired = getattr(plan, "desired", None)
        existing = getattr(plan, "existing", None)
        zone_name = getattr(desired, "name", None) or getattr(existing, "name", None)
        if not zone_name:
            raise ValueError("Plan is missing zone metadata")
        domain = _strip_trailing_dot(zone_name)

        for change in changes:
            action = change.__class__.__name__.lower()
            if action == "create":
                self._apply_create(domain, change.new)
            elif action == "delete":
                self._apply_delete(domain, change.existing)
            elif action == "update":
                # Metaname exposes ``update_dns_record`` but the OctoDNS plan
                # model already represents updates as delete+create pairs, so
                # reuse that flow for now.
                self._apply_delete(domain, change.existing)
                self._apply_create(domain, change.new)
            else:
                raise ValueError(f"Unsupported change action: {action}")

        self._zone_cache.pop(domain, None)
        return True

    # -- Internal helpers ----------------------------------------------

    def _apply_create(self, domain: str, record: Any) -> None:
        for zone_record in self._octodns_record_to_metaname(record):
            self._with_retries(self.client.create_zone_record, domain, zone_record)

    def _apply_delete(self, domain: str, record: Any) -> None:
        cache = self._ensure_cache(domain)
        for zone_record in self._octodns_record_to_metaname(record):
            key = self._cache_key(zone_record)
            cached = cache.get(key)
            if cached and cached.reference:
                self._with_retries(self.client.delete_zone_record, domain, cached.reference)

    def _metaname_to_octodns(self, record: ZoneRecord) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"type": record.rtype, "ttl": record.ttl}
        if record.rtype == "MX":
            payload["values"] = [
                {
                    "exchange": _ensure_trailing_dot(record.data),
                    "preference": record.aux if record.aux is not None else 0,
                }
            ]
        elif record.rtype == "CAA":
            payload["values"] = [record.data]
        elif record.rtype == "TXT":
            payload["values"] = [_escape_txt(record.data)]
        elif record.rtype in ("CNAME", "NS"):
            payload["value"] = _ensure_trailing_dot(record.data)
        else:
            payload["values"] = [record.data]
        return payload

    def _octodns_record_to_metaname(self, record: Any) -> Iterable[ZoneRecord]:
        rtype = getattr(record, "rtype", getattr(record, "_type", None))
        if rtype is None:
            raise ValueError("Record missing type information")
        rtype = rtype.upper()
        name = getattr(record, "name", "@") or "@"
        ttl = getattr(record, "ttl", None) or 3600

        if rtype == "MX":
            for value in getattr(record, "values", []):
                if isinstance(value, dict):
                    exchange = value.get("exchange") or value.get("value")
                    preference = value.get("preference") or value.get("priority")
                else:
                    exchange = getattr(value, "exchange", getattr(value, "value", str(value)))
                    preference = getattr(value, "preference", getattr(value, "priority", None))
                yield ZoneRecord(
                    reference=None,
                    name=name,
                    rtype="MX",
                    data=_ensure_trailing_dot(str(exchange)),
                    ttl=ttl,
                    aux=int(preference) if preference is not None else None,
                )
        elif rtype == "TXT":
            for value in getattr(record, "values", []):
                yield ZoneRecord(
                    reference=None,
                    name=name,
                    rtype="TXT",
                    data=_unescape_txt(str(value)),
                    ttl=ttl,
                )
        elif rtype == "CAA":
            for value in getattr(record, "values", []):
                if isinstance(value, dict):
                    flags = str(value.get("flags", 0))
                    tag = value.get("tag", "") or ""
                    caa_value = value.get("value", "") or ""
                    parts = [flags]
                    if tag:
                        parts.append(tag)
                    if caa_value:
                        parts.append(caa_value)
                    data = " ".join(parts)
                else:
                    data = str(value)
                yield ZoneRecord(
                    reference=None,
                    name=name,
                    rtype="CAA",
                    data=data,
                    ttl=ttl,
                )
        else:
            value = getattr(record, "value", None)
            if value is None:
                values = getattr(record, "values", [])
                value = values[0] if values else ""
            value = _normalize_value(value)
            data = _ensure_trailing_dot(str(value)) if rtype in {"CNAME", "NS"} else str(value)
            yield ZoneRecord(
                reference=None,
                name=name,
                rtype=rtype,
                data=data,
                ttl=ttl,
            )

    def _cache_key(self, record: ZoneRecord) -> Tuple[str, str, str, Optional[int]]:
        return (record.name, record.rtype, record.data, record.aux)

    def _with_retries(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        last_error: Optional[Exception] = None
        for attempt in range(1, self.retries + 1):
            try:
                return func(*args, **kwargs)
            except MetanameError as exc:
                last_error = exc
                if attempt == self.retries:
                    raise
                self._sleep(self.retry_backoff * attempt)
        if last_error is not None:
            raise last_error
        raise RuntimeError("Retry loop exited without executing function")

    def _ensure_cache(self, domain: str) -> Dict[Tuple[str, str, str, Optional[int]], ZoneRecord]:
        cache = self._zone_cache.get(domain)
        if cache is None:
            records = self._with_retries(self.client.list_zone_records, domain)
            cache = {self._cache_key(record): record for record in records}
            self._zone_cache[domain] = cache
        return cache


__all__ = ["MetanameProvider"]
