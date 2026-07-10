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
| DD-005 | Domain registration safety guardrail | Accepted |
| DD-006 | Domain registration in MetanameClient vs MetanameProvider | Accepted |

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

## DD-005 - Domain registration safety guardrail

**Context:** Domain registration costs real money and is irreversible. Adding `register_domain()` to `MetanameClient` brings this mutating operation into a library used by CI pipelines and AI agent workflows.

**Options:**

1. Trust the caller — no guardrails, just document the danger
2. Require explicit `confirm=True` — raise `ValueError` otherwise
3. Use a separate class or client for registration (API surface segregation)

**Decision:** Require `confirm=True`.

**Rationale:**

- Domain registration is the most expensive and irreversible operation the module performs
- A `ValueError` on `confirm=False` is a loud, discoverable failure at development time, not a silent mistake at runtime
- The guardrail survives refactoring (e.g. if an agent wraps `register_domain()` in a loop) because every call site must opt in
- Consistent with the principle that mutating operations with financial cost should require explicit intent

**Consequences:**

- Every caller must pass `confirm=True` — a minor ergonomic cost
- The guardrail is enforced in code, not just documentation, reducing the risk of accidental CI/automation registrations
- The `register_domain()` method also internally calls `check_domain()` and refuses to proceed if the domain is not available

## DD-006 - Domain registration in MetanameClient vs MetanameProvider

**Context:** Domain registration (`register_domain_name` RPC) and domain listing (`domain_names` RPC) are Metaname API operations that sit outside the OctoDNS provider contract. We needed to decide where these methods belong in the module's class hierarchy.

**Options:**

1. Add to `MetanameProvider` — the OctoDNS provider class
2. Add to `MetanameClient` — the lower-level JSON-RPC client wrapper
3. Create a separate `MetanameRegistrar` class

**Decision:** Add domain lifecycle methods to `MetanameClient`.

**Rationale:**

- `MetanameProvider` implements the OctoDNS `BaseProvider` interface (`populate`, `apply`, `SUPPORTS`). Domain registration is not a DNS zone operation — it's a Metaname-specific API call with no OctoDNS counterpart. Mixing it into the provider would blur the separation of concerns.
- `MetanameClient` is the thin JSON-RPC wrapper that already owns authentication, secret resolution, and raw API calls. Registration methods (`check_domain_name`, `register_domain_name`, `domain_names`) are just more RPC methods — they fit naturally alongside `dns_zone`, `create_dns_record`, etc.
- The standalone `scripts/metaname_register.py` script had its own duplicated secret resolution and HTTP logic. The `MetanameClient` already has all that plumbing — putting registration there eliminates the duplication.
- A separate `MetanameRegistrar` class would add a new concept for only 3 methods, creating unnecessary API surface fragmentation.

**Consequences:**

- `MetanameClient` now has two concerns (DNS zone management + domain lifecycle), but both are thin wrappers over Metaname JSON-RPC methods that share the same auth and networking layer
- Consumers who only need DNS zone management via the provider are unaffected — provider-only usage doesn't instantiate `MetanameClient` directly
- `MetanameProvider` stays focused on the OctoDNS contract, preserving the clean OctoDNS provider surface

## Related

- [Functional Requirements](../specs/functional-requirements.md)
- [Non-Functional Requirements](../specs/NFR.md)
- [User Stories](../stories/)
