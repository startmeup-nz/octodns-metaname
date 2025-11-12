"""Behavioural tests for the OctoDNS Metaname provider wrapper."""

from dataclasses import dataclass

import pytest

from octodns_metaname import MetanameProvider
from octodns_metaname.client import MetanameError, ZoneRecord


class DummyZone:
    """Simple stand-in for an OctoDNS zone used during tests."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.records = []

    def add_record(self, record, lenient: bool = False) -> None:
        self.records.append((record, lenient))


def fake_record_factory(zone, name, data, source):
    return {"zone": zone.name, "name": name, "data": data, "source": source.id}


class FakeClient:
    """Fake Metaname client that records actions for assertions."""

    def __init__(self, records=None):
        self.records = records or []
        self.actions = []

    def list_zone_records(self, domain):
        self.actions.append(("list", domain))
        return list(self.records)

    def create_zone_record(self, domain, record):
        self.actions.append(("create", domain, record))

    def delete_zone_record(self, domain, reference):
        self.actions.append(("delete", domain, reference))


@dataclass
class FakeRecord:
    """Minimal record object mirroring the attributes OctoDNS uses."""

    name: str
    rtype: str
    ttl: int
    values: list
    value: str | None = None

    @property
    def _type(self):
        return self.rtype


class Create:
    """Change wrapper mirroring OctoDNS' create action."""

    def __init__(self, new):
        self.new = new


class Delete:
    """Change wrapper mirroring OctoDNS' delete action."""

    def __init__(self, existing):
        self.existing = existing


class Update:
    """Change wrapper mirroring OctoDNS' update action."""

    def __init__(self, existing, new):
        self.existing = existing
        self.new = new


class DummyPlan:
    """Plan fixture that supplies the attributes the provider expects."""

    def __init__(self, changes, zone_name: str):
        self.changes = changes
        self.desired = type("Zone", (), {"name": zone_name})()


def test_populate_builds_zone_cache():
    zone_record = ZoneRecord(
        reference="rec-1",
        name="@",
        rtype="MX",
        data="mx1.forwardemail.net.",
        ttl=3600,
        aux=10,
    )
    client = FakeClient(records=[zone_record])
    provider = MetanameProvider(
        "metaname",
        client=client,
        record_factory=fake_record_factory,
        sleep=lambda _: None,
    )

    zone = DummyZone("opstest.nz.")
    added = provider.populate(zone)

    assert added is True
    assert client.actions == [("list", "opstest.nz")]
    assert len(zone.records) == 1
    assert zone.records[0][0]["name"] == ""
    assert zone.records[0][0]["data"]["values"][0]["exchange"] == "mx1.forwardemail.net."
    cache = provider._zone_cache["opstest.nz"]
    assert provider._cache_key(zone_record) in cache


def test_populate_merges_duplicate_rrsets():
    zone_records = [
        ZoneRecord(
            reference="rec-1",
            name="@",
            rtype="MX",
            data="mx1.forwardemail.net.",
            ttl=3600,
            aux=10,
        ),
        ZoneRecord(
            reference="rec-2",
            name="@",
            rtype="MX",
            data="mx2.forwardemail.net.",
            ttl=3600,
            aux=20,
        ),
    ]
    client = FakeClient(records=zone_records)
    provider = MetanameProvider(
        "metaname",
        client=client,
        record_factory=fake_record_factory,
        sleep=lambda _: None,
    )

    zone = DummyZone("opstest.nz.")
    added = provider.populate(zone)

    assert added is True
    assert client.actions == [("list", "opstest.nz")]
    record_payload = zone.records[0][0]["data"]
    exchanges = {v["exchange"] for v in record_payload["values"]}
    assert exchanges == {"mx1.forwardemail.net.", "mx2.forwardemail.net."}


