# Task: T7 — Engineering operations and multi-harness foundation

Status: `done`
Owner: Codex
Created: 2026-11-07

## Goal

Make the documentation-first repository ready for clean-code, deployment, security, monitoring, cost control, and collaboration across Codex, Claude, and Antigravity/Gemini-compatible harnesses.

## Scope

- In scope: repository contract, operations/security docs, CI policy, Compose/Caddy/backup templates, cost model, curated skill installation.
- Out of scope: application implementation, provider account creation, production credentials, live deployment, and real student data.

## Verification

- [x] `git diff --check`
- [x] `sh -n infra/backup.sh infra/restore.sh`
- [x] Docker Compose config validation
- [x] YAML parsing for workflow and Compose files
- [x] Repository policy and secret-like filename check
- [x] Curated skill installation verification
