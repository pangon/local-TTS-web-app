# DEC-frontend-dev-env: Trail

> Companion to `DEC-frontend-dev-env.md`.
> AI agents read this only when evaluating whether the decision is still
> valid or when proposing a change or supersession.

## Alternatives considered

### Option A: npm + nvm + Vitest (chosen)
- Pros: npm ships with Node.js (no extra install); nvm is already available on the system; Vitest is Vite-native and fast; minimal tooling surface area
- Cons: npm is slower than pnpm for large dependency trees; nvm is bash-only (no native Windows support, but Node version is also tracked in `engines` field)

### Option B: pnpm + volta + Jest
- Pros: pnpm is faster and more disk-efficient; Volta is cross-platform; Jest is widely known
- Cons: Extra tools to install; Jest requires additional configuration for Vite/Vue; Volta not present on system

## Reasoning

Chose the simplest stack that works with what's already installed. nvm is present on the system, npm ships with Node.js, and Vitest integrates natively with Vite (the project's build tool). This minimizes setup friction for a solo developer while staying within FOSS constraints.

## Human involvement

**Type**: ai-proposed/human-approved

**Notes**: Proposed alongside TASK-vue-project-scaffold execution; user confirmed conventions before implementation.

## Changelog

| Date | Change | Involvement |
|------|--------|-------------|
| 2026-03-14 | Initial decision | ai-proposed/human-approved |
