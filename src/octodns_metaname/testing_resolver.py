"""Helpers used in the octodns-metaname test suite."""

from typing import Optional


def resolver(name: str, reference: Optional[str]) -> Optional[str]:
    if reference == "ref-env":
        return "resolved-from-env"
    return None
