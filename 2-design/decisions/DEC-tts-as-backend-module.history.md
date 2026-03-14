# DEC-tts-as-backend-module: Trail

> Companion to `DEC-tts-as-backend-module.md`.
> AI agents read this only when evaluating whether the decision is still
> valid or when proposing a change or supersession.

## Alternatives considered

### Option A: Keep TTS engine as separate top-level component

- Pros: Stronger separation; could be used independently (CLI, scripts); clearer boundary in file system
- Cons: Creates cross-component configuration tension (shared pyproject.toml violates component isolation rules); adds complexity for a single-process, single-user app; the "independent usage" benefit is theoretical given CON-single-user

### Option B: TTS engine as backend submodule (chosen)

- Pros: Eliminates cross-component config tension; matches single-process reality (DEC-single-process); simpler project structure; one pyproject.toml; still modular via clean package interface
- Cons: Slightly harder to extract later if independent usage is ever needed; backend directory is larger

### Option C: Shared configuration directory at 3-code/ level

- Pros: Keeps both components; shared pyproject.toml lives outside both
- Cons: Directly violates component isolation rules; creates a precedent for cross-component coupling; still two Python packages to manage

## Reasoning

The single-process architecture (DEC-single-process) means the TTS engine always runs inside the backend process. Maintaining it as a separate component adds structural overhead without practical benefit — the "independent usage" scenario is not supported by any requirement or constraint. The modularity requirement (REQ-MNT-modular-ai-layer) is fully satisfied by a well-defined subpackage with a clean interface boundary. The cross-component configuration tension was the immediate trigger, but the deeper reason is that the separation does not match the deployment and runtime reality.

## Human involvement

**Type**: ai-proposed/human-approved

**Notes**: AI identified the cross-component configuration tension during TASK-python-project-scaffold preparation. User evaluated three options (keep separate with scoped exception, shared config, merge as submodule) and chose the submodule approach.

## Changelog

| Date | Change | Involvement |
|------|--------|-------------|
| 2026-03-14 | Initial decision | ai-proposed/human-approved |
