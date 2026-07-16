# octodns-metaname

OctoDNS provider for the [Metaname](https://metaname.net) DNS API, originally
bootstrapped from the upstream [`octodns-template`](https://github.com/octodns/octodns-template).
Use it to run a DNS-as-Code workflow with OctoDNS for any zones you host at
Metaname.

## Installation

PyPI release:

```bash
pip install octodns-metaname
```

If you rely on the OpsDev.nz 1Password resolver, install the optional extra:

```bash
pip install octodns-metaname[onepassword]
```

Editable install for local development:

```bash
python -m venv venv && source venv/bin/activate
pip install -e .[dev]
```

## OctoDNS integration

Once installed, the provider is available via the entry point `metaname`. Sample
`config.yaml` fragment:

```yaml
providers:
  metaname-test:
    class: octodns_metaname.MetanameProvider
    base_url: https://test.metaname.net/api/1.1
```

Populate/apply workflows follow the standard OctoDNS CLI tools. Consult the
[OctoDNS docs](https://github.com/octodns/octodns/wiki/Usage) for full CLI
details.

### Domain lifecycle CLI

Domain registration is separate from DNS record management. The CLI defaults
to Metaname's test API:

```bash
octodns-metaname check example.nz
octodns-metaname list
octodns-metaname register example.nz --term 12 --confirm
```

Pass `--production` before the command to use the live API. Registration
requires `--confirm` because it consumes test credit or incurs a production
charge. Omitting `--nameserver` selects Metaname hosted DNS.

### Optional registration during apply

The provider can register a missing domain immediately before applying its
records. This is disabled by default and should normally be enabled only for
the test API:

```yaml
providers:
  metaname-test:
    class: octodns_metaname.MetanameProvider
    base_url: https://test.metaname.net/api/1.1
    auto_register_domains: true
    registration_term: 12
```

The dry-run only reports the proposed records. Registration happens during the
subsequent `octodns-sync --doit` apply. For the production API, an additional
`allow_production_registration: true` safeguard is required. Prefer the CLI for
an explicit availability check and registration before enabling production
automation.

### Secret resolution

By default the provider reads secrets directly from environment variables such
as `METANAME_ACCOUNT_REF` and `METANAME_API_TOKEN`. If your workflow stores
values in a vault (e.g., 1Password) you can register a resolver using:

```python
from octodns_metaname import secrets

def resolve(name: str, reference: str | None) -> str | None:
    ...

secrets.set_secret_resolver(resolve)
```

For CLI usage set `OCTODNS_METANAME_SECRET_RESOLVER="module:function"` so the
resolver is loaded automatically. OpsDev.nz deployments point this at
`op_opsdevnz.octodns_hooks:resolve`, which returns values directly from the
1Password Service Account SDK/CLI.

## Development

```bash
python -m venv venv && source venv/bin/activate
pip install -e .[dev]
ruff check src tests
mypy src
pytest --maxfail=1
```

The repo includes a GitHub Actions workflow that runs linting, type checking,
tests, and a build on every push.

## Releasing

See [RELEASING.md](RELEASING.md) for the full TestPyPI → PyPI checklist.

## License

Apache-2.0 © OpsDev.nz
