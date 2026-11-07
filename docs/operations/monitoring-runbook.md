# Monitoring and alerting runbook

## Checks

- Uptime Kuma: public HTTPS, `/api/health`, certificate expiry, Cloudflare Tunnel.
- Application: 5xx rate, p95 latency, request volume, auth failures, AI errors, quota use.
- Host: CPU, memory, disk, restart count, PostgreSQL availability, backup age.

## Alert thresholds

- Disk warning at 70%, critical at 80%.
- Memory warning at 80%, critical at 90%.
- Any failed backup older than eight hours.
- 5xx or tunnel failure sustained for five minutes.
- AI budget at 80% warning and 100% kill switch.

Alerts must contain environment, service, threshold, request ID if applicable, and runbook link; never include student text or secrets.
