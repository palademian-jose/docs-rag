# Feature Flags

Owner: Release Engineering

## Why we use flags

Every user-visible change and every risky backend change ships behind a
feature flag. Flags decouple deploy from release: code reaches production
dark, is enabled for a small audience, and is expanded or rolled back without
a deploy.

## The flag service

Flags are managed in `flagship`, our internal flag service, and evaluated
through the `larkspur-flags` SDK available for Python, TypeScript and Go.
Evaluation is local: the SDK polls `flagship` every 30 seconds and caches the
ruleset, so a `flagship` outage leaves flags at their last known value.

## Naming and ownership

Flag keys are `<service>.<kebab-case-name>`, for example
`checkout.express-pay`. Every flag has an owner, a description, a ticket link
and an expiry date. Flags without an expiry date are rejected at creation.

## Flag types

- **Release flags** gate unfinished features. They are temporary and MUST be
  removed within 30 days of reaching 100% rollout.
- **Operational flags** act as kill switches for expensive or risky code paths.
  They are permanent and reviewed quarterly.
- **Experiment flags** split traffic for A/B tests and are managed by the
  Experimentation team through the same service.

## Rollout steps

The standard rollout ladder is: internal employees, 1%, 5%, 25%, 50%, 100%.
Each step holds for at least one hour on tier-1 services and is accompanied
by a check of the error-rate and latency dashboards. Skipping steps requires
the on-call engineer's sign-off.

## Targeting rules

Flags can target by user id, organisation id, country, platform and release
version. Targeting by email domain is allowed only for `larkspur.com`
addresses (internal testing). Targeting by any other personal attribute is
not permitted.

## Cleanup

The `flag-reaper` bot opens a pull request removing a release flag seven days
after its expiry date, and pages the owner in `#flags` if the pull request is
not merged within two weeks. Stale flags count against the team's technical
debt budget in quarterly planning.

## Testing with flags

Tests MUST NOT depend on the live flag service. The SDK ships a
`LocalFlagProvider` that reads a dictionary of flag values; tests set the
values they need explicitly.
