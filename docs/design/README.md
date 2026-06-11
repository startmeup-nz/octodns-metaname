# Design Decisions

Architecture and integration decisions for octodns-metaname.

## Decision Record Format

Each decision is documented with:

- **Context** - What problem are we solving?
- **Options** - What alternatives did we consider?
- **Decision** - What did we choose?
- **Rationale** - Why did we choose it?
- **Consequences** - What are the trade-offs?

## Current Decisions

| ID | Title | Status |
|----|-------|--------|
| DD-001 | pyproject.toml vs setup.py | Accepted |
| DD-002 | ruff vs black+isort | Accepted |
| DD-003 | 100% test coverage requirement | Accepted |
| DD-004 | Changelog management approach | Under Review |

## DD-001 - pyproject.toml vs setup.py

**Context:** OctoDNS template uses setup.py alongside pyproject.toml. Modern Python packaging supports pyproject.toml only.

**Options:**

1. Use setup.py + pyproject.toml (OctoDNS pattern)
2. Use pyproject.toml only (modern approach)

**Decision:** Use pyproject.toml only.

**Rationale:**

- Modern Python packaging standard (PEP 517/518)
- Simpler maintenance (one file vs two)
- Fully compatible with pip, build, and other tools
- No functional difference for end users

**Consequences:**

- Diverges from OctoDNS template pattern
- May need to update if OctoDNS adds setup.py-specific features

## DD-002 - ruff vs black+isort

**Context:** OctoDNS template uses black for formatting and isort for import sorting. Ruff provides both in a single, faster tool.

**Options:**

1. Use black + isort (OctoDNS pattern)
2. Use ruff (modern approach)

**Decision:** Use ruff.

**Rationale:**

- 10-100x faster than black+isort
- Single tool for linting, formatting, and import sorting
- Compatible with black formatting style
- Active development and community

**Consequences:**

- Diverges from OctoDNS ecosystem convention
- May require reformatting if contributing upstream

## DD-003 - 100% test coverage requirement

**Context:** Module bridges two upstream systems (OctoDNS and Metaname API). Higher reliability needed.

**Options:**

1. Standard coverage (80-90%)
2. 100% coverage (strict)

**Decision:** Require 100% test coverage.

**Rationale:**

- Two upstream dependencies increase risk
- DNS is critical infrastructure
- Catches edge cases and regressions
- Aligns with OctoDNS template pattern

**Consequences:**

- More test writing effort
- May need pragma: no cover for legitimate cases
- Slower development initially, faster maintenance long-term

## DD-004 - Changelog management approach

**Context:** Current manual CHANGELOG.md vs changelet pattern from OctoDNS template.

**Options:**

1. Manual CHANGELOG.md (current approach)
2. Changelet with .changelog/ directory (OctoDNS pattern)

**Decision:** Under review - leaning toward changelet.

**Rationale (for changelet):**

- Individual entries per PR (easier to review)
- Automatic compilation at release time
- Consistent with OctoDNS ecosystem
- Better traceability (each change has its own file)

**Consequences (if adopted):**

- Need to add changelet dependency
- Need to update CONTRIBUTING.md
- Migration of existing CHANGELOG.md entries
- Training for contributors

## Related

- [Functional Requirements](../specs/functional-requirements.md)
- [Non-Functional Requirements](../specs/NFR.md)
- [User Stories](../stories/)
