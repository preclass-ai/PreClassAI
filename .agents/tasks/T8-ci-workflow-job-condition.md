# Task: T8 — Fix CI workflow evaluation failure

Status: `done`
Owner: Codex
Created: 2026-11-07

## Goal

Allow the repository CI workflow to be evaluated and run while the application scaffold is not yet enabled.

## Scope

- In scope: the job-level condition in `.github/workflows/ci.yml` and its local verification.
- Out of scope: enabling application CI before the application scaffold and lockfile exist.

## Interfaces and decisions

- Inputs: repository variable `APP_CI_ENABLED`.
- Outputs: `app` runs only when `APP_CI_ENABLED == 'true'`; repository policy checks always run.
- ADRs / docs: none; this is a CI configuration bug fix.

## Verification

- [x] Confirm no unsupported `hashFiles()` call remains in a job-level condition.
- [x] Run the repository-policy shell checks locally.
- [x] Run `git diff --check` and YAML parsing.

## Handoff

Changed files: `.github/workflows/ci.yml`, this task record, `.agents/handoffs/T8-ci-workflow-job-condition.md`.
Risks/blockers: GitHub-hosted run cannot be triggered from this environment because the local `gh` token is invalid.
Next action: Push the change and confirm the next GitHub Actions run is green.
