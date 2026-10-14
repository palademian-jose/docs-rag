# Postmortems

Owner: Site Reliability Engineering (SRE)

## When a postmortem is required

A postmortem is written for every Sev-1 and Sev-2 incident, for any incident
that involved data loss or a security event regardless of severity, and for
any near miss that the on-call engineer believes would have been Sev-2 or
worse with slightly different timing. Sev-3 postmortems are optional.

## Timeline

The draft is due within five business days of resolution. The postmortem
review meeting happens within ten business days. Action items are filed as
tickets with the `postmortem` label before the review.

## Blameless

Postmortems are blameless. They describe what the system and the people in it
did, not who was at fault. Names are replaced by roles ("the on-call
engineer", "the deploying engineer"). The question is "what made this the
reasonable action at the time?", never "why did you do that?".

## Template

The template in the `postmortems` repository has these sections:

1. **Summary** - two sentences a non-engineer can understand.
2. **Impact** - customers affected, duration, revenue or SLO impact.
3. **Timeline** - timestamped events from first signal to resolution.
4. **Root cause and contributing factors** - using the "five whys" method.
5. **Detection** - how we found out, and how long after it started.
6. **Response** - what went well, what was difficult.
7. **Action items** - each with an owner, a ticket and a due date.

## Action items

Action items are classified as **prevent** (stops the root cause recurring),
**detect** (alerts sooner) or **mitigate** (reduces impact). Each incident
SHOULD produce at least one *prevent* or *detect* item. Action items have a
default due date of 30 days and are reviewed at the monthly operations review;
items older than 90 days are escalated to the engineering director.

## Review meeting

The review is open to the whole company. The IC presents, the owning team
answers questions, and the SRE facilitator keeps the discussion blameless.
Postmortems and recordings are published in the `postmortems` repository and
linked from the incident ticket.

## Metrics

SRE tracks time to detect (TTD), time to mitigate (TTM) and time to resolve
(TTR) for every incident. The organisation targets are a median TTD under five
minutes and a median TTM under 30 minutes for Sev-1 and Sev-2 incidents.
