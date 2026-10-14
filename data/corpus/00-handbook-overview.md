# Larkspur Systems Engineering Handbook

## Purpose

This handbook is the single source of truth for how engineering works at
Larkspur Systems. It covers how we write, review, ship and operate software,
and how we treat each other while doing it. Every engineer is expected to have
read it within their first two weeks.

## How the handbook is maintained

The handbook lives in the `eng-handbook` repository and is published on every
merge to `main`. Changes follow the normal pull request process; the Developer
Experience (DevEx) team owns the repository and is the default reviewer. Pages
that describe a policy (security, on-call, data retention) additionally require
approval from the policy owner named at the top of the page.

Each page carries a `last-reviewed` date in its front matter. Pages are
reviewed at least every six months; a page older than nine months is flagged
by the `handbook-freshness` bot and its owner is pinged in `#eng-handbook`.

## Structure

The handbook is organised into six areas:

1. **People and process** - onboarding, meetings, RFCs, hiring, mentorship.
2. **Writing code** - style guides, repository layout, branching, code review.
3. **Shipping** - CI, release trains, feature flags, deployments, rollbacks.
4. **Operating** - on-call, incidents, postmortems, SLOs, observability.
5. **Platform** - Kubernetes, Terraform, databases, caching, secrets.
6. **Security and data** - access control, vulnerability response, retention.

## Conventions used in this handbook

- **MUST** and **MUST NOT** describe hard requirements enforced by tooling or
  policy. Violations block merges or deploys.
- **SHOULD** describes the default; deviations require a short written
  justification in the pull request description.
- **MAY** describes options left to the team.

## Getting help

Questions about the handbook go to `#eng-handbook`. If a page is wrong, open a
pull request; if you are not sure what is right, open an issue in the
`eng-handbook` repository with the `question` label and DevEx will respond
within two business days.
