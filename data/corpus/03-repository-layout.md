# Repository Layout and Naming

Owner: Developer Experience (DevEx)

## Monorepo versus polyrepo

Larkspur runs a hybrid model. Product services live in the `larkspur/platform`
monorepo. Shared libraries, infrastructure modules and open-source projects
live in their own repositories. New product services MUST be created in the
monorepo unless the architecture review board grants an exception.

## Monorepo structure

```
platform/
  services/<service-name>/     # one directory per deployable service
  libs/<language>/<lib-name>/  # shared internal libraries
  tools/                       # build and developer tooling
  infra/                       # Kubernetes manifests and Helm values
  docs/                        # architecture decision records, runbooks
```

Each service directory contains a `service.yaml` manifest declaring the
owning team, the on-call rotation, the tier (1, 2 or 3) and the runtime.

## Naming

- Repositories: lowercase, hyphen-separated, no prefixes (`billing-ledger`,
  not `lark-billing-ledger`).
- Services: lowercase, hyphen-separated nouns (`order-router`).
- Kubernetes namespaces: `<team>-<environment>` (`payments-prod`).
- Environment variables: `UPPER_SNAKE_CASE` with a service prefix
  (`ORDER_ROUTER_DB_URL`).
- Feature flags: `kebab-case` prefixed with the service (`checkout.new-cart`).

## Required files

Every service directory MUST contain a `README.md`, a `service.yaml`, a
`Dockerfile`, a `Makefile` with `test` and `lint` targets, and a `runbook.md`.
The `repo-lint` check in CI fails if any of these are missing.

## Code ownership

`CODEOWNERS` files map paths to GitHub teams. A pull request cannot merge until
every touched path has an approval from one of its owners. The DevEx team owns
`tools/` and the root of the monorepo; the Platform team owns `infra/`.

## Deleting a service

A service is removed by a pull request that deletes its directory and a linked
decommission ticket that confirms its DNS records, dashboards, alerts and
secrets have been cleaned up. The Platform team reviews decommissions.
