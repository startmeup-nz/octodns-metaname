# Changelog

All notable changes to this project will be documented in this file.

## [0.2.1] - 2026-07-16
### Added
- `octodns-metaname` CLI for checking, listing, and explicitly registering domains.
- Opt-in `auto_register_domains` provider setting for registering missing domains
  during apply, with an additional production-only safeguard.

### Changed
- Registration messages now distinguish test credit from production charges.

## [0.2.0] - 2026-07-10
### Added
- `MetanameClient.check_domain()` — check domain availability via `check_domain_name` RPC.
- `MetanameClient.register_domain()` — register a domain via `register_domain_name` RPC with a `confirm=True` safety guardrail that prevents accidental registration from automation workflows.
- `MetanameClient.list_domains()` — list all domains under the authenticated account.
- `MetanameClient._registration_contacts()` — build contact block from `_default_contact()` for domain registration.
- Comprehensive test coverage for all new domain lifecycle methods.

### Changed
- `scripts/metaname_register.py` is now a thin deprecation wrapper around `MetanameClient.register_domain()`.

## [0.1.1] - 2025-11-13
### Added
- README, CONTRIBUTING, RELEASING, CODEOWNERS, SECURITY, CODE_OF_CONDUCT, Makefile, requirements, and GitHub Actions CI so the repo matches other OpsDev packages.
- GitHub workflow now runs lint, type-checking, tests, and build on every push.

### Changed
- Expanded `pyproject.toml` metadata, optional extras, and tooling config; fixed type hints and added `types-requests`.
- Updated client defaults to neutral placeholders and ensured the resolver import is type-safe.
- License now declared via SPDX string + `license-files`, removing setuptools warnings.

## [0.1.0] - 2025-11-13
### Added
- Initial extraction from the OpsDev.nz monorepo, including the Metaname OctoDNS
  provider, client, secrets helper, and test suite.
- Packaging metadata and docs for publishing to TestPyPI/PyPI.
- Optional `[onepassword]` extra to pull in `op-opsdevnz` when a resolver is
  needed.