def test_populate_handles_missing_domain(monkeypatch):
    class MissingClient(FakeClient):
        def list_zone_records(self, domain):
            raise MetanameError("Domain name not found")

    client = MissingClient()
    provider = MetanameProvider(
        "metaname",
        client=client,
        record_factory=fake_record_factory,
        sleep=lambda _: None,
    )

    zone = DummyZone("missing.nz.")
    added = provider.populate(zone)

    assert added is False
    assert zone.records == []


def test_populate_skips_blank_records(caplog):
    zone_record = ZoneRecord(
        reference="rec-empty",
        name="@",
        rtype="A",
        data="",
        ttl=3600,
    )
    client = FakeClient(records=[zone_record])
    provider = MetanameProvider(
        "metaname",
        client=client,
        record_factory=fake_record_factory,
        sleep=lambda _: None,
    )

    caplog.set_level("WARNING")
    zone = DummyZone("opstest.nz.")
    added = provider.populate(zone)

    assert added is False
    assert zone.records == []
    assert client.actions == [("list", "opstest.nz")]
    assert any("empty value" in message for message in caplog.messages)


def test_apply_create_makes_api_calls():
    client = FakeClient()
    provider = MetanameProvider(
        "metaname",
        client=client,
        record_factory=fake_record_factory,
        sleep=lambda _: None,
    )
    record = FakeRecord(
        name="@",
        rtype="MX",
        ttl=3600,
        values=[{"exchange": "mx1.forwardemail.net.", "preference": 10}],
    )
    plan = DummyPlan([Create(record)], "opstest.nz.")

    provider.apply(plan)

    assert client.actions[0][0] == "create"
    _, domain, payload = client.actions[0]
    assert domain == "opstest.nz"
    assert payload.rtype == "MX"
    assert payload.data == "mx1.forwardemail.net."
    assert payload.aux == 10


def test_apply_delete_uses_cached_reference():
    zone_record = ZoneRecord(
        reference="rec-1",
        name="@",
        rtype="TXT",
        data="hello",
        ttl=3600,
    )
    client = FakeClient()
    provider = MetanameProvider(
        "metaname",
        client=client,
        record_factory=fake_record_factory,
        sleep=lambda _: None,
    )
    provider._zone_cache["opstest.nz"] = {provider._cache_key(zone_record): zone_record}

    record = FakeRecord(name="@", rtype="TXT", ttl=3600, values=["hello"])
    plan = DummyPlan([Delete(record)], "opstest.nz.")

    provider.apply(plan)

    assert client.actions == [("delete", "opstest.nz", "rec-1")]


def test_apply_delete_populates_cache_when_missing():
    zone_record = ZoneRecord(
        reference="rec-2",
        name="_dmarc",
        rtype="TXT",
        data="v=DMARC1",
        ttl=3600,
    )
    client = FakeClient(records=[zone_record])
    provider = MetanameProvider(
        "metaname",
        client=client,
        record_factory=fake_record_factory,
        sleep=lambda _: None,
    )

    record = FakeRecord(name="_dmarc", rtype="TXT", ttl=3600, values=["v=DMARC1"])
    plan = DummyPlan([Delete(record)], "opstest.nz.")

    provider.apply(plan)

    assert client.actions == [
        ("list", "opstest.nz"),
        ("delete", "opstest.nz", "rec-2"),
    ]


def test_retry_wrapper_retries_then_succeeds():
    client = FakeClient()
    provider = MetanameProvider(
        "metaname",
        client=client,
        retries=3,
        retry_backoff=0,
        sleep=lambda _: None,
    )

    attempts = {"count": 0}

    def flaky(*_args, **_kwargs):
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise MetanameError("temporary failure")
        return "ok"

    result = provider._with_retries(flaky)
    assert result == "ok"
    assert attempts["count"] == 3


def test_retry_wrapper_raises_last_error():
    provider = MetanameProvider(
        "metaname",
        client=FakeClient(),
        retries=2,
        retry_backoff=0,
        sleep=lambda _: None,
    )

    def always_fail():
        raise MetanameError("fail")

    with pytest.raises(MetanameError):
        provider._with_retries(always_fail)
