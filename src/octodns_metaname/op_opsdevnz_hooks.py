"""Optional 1Password resolver adapter for the Metaname provider.

This module is used through ``OCTODNS_METANAME_SECRET_RESOLVER``. The generic
secret-resolution implementation remains in :mod:`op_opsdevnz`; this adapter
translates the Metaname resolver interface into that API.
"""

import os
from typing import Optional, cast

from .secrets import MissingSecret


def _prefer_cli() -> bool:
    """Prefer the local CLI when no service-account token is configured."""

    return not bool(os.getenv("OP_SERVICE_ACCOUNT_TOKEN"))


def resolve(name: str, reference: Optional[str] = None) -> str:
    """Resolve a Metaname secret through the optional op-opsdevnz package."""

    try:
        from op_opsdevnz import resolve_secret  # type: ignore[import-untyped]
    except ImportError as exc:  # pragma: no cover - depends on optional extra
        raise MissingSecret(
            "The op-opsdevnz resolver is unavailable; install "
            "octodns-metaname[onepassword]"
        ) from exc

    if reference:
        resolution = resolve_secret(
            secret_ref=reference,
            env_override=name,
            prefer_cli=_prefer_cli(),
        )
    else:
        resolution = resolve_secret(
            secret_ref_env=f"{name}_REF",
            env_override=name,
            prefer_cli=_prefer_cli(),
        )
    return cast(str, resolution.value)
