# Service Tiers and Ownership

Owner: Site Reliability Engineering (SRE)

## Why tiers exist

Not every service needs the same rigour. Tiers let us apply the strictest
requirements (two reviewers, load tests, canary analysis, 99.95%
availability) where an outage hurts customers most, and lighter rules where
it does not.

## Tier definitions

- **Tier 1**: an outage stops customers from buying, paying or using a core
  workflow, or exposes data. Examples: `api-gateway`, `order-router`,
  `payments-ledger`, `identity`.
- **Tier 2**: an outage degrades the product noticeably but a workaround or
  delay is acceptable for a few hours. Examples: `search-indexer`,
  `notifications`, `reporting`.
- **Tier 3**: internal tools and batch jobs whose outage is an inconvenience.
  Examples: `handbook-site`, `cost-reporter`.

The tier is declared in `service.yaml` and reviewed by SRE when the service
launches and annually afterwards. A service that becomes a dependency of a
tier-1 service inherits tier 1.

## What the tier changes

| Requirement | Tier 1 | Tier 2 | Tier 3 |
|---|---|---|---|
| Pull request approvals | 2 | 1 | 1 |
| Availability SLO | 99.95% | 99.9% | 99.5% |
| Canary and progressive rollout | required | required | optional |
| Load test before release | required | optional | no |
| On-call rotation | required | required | business hours |
| Runbook | required | required | recommended |
| Disaster recovery RTO | 1 hour | 4 hours | 2 business days |

## Ownership

Every service has exactly one owning team recorded in `service.yaml`. The
owning team is responsible for its on-call, its SLOs, its dependencies and
its documentation. Ownership transfers are a pull request to `service.yaml`
approved by both teams and SRE, and include a handover of the runbook and
dashboards.

## Orphaned services

A service whose owning team no longer exists is flagged by Backstage as
orphaned. The engineering director assigns a new owner within 30 days or
schedules the service for decommissioning.

## Runbooks

A runbook lists the service's dashboards, its common alerts with a diagnosis
and a fix for each, how to scale it, how to roll it back, and whom to call.
Runbooks live at `runbook.md` in the service directory and are linked from
every alert. An alert without a runbook link fails the `alerts-lint` check.
