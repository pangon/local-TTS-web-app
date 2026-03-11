# DEC-vue3-frontend: Vue 3 + Vite Frontend

**Status**: Active

**Category**: Architecture

**Scope**: frontend

**Source**: [CON-solo-developer](../../1-objectives/constraints/CON-solo-developer.md)

**Last updated**: 2026-03-11

## Context

The application needs a multi-view SPA (6 views: creation, library, playback, model management, monitoring, text preview) with reactive state for real-time progress updates, audio playback, and form interactions. The solo developer constraint requires a framework with good documentation, a manageable learning curve, and a productive development experience.

## Decision

Use **Vue 3** (Composition API) as the frontend framework, with **Vite** as the build tool. The production build is served as static files by the FastAPI backend.

## Enforcement

### Trigger conditions

- **Design phase**: when defining UI views, component structure, or frontend data flow
- **Code phase**: when implementing any frontend functionality
- **Deploy phase**: when building the frontend for production

### Required patterns

- Frontend is a Vue 3 SPA using the Composition API.
- Vite is the build and dev server tool.
- Vue Router handles client-side routing.
- In development, Vite dev server proxies API requests to FastAPI.
- In production, the Vue build output is served as static files by FastAPI.

### Required checks

1. New frontend dependencies must be compatible with Vue 3.
2. Components use the Composition API (`<script setup>`) style.

### Prohibited patterns

- No alternative frontend frameworks (React, Svelte, Angular) in the project.
- No Options API for new components (Composition API only for consistency).
