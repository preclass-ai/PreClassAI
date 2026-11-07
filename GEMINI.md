# Gemini / Antigravity project entrypoint

Read `AGENTS.md` before acting. `AGENTS.md` is the canonical repository contract; this file is a thin harness adapter.

For multi-harness work:

- Read `.agents/README.md` and the relevant task/handoff record before editing.
- When a task matches a listed workflow, read `.agents/skills/<skill-name>/SKILL.md` before acting.
- Use the shared task status and verification formats.
- Record decisions in `docs/adr/`; do not create harness-specific architectural forks.
- Never place student data, secrets, or private prompts in the repository or in agent context.
