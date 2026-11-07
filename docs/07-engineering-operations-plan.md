---
title: "07 — Engineering, Operations, Security and Collaboration Plan"
status: "Accepted for foundation implementation"
last_reviewed: 2026-11-07
owner: "Tech/Dev Lead"
related: [01-architecture-overview-adr-erd, 02-system-architecture-design, 03-budget-estimate, 04-infrastructure-source-code, 05-team-roles-raci, 06-master-plan-mvp]
---

# 07 — Engineering, Operations, Security and Collaboration Plan

## Current audit

The architecture and MVP plan are strong enough to guide implementation, but the repository is still documentation-only. Before real student data is enabled, the project must close Q-01/Q-02/Q-03/Q-04/Q-05/Q-07/Q-08, accept the ADRs, implement CI/CD, test restore, and activate monitoring.

## Foundation sequence

1. Shared harness contract, task records, ADR workflow, and protected-branch policy.
2. TypeScript/Next.js scaffold with strict lint/type/test/build commands.
3. CI security gates: secret scan, dependency audit, SBOM/image scan, tests, and build.
4. Local/staging/production Compose files with separate databases and secrets.
5. Desktop + Cloudflare Tunnel pilot; Vietnam school/lab VM remains the preferred production target; paid VPS is the fallback.
6. Encrypted backup, restore drill, health endpoints, Uptime Kuma, structured logs, and alerts.
7. Production go/no-go only after consent, privacy, security, restore, load, and budget checks pass.

## Non-negotiable gates

- No real student data in code, fixtures, logs, prompts, backups used for development, or agent context.
- AI can be disabled globally and the student flow remains usable with teacher-authored static hints.
- Production credentials and billing remain controlled by the mentor or school.
- Every change to schema, auth, AI, hosting, retention, or budget is documented in an ADR.
