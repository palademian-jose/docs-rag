# Deployments and Rollbacks

Owner: Platform

## Pipeline

A merge to `main` triggers the deploy pipeline: build the image, push it to
`registry.larkspur.internal`, deploy to `staging`, run the smoke suite, then
start a production canary. The whole path takes about 25 minutes for a
typical service.

## Environments

| Environment | Purpose | Data | Who can deploy |
|---|---|---|---|
| `dev` | shared sandbox for integration work | synthetic | any engineer |
| `staging` | production-like, receives every merge | anonymised copy, refreshed weekly | pipeline only |
| `prod` | customer traffic | real | pipeline, or on-call via `lark deploy --break-glass` |

## Canary analysis

Production deploys start with a canary that receives 5% of traffic for ten
minutes. The canary is promoted automatically when all of the following hold
compared with the baseline:

- HTTP 5xx rate is not more than 0.5 percentage points higher
- p95 latency is not more than 15% higher
- no new panic or unhandled-exception signature appears in logs

If any check fails, the canary is rolled back automatically and the pipeline
posts to the owning team's alerts channel.

## Progressive rollout

After the canary, traffic shifts 25%, 50% and 100% at five-minute intervals.
Tier-1 services use ten-minute intervals. A deploy can be paused at any step
with `lark deploy pause <service>`.

## Rollback

Rollback redeploys the previous image tag; it does not revert code. Run
`lark deploy rollback <service>` or press "Rollback" on the deploy page in
Backstage. A rollback completes in under three minutes because the previous
image is still cached on every node. Rolling back does not undo database
migrations, which is why migrations must be backward compatible for at least
one release (see the database migrations page).

## Deploy windows

Deploys are allowed 24 hours a day, but non-urgent deploys to tier-1 services
SHOULD happen between 08:00 and 17:00 in the owning team's timezone so the
team is online to watch them. Deploys during a declared incident require the
incident commander's approval.

## Database migrations in the pipeline

Migrations run as a Kubernetes Job before the new version starts receiving
traffic. The job has a 15-minute timeout; migrations expected to take longer
are run manually by the on-call engineer using the procedure in the
migrations page.

## Break-glass deploys

`lark deploy --break-glass` bypasses the canary and progressive rollout. It
requires an active incident ticket and is logged to the `audit` topic. It is
used, for example, to roll forward a fix during a Sev-1 incident.
