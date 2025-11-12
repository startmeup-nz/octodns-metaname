# Contributing

Thanks for helping improve `octodns-metaname`! This document outlines the local
workflow we use when adding features or cutting a release.

## Development Environment

```bash
python -m venv venv
source venv/bin/activate
pip install -e .[dev]
```

We keep all tooling in `pyproject.toml`, so editable installs are enough for
linting, tests, type checks, and packaging.

## Common Tasks

| Task        | Command                                     |
|-------------|---------------------------------------------|
| Lint        | `ruff check src tests`                      |
| Type check  | `mypy src`                                  |
| Tests       | `pytest --color=yes --durations=10`         |
| Build       | `python -m build`                           |

You can also run the aggregated target:

```bash
make check
```

## Pull Requests

1. Create a feature branch.
2. Update/add tests for any behavioural changes.
3. Run `ruff`, `mypy`, and `pytest` locally (GitHub Actions enforces the same).
4. Update documentation (`README.md`, `CHANGELOG.md`, `RELEASING.md`, etc.) when
   behaviour, dependencies, or release steps change.
5. Open a PR and ensure the CI workflow is green.

## Cutting a Release

See [RELEASING.md](RELEASING.md) for the detailed checklist, including
TestPyPI and PyPI publication steps.
