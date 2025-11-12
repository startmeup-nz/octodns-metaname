"""Secret resolution helpers for the Metaname provider.

By default secrets are pulled straight from environment variables. Users can
optionally register a resolver (e.g., 1Password, Vault) via
``set_secret_resolver`` or the ``OCTODNS_METANAME_SECRET_RESOLVER`` env var,
which should contain ``module:function``. The resolver receives the secret name
and the value of ``<NAME>_REF`` (if present) and should return the resolved
secret or ``None`` when it cannot help.
"""

import importlib
import os
from typing import Callable, Optional, cast

Resolver = Callable[[str, Optional[str]], Optional[str]]

_secret_resolver: Optional[Resolver] = None
_resolver_loaded = False


class MissingSecret(RuntimeError):
    """Raised when a required secret cannot be resolved."""


def set_secret_resolver(resolver: Optional[Resolver]) -> None:
    """Register a custom secret resolver (or clear when ``None``)."""

    global _secret_resolver, _resolver_loaded
    _secret_resolver = resolver
    _resolver_loaded = True


def _ensure_resolver_loaded() -> None:
    global _secret_resolver, _resolver_loaded
    if _resolver_loaded:
        return
    path = os.getenv("OCTODNS_METANAME_SECRET_RESOLVER")
    if path:
        module_name, _, attr = path.partition(":")
        if not attr:
            raise MissingSecret(
                "OCTODNS_METANAME_SECRET_RESOLVER must be in 'module:function' format"
            )
        module = importlib.import_module(module_name)
        resolver = getattr(module, attr)
        if not callable(resolver):
            raise MissingSecret(
                f"Resolver '{attr}' inside {module_name} must be callable; got {type(resolver)!r}"
            )
        _secret_resolver = cast(Resolver, resolver)
    _resolver_loaded = True


def get_secret(name: str) -> str:
    """Resolve a secret via env var or configured resolver."""

    direct = os.getenv(name)
    if direct:
        return direct

    ref_env = f"{name}_REF"
    reference = os.getenv(ref_env)

    _ensure_resolver_loaded()

    if _secret_resolver:
        resolved = _secret_resolver(name, reference)
        if resolved:
            return resolved

    if reference:
        raise MissingSecret(
            f"Secret reference provided via {ref_env} but no resolver returned a value"
        )

    raise MissingSecret(f"Missing secret: {name}")


def clear_secret_resolver() -> None:
    """Testing helper to reset resolver state."""

    global _secret_resolver, _resolver_loaded
    _secret_resolver = None
    _resolver_loaded = False
