# DEC-text-preprocessing-pipeline: Modular Backend Text-Preprocessing Pipeline

**Status**: Active

**Category**: Architecture

**Scope**: backend

**Source**: [REQ-MNT-preprocessing-pipeline](../../1-objectives/requirements/REQ-MNT-preprocessing-pipeline.md), [GOAL-text-normalization](../../1-objectives/goals/GOAL-text-normalization.md), [REQ-F-text-unicode-sanitization](../../1-objectives/requirements/REQ-F-text-unicode-sanitization.md), [REQ-F-text-layout-repair](../../1-objectives/requirements/REQ-F-text-layout-repair.md), [REQ-F-text-numeric-symbolic-verbalization](../../1-objectives/requirements/REQ-F-text-numeric-symbolic-verbalization.md), [REQ-F-abbreviation-expansion](../../1-objectives/requirements/REQ-F-abbreviation-expansion.md)

**Last updated**: 2026-06-19

## Context

Testing revealed that real-world inputs — especially PDF-to-text extractions — require substantial cleaning before synthesis (`ASM-input-text-quality-varies`). The text-normalization capability spans four distinct cleaning concerns (Unicode sanitization, layout repair, numeric/symbolic verbalization, abbreviation expansion) that are language-dependent and must adapt to different TTS models' input expectations. Implementing this as a single monolithic function would be untestable, hard to extend per language/model, and would entangle cleaning logic with synthesis. The pipeline is CPU-bound text transformation, not GPU inference.

## Decision

Implement text preprocessing as a **dedicated backend application service** (the Preprocessing Service), a sibling to the Library/Job/Model/Monitor services — **not** inside the TTS subpackage, which stays focused on GPU inference and model management.

The service runs a **modular pipeline of discrete, independently unit-testable stages**, executed in this default order (order is config-driven and refined through testing):

1. **Unicode sanitization** — remove invisible/control characters; convert NBSP and whitespace variants to normal spaces; normalize dash and quote variants; remove disallowed Unicode; emoji removed or verbalized per config (`REQ-F-text-unicode-sanitization`).
2. **Layout repair** — resolve end-of-line hyphenation; reflow sentences split across hard line breaks; strip isolated page numbers and standalone layout fragments; normalize irregular whitespace; **preserve genuine paragraph and chapter boundaries** so chapter detection (`REQ-F-chapter-split-output`) still functions (`REQ-F-text-layout-repair`).
3. **Numeric & symbolic verbalization** — spell out cardinals/ordinals, dates, percentages, currency, and common symbols, language-aware (`REQ-F-text-numeric-symbolic-verbalization`).
4. **Abbreviation expansion** — verbalize common abbreviations/acronyms from a language-specific built-in set; apply an optional domain dictionary when supplied (`REQ-F-abbreviation-expansion`).

The pipeline is configurable along two axes (`REQ-MNT-preprocessing-pipeline`):

- **Language profile** (keyed by language code; default `it` per `DEC-default-italian-language`): verbalization rule tables and the built-in abbreviation set. A requested output language that has no registered data is **rejected** rather than degrading to a no-op: because the rewrites are language-specific, an unregistered language would silently return the raw text as if it had been normalized, misleading the user reviewing it (`REQ-USA-normalized-text-review`). The empty/omitted language still falls back to the supported default. (This rejection policy is specific to the **language** axis; the optional domain dictionary keeps its absence-tolerant behavior — see below.)
- **Model profile** (keyed by `model_id`, with a default fallback): which stages run and their parameters, accommodating differing model input expectations without modifying shared stage logic. The service reads the currently loaded model (via the Model Service) to select the model profile.
- **Optional domain dictionary**: a file on disk (e.g. `config/preprocessing/domain_dictionary.json`) mapping acronyms/technical terms to spoken forms; applied when present, built-in defaults otherwise. Delivery mechanism refinable.

Layout repair runs **before** chapter detection (which remains in the Job Service → Chapter Parser path), so reflow operates on the full document while chapter boundaries are preserved.

## Enforcement

### Trigger conditions

- **Design phase**: when modifying the preprocessing pipeline structure, its stages, or its configuration model.
- **Code phase**: when implementing or modifying the Preprocessing Service, any pipeline stage, or stage configuration.

### Required patterns

- Each cleaning concern is a separate stage object/function that can be unit-tested in isolation, given input text and a resolved configuration.
- Language-specific behavior is selected via a language profile keyed by language code; model-specific behavior via a model profile keyed by `model_id` with a default fallback.
- Adding a new language or model is done by adding a profile/stage, not by editing existing shared stage logic.
- The optional domain dictionary is loaded only if present; absence must not break preprocessing.

### Required checks

1. Verify stages are independently unit-testable (each has tests exercising it in isolation).
2. Verify that for a configured output language the language-appropriate stages/rules are selected, and that an output language with no registered data is rejected with a clear error (surfaced by the API as a 400) rather than silently producing an unchanged "normalized" text.
3. Verify two different models can apply different model profiles without changing shared stage code.
4. Verify layout repair preserves paragraph/chapter boundaries and does not defeat chapter detection.

### Prohibited patterns

- A single monolithic preprocessing function combining all cleaning concerns.
- Placing the preprocessing pipeline inside the TTS subpackage (it is GPU-inference-only).
- Hardcoding language- or model-specific rules into shared stage logic.
- Silently treating an unregistered output language as a no-op (returning the raw text unchanged); it must be rejected so the reviewed text is never a passthrough masquerading as normalized output.
