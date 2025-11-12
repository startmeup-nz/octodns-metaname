# octodns-metaname (prototype)

Experimental OctoDNS provider for the [Metaname](https://metaname.net) DNS API.
This package originates from the upstream [`octodns-template`](https://github.com/octodns/octodns-template)
scaffold and is now maintained as part of the public OpsDev.nz automation toolkit.

## Local setup

```bash
cd modules/octodns_metaname
python -m venv .venv && source .venv/bin/activate
pip install -e .[dev]
```

## Testing

```bash
pytest
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

Populate/apply workflows follow the standard OctoDNS CLI tools.

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
resolver is loaded automatically. The OpsDev.nz deployment points this at
`op_opsdevnz.octodns_hooks:resolve` which unwraps `op://…` references via the
1Password CLI.
