# Branching, Commits and Pull Requests

Owner: Developer Experience (DevEx)

## Trunk-based development

All repositories use trunk-based development. `main` is always deployable.
Feature branches are short-lived: the target is to merge within two working
days, and a branch older than seven days is flagged by the `stale-branch` bot.

## Branch names

Branches are named `<type>/<ticket>-<short-description>`, for example
`feat/PAY-412-retry-webhooks` or `fix/ORD-77-null-customer`. Allowed types are
`feat`, `fix`, `chore`, `docs`, `refactor` and `spike`.

## Commit messages

Commits follow the Conventional Commits specification. The subject line is at
most 72 characters, uses the imperative mood, and is prefixed with a type and
optional scope: `feat(checkout): add Apple Pay button`. Breaking changes carry
a `!` after the type and a `BREAKING CHANGE:` footer.

The `commitlint` check runs in CI and rejects non-conforming messages. Squash
merging is the default, so the pull request title becomes the commit subject
and must follow the same rules.

## Pull request size

Pull requests SHOULD change fewer than 400 lines excluding generated files and
tests. Larger changes are split into a stack of dependent pull requests using
the `gh stack` extension. The `pr-size` bot labels requests as `size/S`
(under 100 lines), `size/M` (under 400) or `size/L` (400 or more) and posts a
reminder on `size/L`.

## Pull request template

The template has four sections: **What**, **Why**, **How to test** and
**Rollout**. The Rollout section states whether the change is behind a feature
flag and how it will be rolled back. Leaving Rollout empty blocks the merge
for services in tier 1.

## Merge requirements

A pull request merges when it has at least one approval from a code owner, all
required checks are green, and no review is in the "changes requested" state.
Tier-1 services require two approvals. Authors MUST NOT approve their own
pull requests, and force-pushes to `main` are disabled organisation-wide.

## Reverting

A revert is a normal pull request created with `git revert`. Reverts of
production-impacting changes may be merged with a single approval from the
on-call engineer and are exempt from the pull request size limit.
