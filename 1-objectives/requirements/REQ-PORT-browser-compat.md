# REQ-PORT-browser-compat: Desktop Browser Compatibility

**Type**: Portability

**Status**: Approved

**Priority**: Should-have

**Source**: [GOAL-browser-ui](../goals/GOAL-browser-ui.md)

**Source stakeholder**: [STK-end-user](../stakeholders.md)

## Description

The web interface must function correctly on current stable versions of Chrome, Firefox, and Edge on desktop. All core workflows (text upload, synthesis, playback, library browsing) must work without browser-specific workarounds.

## Acceptance Criteria

- Given the latest stable version of Chrome, Firefox, or Edge on desktop, when the user accesses any core workflow, then it functions correctly without errors or layout breakage
- Given the codebase, then no browser-specific hacks or vendor-prefixed APIs are used without a standards-based fallback

## Related Assumptions

- [ASM-browser-mp3-playback](../assumptions/ASM-browser-mp3-playback.md) — MP3 playback is a subset of overall browser compatibility
