# Frontend guide

Thiện owns the Next.js frontend in `apps/web/`. The current [backend v2 plan](../v2/PreClass_Backend_Plan_v2.md) assigns frontend screens, API integration, responsive behavior, and end-to-end frontend checks to this workstream. Production deployment and backup are assigned to Khải.

## Use these references

- [ADR-0010](../adr/ADR-0010-fastapi-backend.md) — current frontend/backend boundary: Next.js calls FastAPI through `/v1`.
- [API guide](../api/API_GUIDE.md) and [OpenAPI contract](../../apps/api/openapi/openapi.json) — endpoint behavior and generated client input.
- [Data model](../api/DATA_MODEL.md) — domain terms used by the interface.
- [Backend v2 plan](../v2/PreClass_Backend_Plan_v2.md) — screen and integration milestones.

Store frontend design decisions, accessibility notes, responsive behavior, screenshots, and Figma handoff metadata here. Figma source files remain in the approved design workspace; this directory stores the implementation contract, not a binary export.

## Implemented UI contract (2026-11-14)

- **Visual system:** Atlas khám phá ([spec](../superpowers/specs/2026-11-14-atlas-kham-pha-ui-design.md)).
  - Tokens are defined on `:root` in `apps/web/app/globals.css`, with a dark set under `prefers-color-scheme`.
  - Motion is 120–220 ms and turns off under `prefers-reduced-motion`.
  - Touch targets are at least 44 px.
  - Font: **Be Vietnam Pro** (400–800), self-hosted with `next/font` in `apps/web/app/layout.tsx`. It replaced Avenir Next, which lacks Vietnamese diacritics. Use only the weights that are loaded: 400, 500, 600, 700, 800.
- **Status signals:** every status badge and alert shows an icon as well as text and colour (handoff §10). Review status and source evidence are separate badges, because a citation does not make a block "verified".
- **S03 editor:**
  - Desktop: content about 63% and Source Inspector about 37%.
  - Below 1024 px: the inspector opens as a bottom sheet when a block is selected. Close it with ✕ or Esc.
  - Approve, request changes and reject sit next to the selected block. They are bound to its `contentHash`, and there is no approve-all.
- **Autosave:** unsaved block edits are kept in `sessionStorage`, keyed by block and version. They come back after a reload and never overwrite a newer server version.
- **S06:** any revision can be opened read-only. A published revision is the snapshot students received.
- **Responsive checks:** Playwright at 390, 768 and 1280 px. Screenshots go to `apps/web/test-results/screens/`.
