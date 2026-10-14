# Incident Response

Owner: Site Reliability Engineering (SRE)

## What is an incident

An incident is any unplanned event that degrades a customer-facing service,
exposes data, or threatens to do either. When in doubt, declare: a false alarm
costs ten minutes; a late declaration costs hours.

## Severity levels

| Severity | Definition | Examples | Response |
|---|---|---|---|
| Sev-1 | Total or major outage, data loss or security breach | checkout down for all customers | all hands, status page, executive update every 30 minutes |
| Sev-2 | Significant degradation for many customers | p95 latency 5x normal, one region down | incident channel, status page, update every hour |
| Sev-3 | Minor degradation or a workaround exists | one report type failing | owning team during business hours |
| Sev-4 | Cosmetic or internal-only | typo in an email | normal bug process |

## Declaring an incident

Run `/incident declare` in Slack. The bot creates a channel named
`#inc-<date>-<slug>`, opens a ticket, pages the incident commander rotation
for Sev-1 and Sev-2, and starts a timeline. Anyone can declare; nobody is
blamed for declaring.

## Roles

- **Incident Commander (IC)**: owns the response, makes decisions, keeps the
  timeline. Does not debug.
- **Operations lead**: drives the technical investigation and mitigation.
- **Communications lead**: updates the status page, support and executives.
- **Scribe**: records decisions and actions in the channel (optional; the bot
  captures most of it).

The IC rotation is staffed by senior engineers who have completed IC training.

## Mitigation before root cause

The first goal is to stop customer impact, not to understand the bug. Roll
back, disable the feature flag, shift traffic, or scale up first. Root cause
analysis happens in the postmortem.

## Communication

The status page at `status.larkspur.com` is updated within 15 minutes of a
Sev-1 or Sev-2 declaration and at least every 60 minutes until resolution.
Customer-facing wording is owned by the communications lead and uses the
templates in the `incident-comms` repository.

## Resolution

An incident is resolved when customer impact has stopped and the IC is
confident it will not recur in the next 24 hours. Resolution is announced in
the incident channel and on the status page. The postmortem is due within
five business days for Sev-1 and Sev-2.

## Security incidents

Suspected security incidents are declared the same way but with the
`security` flag, which pages the Security on-call and restricts the channel
to the response team. Do not discuss details outside the channel.
