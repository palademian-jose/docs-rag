# Engineer Onboarding

Owner: Developer Experience (DevEx)

## Before day one

Your manager files an onboarding ticket in the `it-requests` project at least
five business days before your start date. The ticket provisions a laptop, a
Google Workspace account, a GitHub seat in the `larkspur` organisation, and a
Slack account. Laptops ship with the standard image: macOS on an Apple Silicon
MacBook Pro with 32 GB of memory, or Ubuntu 24.04 on a ThinkPad for engineers
who request Linux.

## Week one

- **Day 1**: IT orientation, security training (45 minutes), and 1Password
  setup. You will be added to the `eng-all` and `eng-announce` Slack channels.
- **Day 2**: Local development environment setup using the `larkspur-dev`
  bootstrap script. The script installs Homebrew (macOS) or apt packages
  (Ubuntu), `mise` for toolchain versions, Docker, `kubectl`, and `terraform`.
- **Day 3**: Pair with your onboarding buddy on a starter ticket labelled
  `good-first-issue`. The goal is to merge your first pull request by day five.
- **Day 5**: Thirty-minute check-in with your manager.

## Onboarding buddy

Every new engineer is assigned an onboarding buddy from their team who has been
at Larkspur for at least six months. The buddy is not your manager and is not
responsible for your performance; they are the person you ask the small
questions. Buddies are expected to block 30 minutes per day for the first two
weeks.

## The 30/60/90 plan

Your manager shares a 30/60/90 plan on your first day. Typical milestones:

- **30 days**: first production deploy, shadow one on-call shift, read the
  handbook end to end.
- **60 days**: own a small feature from design to launch, review at least ten
  pull requests.
- **90 days**: join the on-call rotation as a secondary, present a ten-minute
  demo at Engineering Forum.

## Required training

All engineers complete the following within 30 days: Security Fundamentals
(45 minutes, annual refresh), Incident Response Basics (one hour), and Data
Handling and Privacy (30 minutes). Completion is tracked in the `training`
dashboard in Backstage.

## Access requests

Production access is not granted during onboarding. Request it through the
`access-requests` form once you have completed the 60-day milestone; it is
approved by your manager and the Security team, and reviewed quarterly.
