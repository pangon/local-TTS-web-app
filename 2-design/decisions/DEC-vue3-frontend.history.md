# DEC-vue3-frontend: Trail

> Companion to `DEC-vue3-frontend.md`.
> AI agents read this only when evaluating whether the decision is still
> valid or when proposing a change or supersession.

## Alternatives considered

### Option A: Vanilla JS (no build step)
- Pros: Zero dependencies, maximum simplicity, no build tool needed.
- Cons: Managing 6+ views with reactive state becomes verbose and error-prone. No component model. Poor developer experience for interactive UIs.

### Option B: Lightweight library (Alpine.js / HTMX, no build step)
- Pros: No build step, declarative bindings reduce boilerplate vs. vanilla JS.
- Cons: Limited component model. Less suitable for complex SPAs with multiple views and rich state management. Smaller ecosystem.

### Option C: Vue 3 + Vite (build step)
- Pros: Full component model, excellent reactivity system, single-file components, official router and state management. Large ecosystem, good documentation. Vite provides fast HMR and simple config.
- Cons: Requires a build step and npm in the development/build toolchain.

### Option D: Svelte + Vite (build step)
- Pros: Minimal boilerplate, compiled output (small bundles), intuitive syntax.
- Cons: Smaller ecosystem and community than Vue. Fewer resources for solo debugging.

### Option E: React + Vite (build step)
- Pros: Largest ecosystem.
- Cons: More verbose (JSX, hooks patterns), heavier runtime. More library choices needed (routing, state).

## Reasoning

The user explicitly preferred a framework with a build step (Option C/D/E) over no-build-step approaches (Option A/B). Among frameworks, Vue 3 was recommended for its balance of productivity, ecosystem size, and gentleness on a solo developer. The Composition API and single-file components keep related concerns co-located. Vite is the default Vue build tool with zero-config setup. The decision would be invalidated if the project needed server-side rendering or if the UI became simple enough that a no-framework approach sufficed.

## Human involvement

**Type**: human-decided

**Notes**: User explicitly chose Option C (framework with build step) when presented with three options, then accepted the Vue 3 recommendation over Svelte and React.

## Changelog

| Date | Change | Involvement |
|------|--------|-------------|
| 2026-03-11 | Initial decision | human-decided |
