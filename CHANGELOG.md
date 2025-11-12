# Changelog

All notable changes to this project will be documented in this file.

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
