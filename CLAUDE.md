## Language Policy

**All AI outputs must be in English**, regardless of the language used in user prompts. This applies to code, comments, documentation, configuration files, commit messages, and response text.

---

## Project Overview

**Local TTS Web App** — A web application that provides text-to-speech functionality running locally. It allows users to convert text into spoken audio through a browser-based interface without relying on external cloud services.

This repository uses a structured, AI-first development lifecycle. All project knowledge — objectives, design, decisions, tasks — lives alongside the source code.

### Current State

The project is in the Code phase. Architecture drafted (updated 2026-06-16 — added Preprocessing Service to Application Services, a Text Preprocessing Pipeline section (4 modular stages + per-language/per-model config), and text-normalization requirement traceability; 2026-04-11 — added Model-Specific Loading Requirements section with compatibility table and adapter pattern); data model drafted (updated 2026-06-16 — added Text Preprocessing (No Persistence) note: no new entities/schema; 2026-06-15 — schema timestamp DEFAULTs use `strftime('%Y-%m-%dT%H:%M:%SZ','now')` to emit ISO 8601 UTC); API design drafted (updated 2026-06-16 — added `POST /preprocess`, changed `POST /jobs/synthesis` from multipart file upload to JSON confirmed text, noted preview consumes already-normalized text, moved `REQ-F-upload-text-file` traceability to `/preprocess`; 2026-06-15 — added `total_duration_seconds` to `GET /audiobooks`, per-chapter `file_size_bytes` to `GET /audiobooks/{id}`, and expanded the `PUT /audiobooks/{id}/position` save triggers to include periodic 20s and page-unload `keepalive` saves; 2026-06-15 — clarified ISO 8601 UTC `Z` timestamp convention; 2026-04-11 — added `loader_available` field to `GET /models` response). 11 decisions recorded (DEC-fastapi-backend, DEC-vue3-frontend, DEC-sqlite-metadata, DEC-single-process, DEC-sse-progress, DEC-tts-as-backend-module, DEC-python-backend-env, DEC-frontend-dev-env, DEC-default-italian-language, DEC-text-preprocessing-pipeline, DEC-preprocess-review-flow — the last two added 2026-06-16 for text normalization). Objectives: 11 Goals, 14 User Stories, 35 Requirements (all approved); 6 Constraints (all active); 6 Assumptions (all verified). Text-normalization capability added & approved 2026-06-16 via SDLC-elicit (need surfaced during testing — raw inputs, esp. PDF→txt, require substantial cleaning before TTS): GOAL-text-normalization (Must) + US-clean-text-for-tts (Must), US-extensible-text-preprocessing (Should) + REQ-F-text-numeric-symbolic-verbalization, REQ-F-text-unicode-sanitization, REQ-F-text-layout-repair (Must), REQ-F-abbreviation-expansion, REQ-MNT-preprocessing-pipeline (Should) + ASM-input-text-quality-varies (Verified 2026-06-16 via developer testing). Two follow-up requirements added & approved 2026-06-16: REQ-PERF-preprocessing-overhead (Should — bounds preprocessing latency; addresses the assessment's Important finding without modifying the approved REQ-PERF-synthesis-latency) and REQ-USA-normalized-text-review (Should — user reviews/confirms normalized text before generation). Downstream design for text normalization drafted 2026-06-16 via SDLC-design (Preprocessing Service as a separate backend module per user choice; synchronous `/preprocess` + confirm-then-synthesize flow per DEC-preprocess-review-flow); implementation tasks created 2026-06-16 as Phase 5.1 (see implementation plan below). The affected already-Done tasks were annotated, not reopened: their successors are TASK-synthesis-api-text-input (multipart→JSON contract) and TASK-creation-view-review-step (review step); TASK-preview-job-service / TASK-text-preview-view (Phase 6, Todo) now depend on TASK-preprocess-api and integrate preprocessing + inline review. Completeness assessment (2026-06-16, post-preprocessing-design — supersedes earlier 2026-06-16 and 2026-03-11 assessments): 0 Critical, 0 Important; all 35 approved requirements satisfiable, no constraint violated, no unverified-assumption risk, both new decisions recorded. 5 Minor (non-blocking): (1) subjective "measurably more natural" goal criterion (testing concern); (2) frontend must pass the same `language` to `/preprocess` and `/jobs/synthesis`; (3) disk preflight now estimates from JSON `text` length (adjust TASK-synthesis-job-api rework); (4) synchronous `/preprocess` has no SSE progress — UI busy state needed; (5) domain-dictionary file delivery refinable during implementation. Design → Code gate satisfied (no Critical). Objectives phase satisfies the Design gate (no Critical). 2 components identified (2026-03-14): frontend, backend; TTS engine merged into backend as subpackage per DEC-tts-as-backend-module. Implementation plan created (2026-03-12, updated 2026-06-16): 10 phases + Phase 3.1 + Phase 5.1, 74 tasks covering all 11 approved goals; Phase 3.1 scoped to adapter abstraction, Kokoro and Qwen3-TTS loaders (5 tasks); Phase 5.1 added (2026-06-16) for text preprocessing & normalized-text review covering GOAL-text-normalization (9 tasks: pipeline skeleton + 4 stages, `POST /preprocess`, JSON-text synthesis contract, creation-view review step, manual testing) — sequenced before the Should-have Phases 6–9 since it is Must-have and modifies the Phase 4 synthesis path; `TASK-synthesis-api-text-input` supersedes the multipart contract of the done `TASK-synthesis-job-api`, and `TASK-creation-view-review-step` adds the review step to the done `TASK-audiobook-creation-view`; Phase 9 (optional) added for additional model adapters (10 tasks); Phase 10 added (2026-06-15) for a database migration mechanism (PRAGMA user_version + startup migration runner; 2 tasks) — currently `init_db` has no migration path, so schema changes apply only to fresh databases. Implementation progress: 37/74 tasks done, Phase 3 complete (6/6 tasks done), Phase 3.1 complete (5/5 tasks done — TASK-model-adapter-interface, TASK-model-loader-status, TASK-loader-kokoro, TASK-loader-qwen3-tts, TASK-phase-3.1-manual-testing complete), Phase 4 complete (6/6 tasks done), Phase 5 complete (6/6 tasks done — TASK-library-api, TASK-chapter-audio-streaming, TASK-playback-position-api, TASK-library-view, TASK-playback-view, TASK-phase-5-manual-testing complete; manual-testing runbook now covers Phases 1-5), Phase 5.1 in progress (1/9 tasks done — TASK-preprocessing-pipeline-skeleton complete: Preprocessing Service package `src/local_tts/preprocessing/` with the `Stage` protocol + name-keyed registry, `Pipeline` runner, two-axis language/model profile resolution, optional domain-dictionary loader, and the `PreprocessingService` orchestrator; canonical `STAGE_*` name constants + the `register_stage` seam in `preprocessing/__init__.py` define the contract for the 4 stage tasks; 45 new tests, no GPU dependency). Post-Phase-5 enhancements applied via SDLC-fix (2026-06-15): library listing shows total chapter duration; playback view shows the generating TTS model and per-chapter on-disk file size; playback position now also saves periodically (every 20s while playing) and on page navigation/reload/close (keepalive). Next actionable task: TASK-stage-unicode-sanitization (Phase 5.1, first concrete pipeline stage).

---

## Phase-Specific Instructions

Each phase directory contains a `CLAUDE.<phase>.md` file. When working in a phase:

1. Read the phase-specific instructions — they extend (not override) this file
2. Consult the decisions index in that phase file before starting work
3. Work within the appropriate phase structure

| Phase | Directory | Focus |
|-------|-----------|-------|
| **Objectives** | `1-objectives/` | Define what to build and why |
| **Design** | `2-design/` | Define how to build it |
| **Code** | `3-code/` | Build it |
| **Deploy** | `4-deploy/` | Ship and operate it |

### Cross-Skill Artifact Procedures

Any modification to phase artifacts — whether performed inside a skill, during a free-prompt conversation, or as a side effect of any other task — must follow the authoritative procedures for that phase:

- **Objectives artifacts** (`1-objectives/`): follow the procedures in [`.claude/skills/SDLC-elicit/SKILL.md`](.claude/skills/SDLC-elicit/SKILL.md) — including traceability rules, status downgrade on modification, index synchronization, bidirectional link maintenance, and Current State tracking.
- **Design artifacts** (`2-design/`): follow the procedures in [`.claude/skills/SDLC-design/SKILL.md`](.claude/skills/SDLC-design/SKILL.md) — including downstream effect checks, decision recording triggers, requirement coverage verification, and Current State tracking.
- **Code phase task artifacts** (`3-code/tasks.md`): follow the procedures in [`.claude/skills/SDLC-implementation-plan/SKILL.md`](.claude/skills/SDLC-implementation-plan/SKILL.md) — including phased task grouping, traceability links, incremental deployability, and Current State tracking.

### Phase Gates

Before creating artifacts in the next phase, check these minimum preconditions. Gates are advisory — warn the user if not met, but proceed if they confirm.

| Transition | Preconditions |
|------------|---------------|
| Objectives → Design | Stakeholders defined; at least one goal Approved; at least one requirement Approved; gap analysis recorded in Current State and fresh (not stale, no Critical gaps) |
| Design → Code | All design documents drafted (`architecture.md`, `data-model.md`, `api-design.md`); completeness assessment recorded in Current State and fresh (not stale, no Critical findings); components identified (per-component directories in `3-code/`) |

There is no gate between Code and Deploy. Deploy activities (deployments, runbooks, infrastructure setup) can happen at any time during the Code phase.

---

## Artifacts

All project knowledge — goals, requirements, assumptions, constraints, design decisions, tasks — is captured as structured markdown files alongside the source code. This gives AI agents the full context that human developers would normally carry in their heads or scattered across external tools, and creates a traceability chain from business goals to deployed code.

### Types and locations

| Prefix | Artifact | Location |
|--------|----------|----------|
| `GOAL` | Goals | `1-objectives/goals/` |
| `US` | User Stories | `1-objectives/user-stories/` |
| `REQ-CLASS` | Requirements | `1-objectives/requirements/` |
| `ASM` | Assumptions | `1-objectives/assumptions/` |
| `CON` | Constraints | `1-objectives/constraints/` |
| `STK` | Stakeholders | `1-objectives/stakeholders.md` (rows) |
| `DEC` | Decisions | `2-design/decisions/` |
| `TASK` | Tasks | `3-code/tasks.md` (rows) |

### Naming

All artifact IDs use the pattern `PREFIX-kebab-name` — a type prefix followed by a descriptive kebab-case name. The descriptive name **is** the unique identifier (e.g., `DEC-use-postgres`, `REQ-F-search-by-name`). There are no numeric sequences, to avoid ID collisions when working on parallel branches.

### Phase indexes

Every `CLAUDE.<phase>.md` file contains index tables listing the artifacts in that phase. Each index must include a **File column** with a relative link to the artifact file, so that AI agents can discover the file name and human reviewers can navigate easily.

---

## Graduated Safeguards

AI agents operate autonomously within development tasks. For project-level decisions, the scaffold defines three tiers:

| Tier | When | Agent behavior |
|------|------|----------------|
| **Always ask** | Conflict resolution, design gaps, decision deprecation/supersession, phase gate advancement | Stop, present options, wait for human approval |
| **Ask first time, then follow precedent** | Naming conventions, error handling patterns, test structure | Ask once, record the decision, apply consistently afterward |
| **Decide and record** | Routine implementation choices within established patterns | Decide autonomously, record in the appropriate artifact |

When spotting a related issue, potential improvement, or ambiguous situation during a task, **surface it to the user** instead of silently deciding to act or not act.

---

## Decisions

Decisions live in `2-design/decisions/`. Each decision has two files:

- **`DEC-kebab-name.md`** — the active record (context, decision, enforcement). Read during normal task execution.
- **`DEC-kebab-name.history.md`** — the trail (alternatives, reasoning, changelog). Read only when evaluating or changing a decision.

Each `CLAUDE.<phase>.md` contains a decisions index with trigger conditions. A decision may appear in multiple phase indexes.

### How to use decisions during tasks

1. Consult the decisions index in the current phase's `CLAUDE.<phase>.md`, or in a component-specific `CLAUDE.<component>.md` when working within a specific component.
2. Follow the File column link to read the relevant `DEC-*.md` file.
3. Apply its enforcement rules.

Do **not** modify `*.history.md` except to append to the changelog.

### Recording, deprecating, or superseding decisions

When a significant decision, pattern, or constraint emerges, record it as a new decision. For the recording procedure, as well as deprecation and supersession, see [`2-design/decisions/PROCEDURES.md`](2-design/decisions/PROCEDURES.md).

---

## After Making Changes

Evaluate whether to:

1. **Update this file** if project-wide patterns or architecture change significantly.
2. **Update phase-specific files** (`CLAUDE.<phase>.md`) if phase-specific patterns or conventions are established.
3. **Create new instruction files** if a workflow becomes complex enough to need dedicated guidance.

Proactively suggest these updates when relevant.
