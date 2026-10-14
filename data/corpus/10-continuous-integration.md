# Continuous Integration

Owner: Developer Experience (DevEx)

## Platform

CI runs on GitHub Actions with self-hosted runners in the `ci` Kubernetes
cluster. Runners are ephemeral: each job gets a fresh container and is
destroyed afterwards. The runner image is rebuilt weekly from
`tools/ci/runner.Dockerfile`.

## Required checks

Every pull request runs these checks, and all must pass before merge:

- `lint` - formatters and linters in check mode
- `test` - unit tests with coverage upload
- `integration` - integration tests against containers
- `build` - container image build and vulnerability scan with Trivy
- `repo-lint` - required files, CODEOWNERS and naming rules
- `commitlint` - commit and pull request title format

Tier-1 services additionally run `contract` (Pact) and `load-smoke` (a
60-second k6 run against an ephemeral preview environment).

## Time budget

The full pull request pipeline SHOULD finish in under 15 minutes. Pipelines
that exceed 20 minutes at p50 over a week are flagged on the `ci-health`
dashboard and the owning team is expected to parallelise or cache.

## Caching

Dependency caches are keyed on the lockfile hash (`uv.lock`, `pnpm-lock.yaml`,
`go.sum`). Docker layer caching uses the registry cache in
`registry.larkspur.internal/cache`. Test result caching with `turborepo`
or `bazel` is used in the monorepo so unchanged packages are not re-tested.

## Secrets in CI

CI jobs obtain short-lived credentials from Vault via OIDC; long-lived secrets
are never stored in GitHub. A job that needs cloud access assumes the
`ci-<repo>` role, which is scoped to read-only unless the job is a deploy.

## Preview environments

Pull requests labelled `preview` get an ephemeral environment at
`pr-<number>.preview.larkspur.dev` that is torn down when the pull request
closes or after 72 hours of inactivity. Preview environments use the shared
`preview` database cluster with per-environment schemas.

## Re-running and skipping

Re-run a failed job from the GitHub UI; do not push empty commits. The
`[skip ci]` trailer is honoured only for documentation-only changes and is
rejected by `repo-lint` if code files changed.

## Merge queue

The monorepo uses the GitHub merge queue. Pull requests are batched in groups
of up to five and tested together on top of `main` before merging, which keeps
`main` green even when two changes conflict semantically.
