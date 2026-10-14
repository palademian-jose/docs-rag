# Dependency Management

Owner: Developer Experience (DevEx)

## Adding a dependency

Before adding a third-party dependency, check that the standard library or
an existing internal library does not already solve the problem. The pull
request that adds a dependency explains why it is needed, links to the
project's license, and notes its maintenance status (last release, open
issues, number of maintainers).

## Allowed licenses

Permissive licenses (MIT, BSD, Apache 2.0, ISC) are allowed without review.
Weak copyleft licenses (LGPL, MPL) are allowed for libraries used unmodified.
Strong copyleft licenses (GPL, AGPL) are not allowed in services or
libraries; the `license-check` CI job fails the build if one is detected.
Anything not in these lists needs Legal approval.

## Lockfiles

Every repository commits its lockfile: `uv.lock` for Python,
`pnpm-lock.yaml` for TypeScript, `go.sum` for Go and `Cargo.lock` for Rust.
Builds in CI use `--frozen` or equivalent so that the lockfile is the source
of truth.

## Automated updates

Renovate runs weekly on Monday mornings and opens grouped pull requests per
repository: one for minor and patch updates, one per major update. Minor and
patch pull requests that pass CI are auto-merged for libraries; services
require a human approval. Security updates run daily and bypass the weekly
schedule.

## Major upgrades

A major version upgrade of a framework (for example Next.js or FastAPI) is
treated as a project: an ADR records the plan, the upgrade is done on a
branch that stays green, and the service is deployed behind the normal
canary. Upgrading a language runtime across the organisation is coordinated
by DevEx with a published timeline.

## Private packages

Internal libraries are published to the private registry at
`packages.larkspur.internal` with semantic versions. Consumers pin to a minor
range (`~=2.3` style). Publishing is done by CI on a tag; manual publishing is
disabled.

## Vendoring

Vendoring a dependency (copying its source into the repository) is allowed
only for abandoned libraries with a small surface, and requires a `VENDORED`
file recording the upstream version, license and reason.

## Removing dependencies

Unused dependencies are flagged by `deptry` (Python) and `knip`
(TypeScript) in CI as warnings. Teams clean them up during the monthly
maintenance day.
