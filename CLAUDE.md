# Claude Code project entrypoint

Read `AGENTS.md` before acting. `AGENTS.md` is the canonical repository contract; this file intentionally contains no duplicate policy.

For multi-agent work:

- Read `.agents/README.md` and the relevant task/handoff record before editing.
- When a task matches a listed workflow, read `.agents/skills/<skill-name>/SKILL.md` before acting.
- Record decisions in `docs/adr/` and implementation handoffs in `.agents/handoffs/`.
- Never place student data, secrets, or private prompts in the repository or in agent context.
- Run the verification commands documented by the task before reporting completion.
