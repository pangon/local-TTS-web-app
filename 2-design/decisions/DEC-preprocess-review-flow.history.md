# DEC-preprocess-review-flow: Trail

> Companion to `DEC-preprocess-review-flow.md`.
> AI agents read this only when evaluating whether the decision is still
> valid or when proposing a change or supersession.

## Alternatives considered

### Option A: Synchronous `/preprocess` + synthesis accepts confirmed text (chosen)

- Pros: Simplest API; guarantees synthesis uses exactly the reviewed text; naturally supports optional user editing of the normalized text; the pipeline runs once. The synchronous call fits `REQ-PERF-preprocessing-overhead` (≤10 s / ≤1 s) on a single-user localhost deployment.
- Cons: Changes the already-implemented `POST /jobs/synthesis` contract from multipart file upload to JSON text; requires reworking the audiobook-creation view to add the review step.

### Option B: Job state machine with a `pending_review` state

- Pros: Keeps `/jobs/synthesis` accepting a file upload; single job lifecycle.
- Cons: Adds job states (`preprocessing`, `pending_review`), extra endpoints (`GET /jobs/{id}/normalized-text`, `POST /jobs/{id}/confirm`), and requires persisting intermediate normalized text in the DB. More moving parts for a single-user app.

### Option C: Display-only `/preprocess`, synthesis re-runs preprocessing

- Pros: Smallest change to `/jobs/synthesis` (keeps file upload).
- Cons: Review is read-only (no editing); correctness relies on the pipeline being perfectly deterministic so the synthesized audio matches what was shown; runs the pipeline twice. Rejected as fragile.

## Reasoning

The user selected Option A. It most directly satisfies `REQ-USA-normalized-text-review`'s requirement that synthesis proceed "using exactly the reviewed text," keeps the server stateless with respect to normalized text, and avoids the extra job states and persistence of Option B. The cost — reworking the already-implemented `POST /jobs/synthesis` and the audiobook-creation view — is accepted; these downstream impacts are flagged for `/SDLC-implementation-plan`.

This decision would be revisited if synchronous preprocessing proved too slow to hold an HTTP request open within `REQ-PERF-preprocessing-overhead`, in which case a job-based (Option B) approach with SSE progress would be reconsidered.

## Human involvement

**Type**: ai-proposed/human-approved

**Notes**: The flow was presented as an explicit three-option choice; the user selected the synchronous `/preprocess` + text-synthesis option, then approved the full design proposal including the contract change to `POST /jobs/synthesis`.

## Changelog

| Date | Change | Involvement |
|------|--------|-------------|
| 2026-06-16 | Initial decision | ai-proposed/human-approved |
