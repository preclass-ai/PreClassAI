# Backup and restore runbook

## Backup policy

- `pg_dump` every six hours.
- Encrypt before leaving the host.
- Keep 14 rotating copies and four weekly copies.
- Store at least one copy on a separate in-country system controlled by the school/mentor.
- Alert if the newest successful backup is older than eight hours.

## Restore drill

1. Provision an isolated target with no public ingress.
2. Restore the newest backup and verify checksum/decryption.
3. Run schema checks, row-count sanity checks, and application smoke tests.
4. Record RTO, RPO, missing data, and corrective actions.
5. Destroy the isolated target after evidence is retained.

Production is not ready until this drill succeeds.
