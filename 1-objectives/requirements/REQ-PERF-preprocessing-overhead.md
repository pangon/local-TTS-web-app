# REQ-PERF-preprocessing-overhead: Bounded Text-Preprocessing Overhead

**Type**: Performance

**Status**: Approved

**Priority**: Should-have

**Source**: [US-clean-text-for-tts](../user-stories/US-clean-text-for-tts.md)

**Source stakeholder**: [STK-end-user](../stakeholders.md)

## Description

Text normalization runs before synthesis and must not materially erode the synthesis latency targets. The CPU-bound preprocessing pipeline shall complete within bounded time on min-spec hardware:

- Preprocessing a full uploaded document of up to ~2 MB shall complete in ≤ 10 s
- Preprocessing of a short preview input (≤ 500 characters) shall complete in ≤ 1 s, so it does not meaningfully consume the preview latency budget

These bounds complement, and must not cause regression of, the synthesis latency targets in [REQ-PERF-synthesis-latency](REQ-PERF-synthesis-latency.md) (preview ≤ 30 s for 500 chars; audiobook RTF ≤ 3.0).

## Acceptance Criteria

- Given a ~2 MB UTF-8 document, when the preprocessing pipeline runs on min-spec hardware, then it completes in ≤ 10 s
- Given a preview input of ≤ 500 characters, when it is preprocessed, then preprocessing adds ≤ 1 s before synthesis begins
- Given the end-to-end preview path (preprocessing + synthesis), when measured for 500 characters, then total time still meets the ≤ 30 s target in REQ-PERF-synthesis-latency

## Related Requirements

- [REQ-PERF-synthesis-latency](REQ-PERF-synthesis-latency.md) — synthesis latency targets this requirement must not regress
- [REQ-F-text-numeric-symbolic-verbalization](REQ-F-text-numeric-symbolic-verbalization.md), [REQ-F-text-unicode-sanitization](REQ-F-text-unicode-sanitization.md), [REQ-F-text-layout-repair](REQ-F-text-layout-repair.md), [REQ-F-abbreviation-expansion](REQ-F-abbreviation-expansion.md) — the cleaning stages whose combined cost this bounds
