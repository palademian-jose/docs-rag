# RFC Process

Owner: Architecture Review Board

## When to write an RFC

An RFC (Request for Comments) is required for any change that affects more
than one team, introduces a new datastore, language or framework, changes a
public API in a breaking way, or is expected to take more than six engineer
weeks. Smaller design decisions are captured as Architecture Decision Records
instead.

## Template

RFCs live in the `rfcs` repository as Markdown files named
`NNNN-short-title.md`. The template has these sections: **Summary**,
**Motivation**, **Proposal**, **Alternatives considered**, **Rollout and
migration**, **Security and privacy review**, **Open questions**.

An RFC SHOULD be readable in 15 minutes. Long appendices go in a linked
document.

## Lifecycle

1. **Draft** - the author shares the pull request in `#rfcs` and with the
   affected teams.
2. **Review** - at least ten business days of open comment. Each affected
   team names a reviewer who must either approve or state objections.
3. **Decision** - the Architecture Review Board meets weekly on Thursdays and
   either accepts, rejects or sends the RFC back with required changes.
4. **Accepted** - the pull request merges and the RFC becomes the reference
   design. Implementation tickets link to it.
5. **Superseded** - a later RFC can supersede an earlier one; both are kept.

## Architecture Review Board

The board has seven members: the principal engineers and one rotating senior
engineer per product area, serving six-month terms. Decisions are by
consensus; if consensus fails after two meetings, the CTO decides.

## Comments

Comments are made on the pull request. Reviewers distinguish `blocking`
objections, which must be resolved before acceptance, from `non-blocking`
suggestions. An objection must propose an alternative or explain the harm;
"I would not do it this way" is not an objection.

## Timeboxing

An RFC that has been in review for more than 30 business days without a
decision is escalated to the board chair, who schedules a decision meeting
within one week.

## After acceptance

Accepted RFCs are reviewed six months after implementation starts. The author
writes a one-page retrospective comparing the outcome with the proposal,
which is linked from the RFC.
