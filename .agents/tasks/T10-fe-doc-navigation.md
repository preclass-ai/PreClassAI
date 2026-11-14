# Task: T10 — Clarify frontend documentation entrypoints

Status: `done`
Owner: Codex (Thiện's frontend scope)
Created: 2026-11-14

## Goal

Help frontend contributors find the current v2/API documents without following superseded v1 architecture links.

## Scope

- In scope: README navigation and the frontend documentation index.
- Out of scope: moving or rewriting Khải-owned architecture, backend, operations, deployment, and budget documents.

## Interfaces and decisions

- Inputs: accepted ADR-0010 and existing v2/API documents.
- Outputs: clear links to current frontend references and labeled historical documents.
- ADRs / docs: ADR-0010 already defines the superseded v1 documents; no new decision.

## Verification

- [x] Check local Markdown links in changed navigation files: no missing targets.
- [x] Run `git diff --check` and inspect the final diff: no whitespace errors.

## Handoff

Changed files: `README.md`, `docs/README.md`, `docs/ui/README.md`, this task record, `.agents/handoffs/T10-fe-doc-navigation.md`.
Risks/blockers: v1 document contents remain in place for their owners to review.
Next action: Khải can decide whether to archive or update the older architecture and operations documents.
