# GOAL-audiobook-creation: Audiobook Creation from Text Files

**Description**: Create complete audiobooks from text files (txt), processing the full document into audio. This extends basic TTS into a batch workflow that produces persistent, replayable audio content.

**Status**: Approved

**Priority**: Must-have

**Source stakeholder**: [STK-end-user](../stakeholders.md)

## Success Criteria

- [ ] Users can upload a .txt file and trigger audiobook generation
- [ ] The system processes the full text into a coherent audio output
- [ ] When the source text contains chapter structure, the system produces one audio file per chapter
- [ ] Generated audiobooks are persisted for later access

## Related Artifacts

- User stories: [US-create-audiobook](../user-stories/US-create-audiobook.md)
- Requirements: [REQ-F-upload-text-file](../requirements/REQ-F-upload-text-file.md), [REQ-F-synthesize-audiobook](../requirements/REQ-F-synthesize-audiobook.md), [REQ-F-chapter-split-output](../requirements/REQ-F-chapter-split-output.md), [REQ-F-synthesis-progress](../requirements/REQ-F-synthesis-progress.md), [REQ-F-disk-space-preflight](../requirements/REQ-F-disk-space-preflight.md), [REQ-PERF-synthesis-latency](../requirements/REQ-PERF-synthesis-latency.md)
