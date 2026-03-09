# CON-zero-budget: Zero Budget

**Category**: Business

**Status**: Active

**Source stakeholder**: [STK-end-user](../stakeholders.md)

## Description

No money will be spent on external services, paid APIs, paid libraries, or cloud hosting. All software components must be free and open-source.

## Rationale

The project exists to avoid recurring costs for cloud TTS services. The developer's own hardware is the only infrastructure. Keeping the entire stack free and open-source ensures long-term sustainability without financial commitment.

## Impact

- All TTS models must be open-weight and freely licensed for personal use.
- No SaaS dependencies for any part of the pipeline (synthesis, storage, delivery).
- All libraries and frameworks must be free and open-source.
- Hosting is exclusively on the developer's own machine — no cloud infrastructure costs.
- Reinforces GOAL-local-tts-synthesis and GOAL-huggingface-models.

## Related Artifacts

- [REQ-COMP-foss-only](../requirements/REQ-COMP-foss-only.md) — all dependencies free and open-source
