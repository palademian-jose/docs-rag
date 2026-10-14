# Service Level Objectives and Error Budgets

Owner: Site Reliability Engineering (SRE)

## Definitions

- A **Service Level Indicator (SLI)** is a measurement: the fraction of
  requests that succeed, or the fraction that complete under a latency bound.
- A **Service Level Objective (SLO)** is a target for an SLI over a window, for
  example "99.9% of requests succeed over 30 days".
- An **error budget** is the allowed failure: 100% minus the SLO. At 99.9% over
  30 days the budget is about 43 minutes of full downtime.

## Required SLOs

Every tier-1 and tier-2 service defines at least an availability SLO and a
latency SLO in its `service.yaml`. The defaults, which teams may tighten but
not loosen without SRE approval:

| Tier | Availability | Latency |
|---|---|---|
| 1 | 99.95% | p95 under 300 ms |
| 2 | 99.9% | p95 under 500 ms |
| 3 | 99.5% | p95 under 1000 ms |

SLOs are measured at the load balancer, not inside the service, so they
include the effects of deploys and infrastructure.

## Burn-rate alerts

Each SLO has two alerts: a fast burn (2% of the monthly budget consumed in one
hour) that pages, and a slow burn (5% consumed in six hours) that posts to the
team channel. Alerting on raw error rate is discouraged because it does not
account for traffic volume.

## Error budget policy

When a service has spent its error budget for the current 30-day window:

1. Feature deploys to that service stop; only reliability fixes and reverts
   ship.
2. The team spends the next sprint on reliability work agreed with SRE.
3. The freeze lifts when the budget is back above zero or after two weeks,
   whichever comes first.

The policy is enforced by the deploy pipeline, which checks the budget in
the SLO service before promoting a canary.

## Reviewing SLOs

SLOs are reviewed quarterly with the product manager. An SLO that is never
threatened is probably too loose; one that is breached every month without
customer complaints is probably too tight. Changes are recorded in the
service's `service.yaml` history.

## Dashboards

Every SLO has an auto-generated Grafana dashboard at
`grafana.larkspur.internal/d/slo-<service>` showing the SLI, remaining
budget and burn rate. The company-wide SLO summary is reviewed at the monthly
operations review.
