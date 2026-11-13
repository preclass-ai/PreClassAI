# Task: T9 — Backend v2 (FastAPI) theo Source-to-Output Traceability

Status: `in_progress`
Owner: Claude Code (Remote Control) · review: Khải
Created: 2026-11-14

## Goal

`apps/api/` chạy được backend FastAPI theo `docs/v2/CLAUDE_CODE_PROMPT_Backend_v2.md`; Giai đoạn 1–3 xong trước để Thiện có `openapi/openapi.json` cho `apps/web/`.

## Scope

- In scope: mọi mục trong prompt v2 (GĐ 1–10).
- Out of scope: sửa `apps/web/` (của Thiện), push lên remote, deploy production thật.

## Interfaces and decisions

- Outputs: `apps/api/`, `apps/api/openapi/openapi.json`, `docs/api/API_GUIDE.md`, `docs/api/DATA_MODEL.md`.
- ADRs / docs: `docs/adr/ADR-0001-fastapi-backend.md` (agent viết ở GĐ 1), `docs/v2/`.

## Verification

- [ ] `cd apps/api && ruff check . && mypy --strict app && pytest`
- [ ] `docker compose -f infra/compose.dev.yml up -d` + `python scripts/smoke.py` xanh

## Handoff

`.agents/handoffs/T9-backend-v2.md`
