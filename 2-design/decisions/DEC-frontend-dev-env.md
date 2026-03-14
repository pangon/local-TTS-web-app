# DEC-frontend-dev-env: Frontend Development Environment Conventions

**Status**: Active

**Category**: Convention

**Scope**: frontend

**Source**: [DEC-vue3-frontend](DEC-vue3-frontend.md), [CON-solo-developer](../../1-objectives/constraints/CON-solo-developer.md)

**Last updated**: 2026-03-14

## Context

The frontend component needs a consistent, reproducible development environment. Without a recorded convention, each task would re-discover how to manage Node.js versions, install dependencies, run tests, and build — wasting effort and risking inconsistency.

## Decision

The frontend uses the following environment conventions:

- **Node.js version management**: nvm with `.nvmrc` file in `3-code/frontend/` (pinned to major version 22).
- **Package manager**: npm (ships with Node.js).
- **Language**: TypeScript with `<script setup lang="ts">` in Vue components.
- **Build tool**: Vite (per DEC-vue3-frontend).
- **Test runner**: Vitest with jsdom environment. Tests live in `3-code/frontend/src/__tests__/`.
- **Type checking**: `vue-tsc --build` via `npm run type-check`.
- **Node.js requirement**: `^20.19.0 || >=22.12.0` (per `engines` in `package.json`).

## Enforcement

### Trigger conditions

- **Code phase**: when installing dependencies, running tests, building, or adding new frontend modules

### Required patterns

- Run `nvm use` in the `3-code/frontend/` directory before any npm/node commands (picks up `.nvmrc`).
- New dependencies go in `package.json` under `dependencies` (runtime) or `devDependencies` (dev-only).
- Tests use Vitest and live in `src/__tests__/` under the frontend directory.
- Vue components use Composition API with `<script setup lang="ts">`.

### Required checks

1. Run `nvm use` to ensure correct Node.js version before running commands.
2. After adding dependencies to `package.json`, run `npm install`.

### Prohibited patterns

- Installing packages globally or outside the project.
- Using alternative package managers (yarn, pnpm) unless the team explicitly switches.
- Using the Options API for new components (Composition API only per DEC-vue3-frontend).
- Using alternative test runners (Jest, Mocha) instead of Vitest.
