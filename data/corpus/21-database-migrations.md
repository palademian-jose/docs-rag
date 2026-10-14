# Database Migrations

Owner: Data Platform

## Tooling

Postgres schema changes are managed with `alembic` for Python services and
`goose` for Go services. Migration files are committed next to the service
and are reviewed like any other code, with the Data Platform team as a
required reviewer for tier-1 services.

## Backward compatibility

Every migration MUST be compatible with both the currently deployed version
and the version being deployed, because the deploy pipeline runs migrations
before the new code starts and a rollback does not undo migrations. In
practice this means the expand/contract pattern:

1. **Expand**: add the new column, table or index. Do not remove anything.
2. **Migrate**: deploy code that writes to both old and new shapes, then
   backfill.
3. **Contract**: at least one release later, remove the old column.

## Forbidden operations in a single migration

- Renaming a column or table (use expand/contract).
- Adding a `NOT NULL` column without a default to a table with rows.
- Creating an index without `CONCURRENTLY` on a table over one million rows.
- Any statement that takes an `ACCESS EXCLUSIVE` lock for more than two
  seconds on a tier-1 database.

The `migration-lint` check rejects the first three automatically.

## Long-running migrations

Migrations that run longer than the pipeline's 15-minute job timeout, such
as backfills, are implemented as idempotent batch jobs that process rows in
chunks of 10,000 with a short sleep between batches, and are run by the
on-call engineer from a `lark migrate run` session with a ticket link.

## Testing migrations

CI applies every migration to an empty database and then to a database seeded
with the previous release's schema and fixture data. For tier-1 services, CI
also runs the migration against an anonymised snapshot of production in the
`staging` cluster and fails if it takes longer than ten minutes.

## Data migrations

Changes to data (not schema) that affect more than 1% of rows in a tier-1
table require a design review and a dry-run report showing the number of rows
to be changed and a sample before/after.

## Rollback of migrations

Down migrations are written but rarely run. If a migration must be reversed
in production, the on-call engineer runs it manually after confirming no
deployed code depends on the new shape. Dropping a column with data requires
a backup verified within the last 24 hours.
