# TypeScript Style Guide

Owner: Web Platform

## Versions and tooling

Frontend code targets TypeScript 5 with `strict: true`. The package manager is
`pnpm`; `npm` and `yarn` lockfiles are rejected by the `repo-lint` check.
Formatting uses Prettier with the shared `@larkspur/prettier-config`; linting
uses ESLint with `@larkspur/eslint-config`.

## Framework

Customer-facing web applications use Next.js with the App Router. Internal
tools use Vite with React. New applications MUST NOT use Create React App or
class components.

## Strictness rules

- `any` is forbidden. Use `unknown` and narrow.
- Non-null assertions (`!`) require an inline comment.
- `enum` is not used; use string literal unions.
- Default exports are not used except for Next.js route files.

## Project structure

```
app/            # Next.js routes
components/     # presentational components, one per file
features/       # feature folders: components, hooks, api, tests together
lib/            # framework-agnostic utilities
```

## State and data fetching

Server state is fetched with TanStack Query. Client state uses React context
or Zustand; Redux is not used in new code. All API calls go through the
generated client in `@larkspur/api-client`; hand-written `fetch` calls to
internal APIs are rejected in review.

## Testing

Unit tests use Vitest and React Testing Library. End-to-end tests use
Playwright and run against the `staging` environment nightly and on demand.
A component test MUST query by accessible role or label, never by CSS class.

## Accessibility

Every interactive element needs an accessible name. The `eslint-plugin-jsx-a11y`
rules are errors, not warnings. Colour contrast MUST meet WCAG 2.1 AA, which
the design system tokens guarantee when used as intended.

## Performance budgets

Customer-facing pages have a budget of 200 KB of compressed JavaScript on
initial load and a Largest Contentful Paint under 2.5 seconds at the 75th
percentile. The `bundle-budget` check fails a pull request that exceeds the
JavaScript budget.
