---
name: SDLC-design
description: Draft or update design documents based on approved objectives. Use when translating requirements into technical specifications. Covers architecture, data model, and API design.
---

## Instructions

You are working in the Design phase, creating or updating architecture, data model, or API design documents.

### Phase Validation

Before doing anything else, read the `### Current State` subsection under `## Project Overview` in `CLAUDE.md` and determine which phase the project is in. Then follow the matching case below:

1. **Project not initialized** — the Current State lacks a real project description (e.g., mentions "not yet been initialized" or "base scaffold"). **Stop**, recommend `/SDLC-init`, and do not proceed.

2. **Project is in the Objectives phase** — the Current State mentions "Objectives phase", lists objectives artifacts being drafted, or no phase beyond Objectives has been started.

   Read the index tables in `1-objectives/CLAUDE.objectives.md` and evaluate the Objectives → Design phase gate preconditions:

   - **(a)** At least one goal with `Status: Approved`
   - **(b)** At least one requirement with `Status: Approved`
   - **(c)** Gap analysis recorded in the Current State and fresh (not stale, no Critical gaps)

   Then respond based on the results:

   - **If (a) or (b) are not met** — elicitation is incomplete. **Stop**, list what is missing, recommend `/SDLC-elicit`, and do not proceed.
   - **If (a) and (b) are met but (c) is not met** (no gap analysis, stale, or Critical gaps) — **strongly recommend** running a gap analysis via `/SDLC-elicit` before design. Proceed only on explicit user confirmation.
   - **If all preconditions are met** — inform the user of any remaining Important/Minor gaps (non-blocking) and proceed with Setup.

3. **Project is in the Design phase** — the Current State indicates the project is in the Design phase (e.g., mentions "Design phase", "architecture", "design documents being worked on", or no phase beyond Design has been started), **proceed normally** with the Setup steps below.

4. **Project has advanced beyond Design** — the Current State indicates the project is in Code or Deploy phase. **Warn** that modifying Design artifacts may impact downstream tasks or deployed code. If the user confirms, proceed but flag downstream dependencies that could be affected.

### Setup

1. Read `2-design/CLAUDE.design.md` (phase instructions and decisions index).
2. Read any decisions whose trigger conditions apply.

### Workflow

#### 1. Assess Current State

Before doing anything else, determine what already exists:

- Read `2-design/architecture.md`, `2-design/data-model.md`, and `2-design/api-design.md` to understand what design work has been done.
- Summarize the current design state to the user: which documents exist, which are empty or incomplete, and what the logical next step is.

#### 2. Load Objectives Artifacts

Read **only the index tables** in `1-objectives/CLAUDE.objectives.md` — do **not** open individual artifact files yet. Use the summary column in each index to determine relevance:

- **Requirements Index** — identify which requirements apply to the current design work.
- **Goals Index** — identify which goals the design must satisfy.
- **Constraints Index** — identify hard limits that affect design choices.
- **Assumptions Index** — identify assumptions that inform feasibility and trade-offs.
- **User Stories Index** — identify stories that provide user-facing context.

**Then**, for each artifact whose summary indicates it is relevant to the design task at hand, read the individual file to get full details. Skip artifacts that are clearly unrelated — there is no need to read every file.

**Flag draft artifacts**: if any requirements, user stories, or assumptions relevant to the current design work are still in `Draft` status, warn the user before proceeding. Draft artifacts may change, and designing against them introduces risk.

#### 3. Guide the Design Process

Follow this progression — each step builds on the previous one:

**a. Architecture** (`2-design/architecture.md`)
- Define the system's components and their responsibilities.
- Choose the simplest architecture that satisfies all approved requirements.
- Document component interactions using Mermaid diagrams.
- Reference requirements by ID (e.g., `REQ-F-search-by-name`) for traceability.
- Ensure constraints from `1-objectives/constraints/` are respected.

**b. Data Model** (`2-design/data-model.md`)
- Define data structures and schemas informed by the architecture.
- Document types, relationships, and lifecycle (creation, updates, deletion).
- Align with component responsibilities established in the architecture.

