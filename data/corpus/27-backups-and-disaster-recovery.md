# Backups and Disaster Recovery

Owner: Data Platform

## Backup schedule

Every production Postgres cluster takes a full base backup daily at 02:00 UTC
and ships write-ahead logs continuously to object storage in a different
region. Point-in-time recovery is possible to any second within the last 35
days. Object storage buckets that hold customer files are versioned and
replicated cross-region with a 15-minute lag.

## Restore testing

A random production database is restored into an isolated environment every
week by the `restore-drill` job. The drill verifies that the restore
completes, that row counts match the source within the expected lag, and
that the application's smoke tests pass against the restored copy. A failed
drill pages the Data Platform on-call.

## Recovery objectives

| Tier | Recovery Point Objective (RPO) | Recovery Time Objective (RTO) |
|---|---|---|
| 1 | 5 minutes | 1 hour |
| 2 | 1 hour | 4 hours |
| 3 | 24 hours | 2 business days |

These objectives are tested in the annual disaster recovery exercise and
reported to the executive team.

## Regional failover

Production runs active-active across `prod-eu` and `prod-us` for stateless
services. Stateful services run primary in one region with a streaming
replica in the other. Failover is initiated by the incident commander with
`lark dr failover <service> --to prod-us` and takes about 20 minutes,
most of which is DNS and cache warming.

## Annual exercise

Once a year, in Q2, Platform and SRE simulate the loss of a full region.
The exercise runs on staging with production-shaped traffic and takes a
full day. Findings are tracked as postmortem-style action items.

## What is not backed up

Caches (Redis), message queues (Kafka topics beyond their retention) and
ephemeral `dev` environments are not backed up. Services MUST be able to
rebuild caches from the source of truth and MUST tolerate the loss of
in-flight queue messages up to the queue's at-least-once guarantees.

## Requesting a restore

A restore of production data for anything other than disaster recovery (for
example, a customer deleted something by mistake) is requested through a
ticket in the `data-platform` project with the table, the time window and
the business justification. Restores are performed into a scratch schema
and the owning team copies the rows they need.
