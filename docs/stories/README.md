# User Stories

Usage patterns and workflows for octodns-metaname.

## Story Format

Each story follows the format:

- **As a** {role}
- **I want to** {action}
- **So that** {benefit}

**Acceptance Criteria:**

- [ ] Criterion 1
- [ ] Criterion 2

## Current Stories

| ID | Title | Status |
|----|-------|--------|
| US-001 | DNS-as-Code workflow | Draft |
| US-002 | 1Password secret management | Draft |
| US-003 | CI/CD integration | Draft |

## Story: US-001 - DNS-as-Code workflow

**As a** DevOps engineer
**I want to** manage my Metaname DNS zones using YAML files
**So that** I can version control my DNS configuration and automate deployments

**Acceptance Criteria:**

- [ ] Can define DNS zones in YAML format
- [ ] Can sync zones to Metaname using octodns-sync
- [ ] Can preview changes before applying (octodns-sync --dry-run)
- [ ] Changes are idempotent (running sync twice has same effect)

**Notes:**

- This is the core use case for the module
- Enables GitOps workflows for DNS
- Supports team collaboration via pull requests

## Story: US-002 - 1Password secret management

**As a** security-conscious operator
**I want to** store Metaname API credentials in 1Password
**So that** secrets are not exposed in environment variables or config files

**Acceptance Criteria:**

- [ ] Can configure provider to use op-opsdevnz resolver
- [ ] API key and account reference fetched from 1Password at runtime
- [ ] No secrets logged or exposed in error messages
- [ ] Works in both local development and CI/CD

**Notes:**

- Optional feature (can still use environment variables)
- Requires installing `octodns-metaname[onepassword]`
- Integrates with op-opsdevnz module

## Story: US-003 - CI/CD integration

**As a** platform engineer
**I want to** run octodns-sync in my CI/CD pipeline
**So that** DNS changes are automatically deployed when merged to main

**Acceptance Criteria:**

- [ ] Can run octodns-sync in GitHub Actions / GitLab CI
- [ ] Secrets injected via CI/CD variables or 1Password
- [ ] Dry-run in pull request checks
- [ ] Actual sync on merge to main branch
- [ ] Clear error messages on failure

**Notes:**

- Should support both GitHub Actions and GitLab CI
- Need to document CI/CD setup examples
- Consider adding example workflow files

## Related

- [Functional Requirements](../specs/functional-requirements.md)
- [Design Decisions](../design/)
- [Getting Started](../index.md)
