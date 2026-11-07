# Handoff: T7 — Engineering operations and multi-harness foundation

Status: `done`
Owner/harness: Codex
Date: 2026-11-07

## Outcome

The repository now has a canonical multi-harness collaboration contract, security and operations runbooks, guarded CI policy, deployment templates, backup/restore scripts, a revised operating-cost model, and project-local copies of seven existing curated skills.

## Changed files

- `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.agents/` — shared collaboration protocol and handoff formats.
- `docs/07-engineering-operations-plan.md` — audit and implementation gates.
- `docs/security/` — threat model, data inventory, access matrix, incident response.
- `docs/operations/` — deployment, backup/restore, monitoring runbooks.
- `infra/` — Compose, Caddy, backup, and restore templates.
- `.github/` — CODEOWNERS, PR template, Dependabot, guarded CI.
- `docs/03-budget-estimate.md`, `docs/04-infrastructure-source-code.md`, `README.md` — updated cost/operations guidance.

## Interfaces

- Codex: `AGENTS.md` plus installed curated skills.
- Claude: `CLAUDE.md` pointer to canonical rules.
- Antigravity/Gemini-compatible: `GEMINI.md` pointer to canonical rules.
- Shared task/handoff format: `.agents/tasks/` and `.agents/handoffs/`.

## Verification evidence

```text
git diff --check                         PASS
sh -n infra/backup.sh infra/restore.sh  PASS
docker compose ... config                PASS
Ruby YAML parse                          PASS for workflow and Compose files
repository policy check                  PASS
seven curated skills                     INSTALLED
```

## Security/privacy impact

No application code, credentials, provider keys, or student data were added. HSTS was intentionally omitted from the shared Caddyfile until the production hostname and rollback posture are confirmed.

## Risks and next action

- Risks: provider region/no-training terms, school ownership, GitHub teams, production host, and application scaffold remain open decisions.
- Next action: scaffold `apps/web`, package manifests, database schema, and executable CI checks behind the documented gates.
