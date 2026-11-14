# Reusable skills and harness mapping

This project uses existing skills from the curated catalog; it does not define a project-specific skill. The actual project-local packages are under `.agents/skills/`; this file is only the inventory and mapping.

| Skill | Use in PreClassAI | Codex | Claude / Antigravity |
|---|---|---|---|
| `security-best-practices` | Secure TypeScript/Next.js implementation review | `.agents/skills/security-best-practices/` | Read the same `SKILL.md` from `.agents/skills/` |
| `security-threat-model` | Threat model for child data, AI, auth, and hosting | `.agents/skills/security-threat-model/` | Use the same `SKILL.md` and `docs/security/threat-model.md` |
| `security-ownership-map` | Map security ownership to Tech Lead, Backend, Mentor, and school | `.agents/skills/security-ownership-map/` | Use the same `SKILL.md` and committed ownership matrix |
| `playwright` | Responsive browser and regression tests | `.agents/skills/playwright/` | Run the repository's Playwright commands |
| `cloudflare-deploy` | Tunnel/deployment guidance for the pilot path | `.agents/skills/cloudflare-deploy/` | Follow `docs/operations/deployment-runbook.md` |
| `gh-fix-ci` | Diagnose failed GitHub Actions checks | `.agents/skills/gh-fix-ci/` | Use the CI logs and shared handoff format |
| `gh-address-comments` | Resolve review comments with evidence | `.agents/skills/gh-address-comments/` | Record decisions in task/ADR files |
| `figma` | Figma inspection and design-workflow entrypoint | `.agents/skills/figma/` | Use the same project-local skill when Figma is available |
| `figma-use` | Use existing Figma files as implementation references | `.agents/skills/figma-use/` | Follow the same Figma handoff contract |
| `figma-create-design-system-rules` | Extract reusable design-system rules | `.agents/skills/figma-create-design-system-rules/` | Store the resulting implementation rules in `docs/ui/` |
| `figma-implement-design` | Implement approved Figma designs in code | `.agents/skills/figma-implement-design/` | Use the same UI acceptance criteria |
| `figma-generate-design` | Generate new design explorations | `.agents/skills/figma-generate-design/` | Treat generated designs as proposals until approved |
| `screenshot` | Visual QA and screenshot capture | `.agents/skills/screenshot/` | Store only approved, non-sensitive screenshots |
| `playwright-interactive` | Interactive browser investigation | `.agents/skills/playwright-interactive/` | Use shared test IDs and viewport matrix |
| `vercel-react-best-practices` | React/Next.js performance review for `apps/web` | `.agents/skills/vercel-react-best-practices/` | Same package; Claude Code discovers it via the `.claude/skills/` symlink |
| `web-design-guidelines` | UI/accessibility review against Web Interface Guidelines | `.agents/skills/web-design-guidelines/` | Same package; Claude Code discovers it via the `.claude/skills/` symlink |

Installation source: the OpenAI curated skills catalog, queried and installed 2026-11-07. `vercel-react-best-practices` and `web-design-guidelines` come from `vercel-labs/agent-skills`, added 2026-11-14 and pinned by hash in `skills-lock.json`. The same packages are also installed globally for Codex at `~/.codex/skills/`; the repo-local copy is the collaboration source of truth.

Harnesses must share repository artifacts, not copied skill bodies. `AGENTS.md` is canonical; `CLAUDE.md` and `GEMINI.md` are adapters.
