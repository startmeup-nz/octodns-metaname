"""Tests for the Metaname domain lifecycle CLI."""

import json

import pytest

from octodns_metaname import cli


class FakeClient:
    def __init__(self):
        self.calls = []

    def check_domain(self, domain, *, source_ip=None):
        self.calls.append(("check", domain, source_ip))
        return "available"

    def list_domains(self):
        self.calls.append(("list",))
        return [{"name": "example.nz", "status": "active"}]

    def register_domain(self, domain, *, term, confirm, nameservers=None):
        self.calls.append(("register", domain, term, confirm, nameservers))
        return {"domain": domain, "status": "registered"}


def test_check_command(monkeypatch, capsys):
    client = FakeClient()
    monkeypatch.setattr(cli, "_client", lambda production: client)

    assert cli.main(["check", "example.nz."]) == 0

    assert client.calls == [("check", "example.nz.", None)]
    assert json.loads(capsys.readouterr().out) == {
        "domain": "example.nz",
        "status": "available",
    }


def test_list_command_uses_production_when_requested(monkeypatch, capsys):
    client = FakeClient()
    selected = []

    def fake_client(production):
        selected.append(production)
        return client

    monkeypatch.setattr(cli, "_client", fake_client)

    assert cli.main(["--production", "list"]) == 0

    assert selected == [True]
    assert client.calls == [("list",)]
    assert json.loads(capsys.readouterr().out)[0]["name"] == "example.nz"


def test_register_command_requires_confirm():
    with pytest.raises(SystemExit):
        cli.main(["register", "example.nz"])


def test_register_command(monkeypatch, capsys):
    client = FakeClient()
    monkeypatch.setattr(cli, "_client", lambda production: client)

    assert (
        cli.main(
            [
                "register",
                "example.nz",
                "--term",
                "6",
                "--confirm",
                "--nameserver",
                "ns1.example.nz",
                "--nameserver",
                "ns2.example.nz",
            ]
        )
        == 0
    )

    assert client.calls == [
        (
            "register",
            "example.nz",
            6,
            True,
            ["ns1.example.nz", "ns2.example.nz"],
        )
    ]
    assert json.loads(capsys.readouterr().out)["status"] == "registered"