**c. Interface Design** (`2-design/api-design.md`)
- Specify APIs and contracts between the components defined in the architecture.
- Follow REST conventions or document deviations.
- Define request/response formats, error handling, and status codes.

The user does not have to complete all three documents in a single session. If the architecture is not yet defined, start there. If the architecture exists but the data model is missing, start with the data model, and so on.

#### 4. Present and Write

- **Present the draft** to the user for review before writing. Highlight:
  - Which requirements are addressed
  - Any requirements that cannot be addressed yet (and why)
  - Design trade-offs made
- **After user approval**, write the document.

### Decision Triggers

Decisions must be captured whenever the user shapes the design — not only when a technical pattern emerges. Follow the recording, deprecation, and supersession procedures in [`2-design/decisions/PROCEDURES.md`](../../../2-design/decisions/PROCEDURES.md).

**When to create a new decision:**
- A significant technical pattern emerges (error handling, data flow, security, naming conventions, etc.).
- The user **approves a design choice** — the approval itself is the decision; record it immediately.
- The user **expresses a preference** (e.g., "I'd rather use SQLite than PostgreSQL", "let's keep the API REST-only") — treat every stated preference as a decision to record.

**When to modify an existing decision:**
- The user **changes their mind** about a previously recorded decision — follow the deprecation or supersession procedure in `PROCEDURES.md`.
- New information invalidates or narrows a prior decision — propose an update and wait for approval before modifying.

**Rules:**
- Do **not** silently embed decisions into design documents without recording them as `DEC-*` artifacts.
- Do **not** wait until the end of the session — record or update decisions as soon as they are confirmed.
- When in doubt about whether something qualifies as a decision, surface it to the user and ask.

### Interaction Style

- Ask one topic at a time — closely related design questions may be grouped together (e.g., "Which components need persistent storage, and what are their data access patterns?"), but avoid mixing unrelated topics in a single turn. Wait for the user's answer before moving to the next topic.
- When the architecture involves trade-offs or multiple valid approaches, present the options with pros and cons and let the user choose.
- After gathering enough information, propose the content and ask for confirmation before writing the file. **Multiple related design sections may be proposed together** in a single batch (e.g., two component descriptions at once, several API endpoints at once). Present each section clearly so the user can approve, modify, or decline them individually.
- When the user confirms, write the document or section.
- **After completing an approved action or after the user declines a proposal, briefly summarize what was done, then ask the user how they want to proceed.** Do not jump directly into the next design step.
- When the user asks for suggestions or is unsure what to do next, suggest the next design step based on the progression (architecture → data model → interfaces) and the current state of the design documents.
- Surface potential conflicts between requirements and design constraints immediately — do not resolve silently. When a design choice impacts multiple documents, note the cross-document implications.

### Current State Tracking

Whenever the skill applies user-approved changes (creating or updating design documents, recording decisions), update the `### Current State` subsection under `## Project Overview` in `CLAUDE.md` to reflect:

1. **Phase transition** — if this is the first design work in the project (transitioning from Objectives to Design), **rewrite** the Current State section: replace the Objectives-phase information (artifact counts, statuses, gap analysis details, etc.) with a fresh Design-phase summary.
2. **Design documents status** — list which design documents have content and which are still empty or incomplete (e.g., "Architecture drafted; data model and API design pending"). Update this incrementally as documents are created or modified.
3. **Decisions recorded** — note the count of decisions created (e.g., "3 decisions recorded"). Update this when new decisions are recorded.

### Rules

- **Current State synchronization**: whenever design documents are created, updated, or decisions are recorded, update `### Current State` in `CLAUDE.md` as described in the Current State Tracking section above. This update must happen in the same operation as the design change.
- Always reference requirements by ID (e.g., `REQ-F-search-by-name`) for traceability.
- Use Mermaid diagrams where they add clarity.
- Default to the simplest design that satisfies all requirements.
- If a requirement is ambiguous or contradictory, surface it — do not resolve silently.
- Check that constraints from `1-objectives/constraints/` are respected in the design.
