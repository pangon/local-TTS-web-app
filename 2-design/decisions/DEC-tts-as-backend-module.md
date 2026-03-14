# DEC-tts-as-backend-module: TTS Engine as Backend Submodule

**Status**: Active

**Category**: Architecture

**Scope**: backend

**Source**: [REQ-MNT-modular-ai-layer](../../1-objectives/requirements/REQ-MNT-modular-ai-layer.md), [CON-solo-developer](../../1-objectives/constraints/CON-solo-developer.md), [CON-single-user](../../1-objectives/constraints/CON-single-user.md)

**Last updated**: 2026-03-14

## Context

The original component decomposition placed the TTS engine as a separate top-level component (`3-code/tts-engine/`) alongside the backend (`3-code/backend/`). Both are Python components running in the same process (DEC-single-process), sharing the same language and runtime.

This separation created a cross-component configuration tension: two Python components need a shared `pyproject.toml` for dependency management, but the component isolation rules in `CLAUDE.code.md` prohibit cross-component configuration files. The single-process architecture (DEC-single-process) means the TTS engine is always loaded into the backend process via direct function calls — it is never deployed or run as an independent service.

## Decision

The TTS engine is a **subpackage within the backend component**, not a separate top-level component. It lives at `3-code/backend/src/<package>/tts/` (or equivalent) and maintains a clean interface boundary via a `TTSEngine` class, satisfying REQ-MNT-modular-ai-layer.

The project has **two components**: frontend and backend.

## Enforcement

### Trigger conditions

- **Design phase**: when defining component boundaries or modifying architecture
- **Code phase**: when implementing TTS engine functionality or organizing backend package structure

### Required patterns

- TTS engine code resides inside the backend source tree as a dedicated subpackage (e.g., `tts/`)
- The `TTSEngine` class provides the public interface — backend services import and call it directly
- TTS engine subpackage must not import from backend services (unidirectional dependency: services → tts, never tts → services)
- All TTS dependencies (PyTorch, HuggingFace Transformers/Hub) are declared in the backend's `pyproject.toml`

### Required checks

1. Verify TTS engine code is within the backend directory, not at the top level
2. Verify no circular imports between TTS subpackage and backend services
3. Verify `TTSEngine` class exists with a clean public interface

### Prohibited patterns

- Separate top-level `tts-engine/` component directory
- TTS engine code importing from backend application services (e.g., Job Service, Model Service)
- Separate `pyproject.toml` for TTS engine
