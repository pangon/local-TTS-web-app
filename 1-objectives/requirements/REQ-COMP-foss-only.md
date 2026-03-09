# REQ-COMP-foss-only: All Dependencies Free and Open-Source

**Type**: Compliance

**Status**: Draft

**Priority**: Must-have

**Source**: [GOAL-local-tts-synthesis](../goals/GOAL-local-tts-synthesis.md)

**Source stakeholder**: [STK-end-user](../stakeholders.md)

## Description

All software dependencies (libraries, frameworks, TTS models) must be free and open-source. No paid APIs, proprietary libraries, or commercial SaaS components are permitted.

## Acceptance Criteria

- Given the project's dependency list, then every library and framework is available under a free and open-source license
- Given the TTS models used, then each model is open-weight and freely licensed for personal use
- Given the full application stack, then no component requires a paid subscription, API key for a commercial service, or proprietary license

## Related Constraints

- [CON-zero-budget](../constraints/CON-zero-budget.md) — no paid services, APIs, or libraries; all components free and open-source
