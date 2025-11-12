"""
Package exposing the pytest suites for documentation purposes.

The concrete test modules live outside the installable package (under
``modules/octodns_metaname/tests``). To make their docstrings available to
MkDocStrings, we load them dynamically and register them under the
``octodns_metaname.tests`` namespace.
"""

import sys
from importlib.abc import Loader
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType
from typing import cast

_BASE = Path(__file__).resolve().parent.parent.parent.parent / "tests"


def _load(module_name: str) -> ModuleType:
    spec = spec_from_file_location(
        f"octodns_metaname.tests.{module_name}", _BASE / f"{module_name}.py"
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load test module: {module_name}")
    module = module_from_spec(spec)
    loader = cast(Loader, spec.loader)
    loader.exec_module(module)
    sys.modules[f"octodns_metaname.tests.{module_name}"] = module
    return module


test_client = _load("test_client")
test_provider = _load("test_provider")
test_secrets = _load("test_secrets")

__all__ = ["test_client", "test_provider", "test_secrets"]
