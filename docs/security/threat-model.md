# Threat model

## Assets

- Student learning records, revisions, chat turns, consent records, and audit events.
- Teacher-authored lesson sources, answer keys, transfer prompts, and AI budget controls.
- Authentication credentials, database credentials, LLM keys, backup keys, and deployment access.

## Trust boundaries

1. Student/teacher browser → Caddy/Cloudflare edge.
2. Edge → Next.js application.
3. Application → PostgreSQL.
4. Application → external LLM provider.
5. Deployment runner → host and GHCR.
6. Backup job → encrypted off-host storage.

## Primary threats and controls

| Threat | Control | Evidence |
|---|---|---|
| IDOR or role escalation | Service-layer ownership checks, deny-by-default access, 404/403 policy | Authz integration tests |
| Student data sent to LLM | Data minimization, PII filter, provider region/no-training approval | Provider record + contract test |
| AI reveals answer or transfer prompt | Server-side state machine, source allowlist, output length/similarity checks, static fallback | Eval suite and transfer tests |
| Secret leakage | GitHub environments, `.env` exclusion, gitleaks, key rotation runbook | CI and incident drill |
| Host compromise | SSH keys, UFW, fail2ban, patching, isolated Docker networks | Host checklist |
| Data loss | Six-hour encrypted dumps, off-host copy, tested restore | Restore report |
| Monitoring exposes content | Redacted structured logs and restricted dashboards | Log inspection test |

## Residual risks

Desktop hosting has power, connectivity, and single-host failure risk. Cloudflare Tunnel introduces a third-party edge dependency. Neither is acceptable for sustained production without an owner, restart procedure, and tested fallback.
