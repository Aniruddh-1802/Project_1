# C13 — Plugin Versioning & Ownership (required write-up)

**Plugin:** plugins/network-engineering-plugin (installable via the team
plugin marketplace / `claude plugin install network-engineering`).

## Ownership
- Owner: the platform engineering lead (single accountable owner).
- Change control: rule changes (CLAUDE.md contents, C6-derived policies,
  hook behaviour) require review by one data engineer AND one NOC
  representative — these encode DE-phase data contracts and NOC terminology,
  not preferences.
- The C12 MCP config is owned jointly with the API owners: a new MCP tool may
  be added only when the corresponding API endpoint exists (the thin-wrapper rule).

## Versioning
- Semantic versioning: PATCH = wording/doc fixes; MINOR = new command/skill
  (additive, like the C5 API rule); MAJOR = any rule change that alters what
  Claude will refuse or how hooks block.
- Version pinned per repository; upgrades are a PR so the C15 CI review runs
  against the new rules before adoption.

## Clean-environment verification (acceptance criteria)
Installed into a fresh clone with an empty .claude/: `/network-health` ran and
reported PASS ✔; asking "is grid 4821 congested?" produced the terminology
correction from the CLAUDE.md rule ✔. One command and one rule demonstrably
active after install.
