# Architecture Decision Records

Owner: Architecture Review Board

## Purpose

An Architecture Decision Record (ADR) captures a single technical decision,
its context and its consequences, so that future engineers understand why
the system looks the way it does. ADRs are lightweight: one page, written by
the person making the decision, reviewed by the team.

## When to write one

Write an ADR when a decision is hard to reverse, when it will surprise
someone reading the code later, or when the team debated it for more than an
hour. Choosing a library, deciding how to model a core entity, or picking a
consistency model all qualify. Decisions that affect multiple teams need an
RFC instead.

## Location and naming

ADRs live in the service directory under `docs/adr/` and are numbered
sequentially: `0001-use-postgres-for-ledger.md`. Cross-cutting ADRs that
do not belong to one service live in `platform/docs/adr/`.

## Template

```
# ADR-0001: Use Postgres for the ledger

Status: Accepted | Proposed | Deprecated | Superseded by ADR-00NN
Date: 2026-03-14
Deciders: names of the people who decided

## Context
## Decision
## Consequences
```

The **Context** section states the forces at play. The **Decision** section
is one or two sentences in the active voice: "We will use Postgres with
serialisable isolation for the ledger." The **Consequences** section lists
what becomes easier and what becomes harder, including the follow-up work.

## Status changes

An ADR is never edited after acceptance except to change its status. To
reverse a decision, write a new ADR that supersedes the old one and update
both status lines.

## Review

ADRs are reviewed in the normal pull request process by the owning team. No
board approval is needed. The `adr-lint` check verifies the template
headings and that the number is unique.

## Index

The `lark adr list` command prints every ADR in the current repository with
its status. Backstage renders the index for each service on the service's
documentation tab.
