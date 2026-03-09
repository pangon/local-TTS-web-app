# GOAL-quick-tts-preview: Quick TTS from Direct Text Input

**Description**: Allow users to type or paste text directly into the web interface and synthesize speech immediately, without uploading a file. This enables quick voice and model previews and short-form TTS use cases, complementing the file-based audiobook creation workflow.

**Status**: Approved

**Priority**: Should-have

**Source stakeholder**: [STK-end-user](../stakeholders.md)

## Success Criteria

- [ ] Users can enter text in a text field and trigger synthesis
- [ ] Audio plays back directly in the browser after synthesis
- [ ] Works with the currently selected model and voice
- [ ] Preview audio is ephemeral — not persisted and not added to the audiobook library

## Related Artifacts

- User stories: [US-synthesize-text-input](../user-stories/US-synthesize-text-input.md)
- Requirements: [REQ-F-text-preview](../requirements/REQ-F-text-preview.md), [REQ-PERF-synthesis-latency](../requirements/REQ-PERF-synthesis-latency.md)
