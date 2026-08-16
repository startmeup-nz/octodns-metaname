# Agents — octodns_metaname

**Audience:** Contributors and AI assistants working on the octodns_metaname module.

## IMPORTANT: No Autonomous Commits

AI assistants must NOT commit changes to this repository. Always stage changes
and describe what was done, then wait for human review and confirmation before
committing.

## OctoDNS Workflow

- OctoDNS configurations live under `octodns/configs/` in the consuming project.
- Published zone files live under `octodns/zones/`.
- Load credentials via environment files (e.g. `env/metaname-test.env` or `env/metaname-prod.env`).
- Run `octodns-validate` / `octodns-sync` using configs in `octodns/configs/`.
- CI environments rely on `_REF` variables pointing to 1Password references.
- Secret resolution uses the optional `op-opsdevnz` integration:
  `OCTODNS_METANAME_SECRET_RESOLVER="octodns_metaname.op_opsdevnz_hooks:resolve"`

## Git Signing

This repository is frequently edited via AI agents.

- Never disable or bypass the default git signing configuration.
- Run commits/pushes normally so the signing prompt can appear for the operator.
