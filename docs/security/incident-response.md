# Incident response runbook

## Severity

- **SEV-1:** suspected student-data exposure, credential compromise, or production-wide outage.
- **SEV-2:** material security control failure, backup failure, or sustained degradation.
- **SEV-3:** isolated defect without evidence of data exposure.

## First 15 minutes

1. Record incident ID, time, reporter, affected environment, and evidence location.
2. Disable `ai.enabled` and, if needed, place the application in maintenance mode.
3. Preserve relevant audit events and host logs; do not copy student content into chat or tickets.
4. Rotate the suspected key or credential through the mentor/school-owned account.
5. Notify Tech Lead, Backend owner, Mentor, and school data owner using the agreed channel.

## Recovery

- Identify affected records and access paths.
- Restore to an isolated host if integrity is uncertain.
- Validate authz, backup, and monitoring controls before reopening.
- Document timeline, impact, root cause, corrective action, and notification decisions.

## Exercises

Run one tabletop exercise before pilot launch and one restore/credential-rotation exercise before real data is enabled.
