# Data inventory and handling rules

| Data | Purpose | Location | Retention | LLM allowed? |
|---|---|---|---|---|
| Mock IDs | Development and fixtures | Repository/CI | Indefinite | No |
| Student code and password hash | Login and access | PostgreSQL | Study retention policy | No |
| Revisions and chat turns | Learning flow and teacher view | PostgreSQL | Study retention policy | Only filtered request context |
| Private notes | Student-only notes | Browser localStorage | Until logout/device cleanup | No |
| Teacher sources and hints | Grounded tutoring | PostgreSQL/content seed | Lesson lifecycle | Yes, approved sources only |
| Audit events | Security and operations | PostgreSQL/log storage | Per retention policy | No |
| Backups | Recovery | Encrypted off-host storage | 14 rotating copies + weekly copies | No |

Never log raw student text, private notes, secrets, provider prompts, or full model responses. Use request IDs, event types, latency, token counts, and redacted error codes.
