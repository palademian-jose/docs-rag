# Cloud Cost Management

Owner: Platform and Finance

## Budgets

Each team has a monthly cloud budget set during quarterly planning and
tracked in the `cost-reporter` dashboard. Spend is allocated by the `team`
and `service` tags on every resource. The dashboard updates daily and shows
the forecast for the month; a team forecast to exceed its budget by more than
10% receives an automatic notice in its channel.

## Review cadence

Platform and Finance review total cloud spend monthly. Each team lead reviews
their team's spend in the first week of the month and records planned
optimisations in the `cost` project. Savings above 5,000 USD per month are
announced at Engineering Forum.

## Guardrails

- New instance types, managed services and regions require Platform approval
  through a Terraform pull request review.
- Any single resource costing more than 2,000 USD per month is tagged
  `cost-review` and justified in its Terraform code comments.
- Development environments are shut down automatically between 20:00 and
  07:00 in the owning team's timezone and at weekends.
- Unattached volumes, idle load balancers and snapshots older than 90 days
  are deleted weekly by the `cost-janitor` job after a seven-day warning.

## Commitments

Platform purchases one- and three-year compute commitments covering about 70%
of the baseline production footprint, reviewed every six months. Teams do
not need to think about commitments; they are applied at the account level.

## Spot capacity

Batch workloads and stateless workers run on the `spot` node pool, which is
roughly 60-70% cheaper than on-demand. Workloads on spot must checkpoint or
be restartable; the pool drains nodes with a two-minute warning.

## Data transfer

Cross-region traffic is the most common surprise cost. Services SHOULD talk
to datastores in their own region and use the regional replica for reads.
Egress to the public internet is reviewed when it exceeds 1 TB per month for
a single service.

## Observability spend

Logging, metrics and tracing are budgeted at 8% of the total cloud bill.
The highest-volume log producers and highest-cardinality metrics are reported
weekly to the owning teams.

## Requesting more budget

A team that needs more budget files a request with the expected monthly cost,
the business reason and the alternative considered. Requests under 3,000 USD
per month are approved by the engineering director; larger requests go to
the CTO and Finance.
