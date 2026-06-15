# DEC-preprocess-review-flow: Synchronous Preprocess-then-Confirm Synthesis Flow

**Status**: Active

**Category**: Architecture

**Scope**: backend, frontend

**Source**: [REQ-USA-normalized-text-review](../../1-objectives/requirements/REQ-USA-normalized-text-review.md), [REQ-PERF-preprocessing-overhead](../../1-objectives/requirements/REQ-PERF-preprocessing-overhead.md)

**Last updated**: 2026-06-16

## Context

Before committing GPU time to synthesis, the user must be able to review the exact normalized text that will be read aloud and explicitly confirm it (`REQ-USA-normalized-text-review`) — catching cases where automatic cleaning altered the text undesirably (e.g. over-aggressive reflow). The original flow (`POST /jobs/synthesis` uploads a `.txt` file and synthesizes immediately) has no review step. A flow is needed that (a) shows normalized text before generation, (b) guarantees synthesis uses *exactly* the reviewed text, and (c) respects the preprocessing latency bounds (`REQ-PERF-preprocessing-overhead`).

## Decision

Use a **two-step, synchronous flow** where preprocessing and synthesis are separate calls and the normalized text round-trips through the client:

1. **`POST /api/v1/preprocess`** runs the pipeline synchronously and returns the normalized text (within `REQ-PERF-preprocessing-overhead` bounds: ≤10 s for ~2 MB, ≤1 s for ≤500-char preview). It accepts either an uploaded `.txt` file (audiobook path) or raw `text` (preview path), plus an optional output `language`, and uses the currently loaded model for the model profile.
2. The frontend presents the normalized text for **review and explicit confirmation** (the user may proceed directly; review is a confirmation step, not a mandatory edit). For the quick text-preview path the review is satisfied inline, since the input text is already visible.
3. **`POST /api/v1/jobs/synthesis`** accepts the confirmed text as JSON (`text`, `source_filename`, optional `voice`/`language`) and synthesizes **exactly** that text — it does **not** re-run preprocessing. **`POST /api/v1/jobs/preview`** likewise synthesizes exactly the (already-normalized) `text` it receives.

Because the upload now happens at `/preprocess`, the `.txt` upload requirement (`REQ-F-upload-text-file`) is satisfied at `/preprocess`; `/jobs/synthesis` no longer accepts a file.

The normalized text is **transient**: it is not persisted server-side. The client holds it between the preprocess and synthesis calls.

## Enforcement

### Trigger conditions

- **Design phase**: when modifying the preprocess/synthesis API contracts or the review flow.
- **Code phase**: when implementing the `/preprocess` endpoint, the `/jobs/synthesis` and `/jobs/preview` request handling, or the frontend audiobook-creation / text-preview review UI.

### Required patterns

- `POST /preprocess` is synchronous and returns the normalized text in the response body.
- `POST /jobs/synthesis` and `POST /jobs/preview` synthesize exactly the `text` provided in the request, without re-running the preprocessing pipeline.
- The frontend audiobook-creation flow shows the normalized text and requires an explicit user action before calling `/jobs/synthesis`.
- The text-preview flow may satisfy review inline (no separate confirmation screen).

### Required checks

1. Verify the text synthesized equals the text returned by `/preprocess` and confirmed by the user (no second normalization pass).
2. Verify synthesis cannot be triggered for the audiobook path without an explicit confirmation action.
3. Verify `/preprocess` meets the latency bounds in `REQ-PERF-preprocessing-overhead` on min-spec hardware.

### Prohibited patterns

- Re-running the preprocessing pipeline inside `/jobs/synthesis` or `/jobs/preview` (would risk diverging from the reviewed text).
- Persisting normalized text server-side as a stored entity.
- Auto-starting audiobook synthesis without a review/confirm step.
