# Release Trains and Versioning

Owner: Release Engineering

## Cadence

Backend services deploy continuously: every merge to `main` that passes CI is
deployed to `staging` automatically and to production after the canary
analysis described in the deployment page. There is no fixed release day.

Mobile applications and the customer-facing web application ship on a weekly
release train. The train is cut every Tuesday at 10:00 UTC from `main`,
soaks on staging for 24 hours, and is released on Wednesday. Missing the train
means waiting for the next one; there are no "hold the train" requests except
for a declared incident.

## Versioning

- Backend services are versioned by git SHA and the deploy timestamp; semantic
  versions are not used for internal services.
- Libraries use semantic versioning. A major version bump requires a migration
  note in the changelog.
- Mobile applications use `MAJOR.MINOR.PATCH` with the build number set to the
  CI run number.
- Public APIs are versioned in the URL path (`/v2/orders`) as described in the
  API design page.

## Release notes

Release notes for customer-visible changes are written in the pull request
under a `## Release note` heading. The `release-notes` bot collects them into
the weekly changelog published on Wednesday. Internal-only changes use
`Release note: none`.

## Freeze periods

A deploy freeze applies during the last five business days of each quarter
and for the 48 hours around Black Friday. During a freeze only fixes for
Sev-1 and Sev-2 incidents are deployed, and each needs approval from the
Release Engineering on-call.

## Hotfixes

A hotfix is a change that must reach production before the next train. It is
branched from the released tag, cherry-picked to `main`, and requires an
incident ticket or a Sev-3-or-higher bug. Hotfixes to the mobile apps go
through expedited store review and typically land within 24 hours.

## Changelog ownership

Each product area has a release manager who reviews the weekly changelog
before publication. The release manager rotates monthly and is listed in the
`release-managers` group in Backstage.
