# On-Call

Owner: Site Reliability Engineering (SRE)

## Rotation structure

Every team that owns a tier-1 or tier-2 service runs a weekly on-call rotation
with a primary and a secondary engineer. Shifts hand over on Tuesdays at
10:00 local time. The secondary is paged if the primary does not acknowledge
within ten minutes. Teams with fewer than five eligible engineers share a
rotation with a sister team.

## Eligibility

Engineers join the rotation as a secondary after 90 days at Larkspur and as a
primary after shadowing two full shifts. Managers are not in the rotation.

## Paging

Pages are sent through PagerDuty. Only alerts tagged `severity: page` page a
human; everything else goes to the team's alerts channel. An alert that pages
more than three times in a week without requiring action is reviewed at the
weekly operations review and either fixed or downgraded.

## Response expectations

- Acknowledge a page within ten minutes.
- Post a first update in the incident channel within 20 minutes.
- If the issue is not resolved within 30 minutes, declare an incident (see the
  incident response page).

## Compensation and time off

On-call primaries receive a flat weekly stipend plus one additional day of
leave for every week on call. Engineers who are paged between 22:00 and 07:00
local time start the next day no earlier than four hours after the page was
resolved, with no approval required.

## Handover

The outgoing primary writes a handover note in the team's on-call channel
covering open alerts, silenced alerts and anything "weird" observed during
the week. The incoming primary acknowledges the note before the shift starts.

## Tooling

- `lark oncall who <team>` shows the current primary and secondary.
- `lark oncall silence <alert> --for 2h --reason "..."` silences an alert;
  silences without a reason are rejected, and silences expire after a
  maximum of 24 hours.
- The on-call dashboard in Grafana lists every page in the last 30 days with
  time to acknowledge and time to resolve.

## Escalation

If the primary and secondary are both unreachable, PagerDuty escalates to the
team's engineering manager after 20 minutes, then to the SRE on-call after a
further ten minutes.
