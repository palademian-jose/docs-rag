# Internal Tools Glossary

Owner: Developer Experience (DevEx)

This page lists the internal tools and services referenced throughout the
handbook, with the team that owns each and where to find it.

## Developer tooling

- **lark** - the command-line developer tool. Wraps local stacks, tests,
  deploys, secrets and on-call commands. Owned by DevEx. Installed by the
  bootstrap script.
- **Backstage** - the developer portal at `backstage.larkspur.internal`.
  Shows every service with its owner, tier, SLOs, runbook, ADRs and training
  status. Owned by DevEx.
- **mise** - toolchain version manager used for Node, Python, Go, Rust and
  Terraform. Replaced `asdf` in 2025.
- **repo-lint** - CI check that verifies required files, naming rules and
  CODEOWNERS coverage.

## Delivery

- **flagship** - the feature flag service and its UI at
  `flags.larkspur.internal`. Owned by Release Engineering.
- **atlantis** - applies Terraform plans on merge. Owned by Platform.
- **registry** - the container and package registry at
  `registry.larkspur.internal` and `packages.larkspur.internal`.
- **merge queue** - GitHub's merge queue, enabled on the monorepo and on
  tier-1 repositories.

## Operations

- **PagerDuty** - paging and on-call schedules. Schedules are managed as
  code in the `oncall` repository.
- **Grafana / Loki / Tempo / Prometheus** - dashboards, logs, traces and
  metrics, all at `grafana.larkspur.internal`. Owned by SRE.
- **Sentry** - crash and exception reporting for web and mobile clients.
- **status page** - `status.larkspur.com`, updated by the communications lead
  during incidents.
- **SLO service** - stores SLO definitions and error budgets; queried by the
  deploy pipeline before promoting a canary.

## Security and data

- **Vault** - secrets storage. Owned by Security.
- **access-requests** - the form and workflow for requesting group
  membership and break-glass access.
- **deletion-orchestrator** - fans out customer deletion requests to every
  service with a registered handler.
- **log-scrubber** - redacts known sensitive patterns from logs before
  storage.

## Bots

- **stale-branch**, **pr-size**, **flake-hunter**, **flag-reaper**,
  **coverage**, **handbook-freshness**, **drift-detector**, **cost-janitor**,
  **access-reaper** and **release-notes** are GitHub or scheduled bots
  described on the relevant handbook pages. All bot source code lives in
  the `bots` repository owned by DevEx, and every bot posts under its own
  name so its messages can be muted individually.

## Chat channels

- `#eng-announce` - announcements only, read by every engineer.
- `#eng-handbook` - questions and changes to this handbook.
- `#rfcs` - new RFCs and review discussion.
- `#api-review` - public API changes.
- `#flags` - feature flag lifecycle notices.
- `#inc-<date>-<slug>` - one channel per incident, created by the bot.
