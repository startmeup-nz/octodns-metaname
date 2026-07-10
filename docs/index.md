# octodns-metaname

OctoDNS provider for the [Metaname](https://metaname.net) DNS API.

- **Status:** Development
- **License:** Apache 2.0
- **Python:** 3.10+

## Overview

octodns-metaname is an [OctoDNS](https://github.com/octodns/octodns) provider that enables DNS-as-Code workflows for domains hosted with [Metaname](https://metaname.net), a New Zealand-based DNS registrar.

This provider allows you to manage your Metaname DNS zones using YAML configuration files, enabling version control, automated testing, and CI/CD integration for your DNS infrastructure.

## Features

- Full support for Metaname DNS record types
- Domain registration and availability checking
- Zone synchronization with OctoDNS
- Integration with 1Password for secret management (via op-opsdevnz)
- Comprehensive test coverage
- Type-safe implementation with mypy

## Installation

```bash
pip install octodns-metaname
```

For 1Password integration:

```bash
pip install octodns-metaname[onepassword]
```

## Quick Start

1. Create an OctoDNS configuration file (`config.yaml`):

```yaml
providers:
  config:
    class: octodns.provider.yaml.YamlProvider
    directory: ./zones
  
  metaname:
    class: octodns_metaname.provider.MetanameProvider
    api_key: env/METANAME_API_KEY
    account_reference: env/METANAME_ACCOUNT_REFERENCE
```

2. Create your zone file (`zones/example.com.yaml`):

```yaml
---
? ''
: type: A
  values:
    - 1.2.3.4
```

3. Sync your DNS:

```bash
octodns-sync --config-file=config.yaml
```

## Documentation

- **[Specifications](specs/)** - Functional and non-functional requirements
- **[Design Decisions](design/)** - Architecture and integration decisions
- **[User Stories](stories/)** - Usage patterns and workflows

## Development

```bash
# Install with dev dependencies
pip install -e .[dev]

# Run tests
pytest

# Run linting
ruff check .

# Build docs
zensical build
```

## Related

- [OctoDNS](https://github.com/octodns/octodns) - DNS-as-Code framework
- [Metaname](https://metaname.net) - New Zealand DNS registrar
- [OpsDev.nz](https://opsdev.nz) - Parent project
