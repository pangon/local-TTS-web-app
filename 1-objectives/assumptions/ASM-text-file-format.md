# ASM-text-file-format: Text File Format and Size

**Category**: User

**Status**: Unverified

**Risk if wrong**: Medium — wrong encoding produces garbled text in the audiobook; excessively large files could exhaust memory or make synthesis take unreasonably long

## Statement

Users upload UTF-8 encoded `.txt` files of reasonable size (up to ~2 MB). The system does not need to handle binary formats, other encodings, or extremely large documents.

## Rationale

UTF-8 is the dominant text encoding. A 2 MB plain text file covers most novels and long documents. Larger inputs are unlikely for a single-user local TTS application.

## Verification Plan

During implementation, test with UTF-8 files of varying sizes (small paragraph, medium chapter, full novel ~2 MB). Confirm the TTS pipeline handles the upper bound within acceptable time and memory on a 4 GB VRAM GPU.

## Related Artifacts

- [GOAL-audiobook-creation](../goals/GOAL-audiobook-creation.md), [US-create-audiobook](../user-stories/US-create-audiobook.md)
