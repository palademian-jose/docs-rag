# Data Retention and Deletion

Owner: Security and Legal

## Classification

Data is classified into four levels, and every datastore declares its highest
level in its `service.yaml`:

- **Public** - marketing content, published documentation.
- **Internal** - source code, runbooks, non-sensitive metrics.
- **Confidential** - customer business data, contracts, financial records.
- **Restricted** - personal data, payment card data, credentials.

## Retention periods

| Data | Retention | Owner |
|---|---|---|
| Customer account data | life of the account plus 30 days | Product |
| Order and invoice records | 7 years (statutory) | Finance |
| Application logs | 30 days | SRE |
| Error logs | 1 year | SRE |
| Traces | 14 days | SRE |
| Analytics events | 13 months | Data |
| Backups | 35 days | Data Platform |
| Support tickets | 3 years | Support |

Retention is enforced by automated jobs, not by policy documents alone. A
datastore without an enforcement job cannot be promoted to production.

## Deletion requests

Customers can request deletion of their personal data. Requests arrive
through the privacy portal and are fulfilled within 30 days. The
`deletion-orchestrator` service fans the request out to every service that
registered a deletion handler and records a completion receipt per service.
A service that stores personal data MUST register a handler; the privacy
review during launch checks this.

## Backups and deletion

Deleted data may persist in backups for up to the 35-day backup retention
period. Backups are encrypted and are not restored except for disaster
recovery; a restore after a deletion request triggers a re-run of the
deletion.

## Anonymised copies

The `staging` database is refreshed weekly from an anonymised copy of
production. The anonymisation job replaces names, emails, addresses and
free-text fields with synthetic values and is reviewed by Security annually.
Engineers must not attempt to re-identify records in anonymised copies.

## Legal holds

Legal may place a hold on specific data, which suspends deletion for the
affected records. Holds are recorded in the `legal-holds` registry and are
checked by every deletion job before it runs.
