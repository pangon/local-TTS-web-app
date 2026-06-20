# DEC-text-preprocessing-pipeline: Trail

> Companion to `DEC-text-preprocessing-pipeline.md`.
> AI agents read this only when evaluating whether the decision is still
> valid or when proposing a change or supersession.

## Alternatives considered

### Option A: Modular pipeline as a dedicated backend service (chosen)

- Pros: Each cleaning concern is independently testable; per-language and per-model configuration is isolated from shared logic (`REQ-MNT-preprocessing-pipeline`); keeps the TTS subpackage focused on GPU inference; the CPU-bound text work is cleanly separated from synthesis.
- Cons: Model-aware configuration becomes a cross-module concern (the service must read the currently loaded model from the Model Service) rather than living next to the model adapters.

### Option B: Preprocessing module inside the TTS subpackage

- Pros: Co-located with the Chapter Parser (also non-GPU text processing) and the model-adapter pattern, so model-aware config sits next to adapters; keeps the whole text→audio transformation in one subpackage.
- Cons: Mixes CPU-bound text cleaning into a subpackage whose stated responsibility is GPU inference and model management; the user preferred to keep the TTS subpackage strictly inference-focused.

### Option C: Single monolithic preprocessing function

- Pros: Simplest to write initially.
- Cons: Untestable at the stage level, hard to extend per language/model, violates `REQ-MNT-preprocessing-pipeline`. Rejected.

## Reasoning

The user chose to place the preprocessor as a separate backend module rather than inside the TTS subpackage, keeping the TTS subpackage strictly GPU/inference-focused. The modular staged structure with two-axis (language, model) configuration is mandated by `REQ-MNT-preprocessing-pipeline` and aligns with the modularity intent of `REQ-MNT-modular-ai-layer`. Stage ordering (sanitize → layout repair → verbalize → abbreviation expansion) puts character-level cleanup first so later regex/verbalization stages operate on clean, reflowed text; layout repair precedes chapter detection so sentences are whole while chapter boundaries are preserved.

This decision would be revisited if profiling shows the synchronous CPU pipeline cannot meet `REQ-PERF-preprocessing-overhead`, or if a future model requires preprocessing tightly coupled to its adapter (which might argue for moving model-specific stages closer to the adapter layer).

## Human involvement

**Type**: ai-proposed/human-approved

**Notes**: Placement (separate backend module vs. TTS subpackage) was presented as an explicit choice; the user selected the separate backend module. The staged structure, ordering, and configuration model were proposed by the AI and approved together with the rest of the design proposal.

## Changelog

| Date | Change | Involvement |
|------|--------|-------------|
| 2026-06-16 | Initial decision | ai-proposed/human-approved |
| 2026-06-19 | Clarified the language-axis policy: a requested output language with no registered data is **rejected** (API 400), not treated as a no-op. Surfaced during manual testing (runbook 5.1.8) — `language=en` produced no rewriting because only `it` data ships, which silently returned the raw text as "normalized" and misled the reviewer. The original no-op-for-unknown-language behavior (a code/runbook default, never mandated by this decision) is reversed; the domain-dictionary absence-tolerance is unaffected. Added a Required check and a Prohibited pattern. | human-decided |
| 2026-06-20 | Added a fifth stage, **sentence segmentation** (one sentence per line), running last. Surfaced during manual testing on a real book file: layout repair glued structural front-matter lines (title / lone chapter number / heading) into the body and collapsed the whole body onto one line. Fix had two parts: (a) layout repair now keeps bare-number lines standalone (like headings/list items), and (b) the new last stage segments sentences after numbers/abbreviations are expanded, so `11.988` / `E.F.` are not mis-split. Within REQ-F-text-layout-repair's "heuristics refined through testing"; no requirement change. | human-decided |
