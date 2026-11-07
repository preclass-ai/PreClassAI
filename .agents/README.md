# Multi-harness collaboration contract

This directory defines the shared protocol for Codex, Claude Code, Antigravity/Gemini-compatible tools, and future harnesses. The repository's source of truth is the worktree, not a harness transcript.

## Shared skills

Reusable skill packages live in `.agents/skills/<skill-name>/` and retain their upstream `SKILL.md`, references, and scripts. `docs/tooling/skills.md` is only the inventory and version/source record. Do not replace a skill package with a summary or rewrite its instructions.

Codex can use the project-local skill directory. Claude and Antigravity/Gemini-compatible harnesses should read the same `SKILL.md` when the task matches; their adapter files point here because harness auto-discovery differs.

## Before starting a task

1. Read `AGENTS.md` and the relevant architecture/security/operations document.
2. Create or claim a task record using `.agents/tasks/task-template.md`.
3. Check for an existing ADR or open Q-/A- decision before changing interfaces, data handling, deployment, or cost assumptions.

## During work

- Keep route handlers thin and business logic in services.
- Prefer small, reviewable commits and conventional commit subjects.
- Keep generated files and credentials out of the repository.
- Use the same task status vocabulary across harnesses: `planned`, `in_progress`, `blocked`, `in_review`, `done`.
- A harness may add notes to a task, but may not rewrite another harness's completed verification evidence.

## Handoff requirements

Every completed task gets a handoff based on `.agents/handoffs/handoff-template.md` containing changed files, interfaces, commands run, results, risks, and the next action.

## Decision protocol

If the task changes an API, schema, security boundary, hosting arrangement, retention rule, provider, or budget, stop and write an ADR or update the relevant ADR before implementation. When time pressure requires a temporary decision, record the rationale, owner, expiry/revisit date, and rollback path.
