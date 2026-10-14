# Code Review

Owner: Developer Experience (DevEx)

## Goals

Code review exists to catch defects, spread knowledge and keep the codebase
consistent. It is not a gate for style nitpicks: formatting is enforced by
tooling, so reviewers focus on correctness, design, tests and operability.

## Turnaround

Reviewers SHOULD respond to a review request within four working hours and
MUST respond within one working day. If you cannot review in time, reassign
rather than let the request sit. The `review-latency` dashboard tracks median
time to first review per team; the organisation target is under three hours.

## What a reviewer checks

1. Does the change do what the description says, and is the description
   accurate?
2. Are edge cases and failure modes handled (timeouts, retries, partial
   failures)?
3. Are there tests, and do they test behaviour rather than implementation?
4. Does the change affect a public API, a database schema or a feature flag?
   If so, is the rollout plan credible?
5. Are logs, metrics and traces added where an operator would need them?

## Comment conventions

Comments are prefixed to signal intent:

- `blocking:` must be addressed before merge.
- `suggestion:` optional improvement; the author decides.
- `question:` the reviewer needs information, not a change.
- `nit:` trivial; never blocks on its own.
- `praise:` call out something done well.

A review with only `nit:` and `suggestion:` comments SHOULD be approved rather
than left as "comment".

## Author responsibilities

Authors keep pull requests small, write a clear description, self-review the
diff before requesting review, and respond to every comment. "Done" is an
acceptable response to a blocking comment once it is addressed. Authors
resolve conversations; reviewers do not.

## Disagreements

If an author and reviewer cannot agree after two rounds, either side can pull
in a third engineer from the owning team. If the disagreement is about design,
it is escalated to the team lead; it is never settled by waiting the other
person out.

## Review of generated code

Generated code (protobuf stubs, OpenAPI clients, migrations produced by a tool)
is committed but reviewed only for the inputs that produced it. The `generated`
label hides these files from the diff by default.
