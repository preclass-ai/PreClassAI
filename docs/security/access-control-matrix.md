# Access-control matrix

| Resource | Student | Teacher | Backend | Tech Lead | Mentor/school |
|---|---:|---:|---:|---:|---:|
| Own learning session | Read/write own | Read assigned class | Support via approved ops | Support via approved ops | No default access |
| Other student's session | No | Assigned class only | Break-glass, audited | Break-glass, audited | No default access |
| Teacher dashboard | No | Assigned classes | Support via service | Review/support | No default access |
| Production SSH | No | No | Approved operator | Approved operator | Account owner/auditor |
| Billing and provider keys | No | No | No | Operational use, never committed | Owner/control |
| Backups | No | No | Restore operator | Restore/audit | Owner/control |

Break-glass access requires a ticket, reason, time window, least privilege, and audit event.
