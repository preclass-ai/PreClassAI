# Handoff: T8 — Fix CI workflow evaluation failure

Status: `done`
Owner/harness: Codex
Date: 2026-11-07

## Outcome

The CI workflow no longer calls the unsupported `hashFiles()` function from a job-level condition. The application job is explicitly opt-in through the `APP_CI_ENABLED` repository variable, so repository-policy CI runs while the application scaffold is absent.

## Changed files

- `.github/workflows/ci.yml` — replaced the invalid job-level `hashFiles()` condition with `vars.APP_CI_ENABLED == 'true'`.
- `.agents/tasks/T8-ci-workflow-job-condition.md` — recorded scope and verification.

## Interfaces

- Added/changed: CI job gating via the repository variable `APP_CI_ENABLED`.
- Compatibility notes: set `APP_CI_ENABLED` to the string `true` after the application scaffold and lockfile are committed.

## Verification evidence

```text
rg job-level condition check: passed; APP_CI_ENABLED condition found
repository policy checks: passed
Ruby YAML parse: workflow YAML parsed
sh -n infra/backup.sh infra/restore.sh: passed
git diff --check: passed
```

## Security/privacy impact

None. The workflow remains read-only and the existing secret-like filename check is unchanged.

## Risks and next action

- Risks: GitHub-hosted verification could not be run because the local `gh` token is invalid.
- Next action: push the change and confirm the next GitHub Actions run is green; later set `APP_CI_ENABLED=true` when the app scaffold is ready.
