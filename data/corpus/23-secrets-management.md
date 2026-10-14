# Secrets Management

Owner: Security

## Where secrets live

All secrets live in HashiCorp Vault. Secrets are never stored in git, in
container images, in CI variables, in Slack, or in tickets. The
`secret-scanner` pre-receive hook rejects pushes containing strings that
match known credential patterns, and a weekly scan of the entire organisation
catches anything that slipped through.

## Paths

Vault paths follow `secret/<environment>/<service>/<name>`, for example
`secret/prod/order-router/db-password`. Shared secrets used by several
services live under `secret/<environment>/shared/` and are owned by Platform.

## Access

Services authenticate to Vault with their Kubernetes service account and
receive a policy scoped to their own path. Engineers authenticate with SSO and
can read `dev` secrets for services their team owns, and nothing in
`staging` or `prod`. Reading a production secret requires a break-glass
request that is approved by the Security on-call and logged.

## Delivery to workloads

Secrets are injected at pod start by the Vault agent sidecar as files under
`/vault/secrets/`, never as environment variables, so they do not leak into
crash dumps or `kubectl describe` output. Services read them once at startup
and reload on `SIGHUP`.

## Rotation

- Database credentials are dynamic: Vault issues a credential with a 24-hour
  lease and the service renews it.
- API keys for third-party services are rotated every 90 days; the
  `rotation-tracker` dashboard lists keys by age and pages Security when a
  key passes 100 days.
- TLS certificates are issued by the internal CA with 30-day validity and
  renewed automatically at 20 days.

## Leaked secrets

If a secret is exposed, rotate it first and investigate second. Declare a
security incident, rotate the secret in Vault, redeploy affected services,
and only then look at where it leaked. Git history containing a leaked secret
is rewritten by Security; the secret is considered compromised even after the
rewrite.

## Local development

Development secrets are fetched with `lark secrets pull`, which writes them to
`.env.local`. These are real credentials for the `dev` environment and must
not be shared. Production secrets are never available on laptops.
