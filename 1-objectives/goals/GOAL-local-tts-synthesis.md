# GOAL-local-tts-synthesis: Local Text-to-Speech Synthesis

**Description**: Convert text to speech entirely on the local machine, with no external API calls. This is the core value proposition — privacy and independence from cloud services.

**Status**: Approved

**Priority**: Must-have

**Source stakeholder**: [STK-end-user](../stakeholders.md)

## Success Criteria

- [ ] Users can input text and receive synthesized audio output
- [ ] All speech synthesis runs locally (no network requests to external TTS services)
- [ ] At least one TTS model/engine is bundled or easily installable

## Related Artifacts

- User stories: [US-create-audiobook](../user-stories/US-create-audiobook.md), [US-synthesize-text-input](../user-stories/US-synthesize-text-input.md)
- Requirements: [REQ-F-gpu-validation](../requirements/REQ-F-gpu-validation.md), [REQ-COMP-foss-only](../requirements/REQ-COMP-foss-only.md)
