# REQ-MNT-modular-ai-layer: Modular AI Execution Layer

**Type**: Maintainability

**Status**: Draft

**Priority**: Should-have

**Source**: [US-evaluate-local-ai](../user-stories/US-evaluate-local-ai.md)

**Source stakeholder**: [STK-developer](../stakeholders.md)

## Description

The AI execution layer (TTS inference) shall have clear interfaces separated from the web application layer, allowing extraction into a standalone project without major refactoring.

## Acceptance Criteria

- Given the codebase, when reviewing the AI execution layer, then it has well-defined interfaces that do not depend on the web framework
- Given the AI execution layer, then it can be invoked independently of the web application (e.g., via a script or CLI)
