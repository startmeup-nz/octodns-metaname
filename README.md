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
