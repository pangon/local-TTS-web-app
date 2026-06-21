Phase-specific instructions for the **Design** phase. Extends [../CLAUDE.md](../CLAUDE.md).

## Purpose

This phase defines **how** we're building the system. Focus on architecture, data models, APIs, and key technical decisions.

## Files in This Phase

| File | Purpose |
|------|---------|
| [`architecture.md`](architecture.md) | System architecture overview and diagrams |
| [`data-model.md`](data-model.md) | Data structures, schemas, and relationships |
| [`api-design.md`](api-design.md) | API specifications and contracts |
| [`decisions/`](decisions/) | Decision Records (`DEC-kebab-name`) |

---

## Decisions Relevant to This Phase

| File | Title | Trigger |
|------|-------|---------|
| [DEC-fastapi-backend](decisions/DEC-fastapi-backend.md) | Python + FastAPI Backend | When defining API endpoints, backend components, or startup commands |
| [DEC-vue3-frontend](decisions/DEC-vue3-frontend.md) | Vue 3 + Vite Frontend | When defining UI views, component structure, or frontend build |
| [DEC-sqlite-metadata](decisions/DEC-sqlite-metadata.md) | SQLite for Metadata Storage | When defining data models or storage patterns |
| [DEC-single-process](decisions/DEC-single-process.md) | Monolithic Single-Process Architecture | When defining component boundaries, background processing, or deployment |
| [DEC-sse-progress](decisions/DEC-sse-progress.md) | Server-Sent Events for Real-Time Updates | When implementing progress reporting or live status updates |
| [DEC-tts-as-backend-module](decisions/DEC-tts-as-backend-module.md) | TTS Engine as Backend Submodule | When defining component boundaries or modifying architecture |
| [DEC-text-preprocessing-pipeline](decisions/DEC-text-preprocessing-pipeline.md) | Modular Backend Text-Preprocessing Pipeline | When modifying the preprocessing pipeline structure, its stages, or its configuration model |
| [DEC-preprocess-review-flow](decisions/DEC-preprocess-review-flow.md) | Synchronous Preprocess-then-Confirm Synthesis Flow | When modifying the preprocess/synthesis API contracts or the normalized-text review flow |
| [DEC-model-license-disclosure](decisions/DEC-model-license-disclosure.md) | Permit Open-Weight Non-FOSS Models with Frontend License Disclosure | When adding a model to the Compatibility Table, defining model metadata, or changing the model-listing / `GET /models` contract |
| [DEC-transformers-5x-baseline](decisions/DEC-transformers-5x-baseline.md) | Backend transformers baseline (exploratory: MOSS-TTSD needs ≥5.x; Qwen3-TTS / Fish S2-Pro need 4.57.3) | When adding a model to the Compatibility Table or choosing a model-loading library/approach (must fit the exploratory baseline — installable on 4.57.3 ⇄ 5.x) |

---

## Linking to Other Phases

- Reference requirements from `1-objectives/` to justify design choices
- Design documents guide implementation in `3-code/`
- Infrastructure design informs deployment in `4-deploy/`
