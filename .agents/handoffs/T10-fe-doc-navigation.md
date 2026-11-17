# Handoff: T10 — Clarify frontend documentation entrypoints

Status: `done`
Owner/harness: Codex (Thiện's frontend scope)
Date: 2026-11-14

## Outcome

The repository entrypoint now leads frontend contributors to the current v2 architecture decision, frontend guide, and API references. The documentation map labels superseded v1 files without changing their contents.

## Changed files

- `README.md` — replace stale architecture link with current navigation.
- `docs/README.md` — map current references and historical v1 documents.
- `docs/ui/README.md` — list Thiện's frontend scope and integration references.
- `.agents/tasks/T10-fe-doc-navigation.md` — record scope and verification.

## Interfaces

- Added/changed: documentation links only.
- Compatibility notes: no file moves; existing links to v1 documents still resolve.

## Verification evidence

```text
Local Markdown link check over README.md, docs/README.md, docs/ui/README.md: Missing links: []
git diff --check: exit 0
```

## Security/privacy impact

None. No application, credentials, data handling, or infrastructure changes.

## Risks and next action

- Risks: the older budget, infrastructure, and operations documents still need review against v2.
- Next action: Khải decides whether to archive or update those owner-managed documents.
