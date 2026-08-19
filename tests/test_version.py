"""Tests for package metadata consistency."""

from importlib.metadata import version


def test_version_consistency():
    """Ensure __version__ matches what pyproject.toml declares."""
    from octodns_metaname import __version__

    assert __version__ == version("octodns-metaname")
