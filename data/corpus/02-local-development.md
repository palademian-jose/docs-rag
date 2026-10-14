# Local Development Environment

Owner: Developer Experience (DevEx)

## Bootstrap script

Run the bootstrap script from `dev.larkspur.internal/bootstrap` once on a new
machine. The script is idempotent and safe to re-run. It installs:

- `mise` for managing language toolchains (Node, Python, Go, Rust)
- Docker Desktop (macOS) or Docker Engine (Ubuntu)
- `kubectl`, `kubectx`, `helm`, and `terraform` at the versions pinned in
  `tooling/versions.toml`
- the `lark` CLI, our internal developer tool

## Toolchain versions

Toolchain versions are pinned per repository in `.mise.toml`. The organisation
defaults are Node 22, Python 3.12, Go 1.23 and Rust stable. Do not install
language runtimes with Homebrew; `mise` owns them.

## The lark CLI

`lark` wraps the commands most engineers run every day:

- `lark up` starts the local stack for the current repository using Docker
  Compose and seeds the database with fixture data.
- `lark test` runs the repository's test suite with the same flags CI uses.
- `lark lint` runs the linters and formatters in check mode.
- `lark env <name>` opens a short-lived port-forward to a named environment
  (`dev`, `staging`); it never targets production.
- `lark secrets pull` fetches development secrets from Vault into a local
  `.env.local` file that is gitignored.

## Local databases

Services that need Postgres run it in Docker via `lark up`. The default local
database is `postgres:16` with the `pgvector` and `pg_stat_statements`
extensions enabled, listening on port 5432 with user `app` and password
`app`. Redis runs on port 6379. Both bind to localhost only.

## Ports

To avoid collisions, each service claims a port range in `tooling/ports.toml`.
Web services use 8000-8099, workers use 8100-8199, and internal admin UIs use
8200-8299. The `lark ports` command prints the allocation for the current
repository.

## Working offline

The `lark up --offline` flag uses the Docker images cached locally and the
fake LLM provider so that the stack starts without network access. Most
services support this mode; those that do not are listed in their README.
