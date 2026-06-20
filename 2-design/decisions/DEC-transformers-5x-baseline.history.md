# DEC-transformers-5x-baseline: Trail

> Companion to `DEC-transformers-5x-baseline.md`.
> AI agents read this only when evaluating whether the decision is still
> valid or when proposing a change or supersession.

## Alternatives considered

### Option A: Upgrade the backend to transformers 5.x; drop qwen-tts / Qwen3-TTS (chosen)
- Pros: enables MOSS-TTSD v1.0 now and Higgs Audio v3 (≥5.5) later — both priority Phase 5.2 models; tracks the models' actual intended runtime; one consistent, current transformers across the backend.
- Cons: drops the Qwen3-TTS adapter (qwen-tts has no 5.x-compatible release); requires re-validating Kokoro and VoxCPM2 on transformers 5.x (full GPU validation is a host step); pulls `huggingface-hub` to 1.x.

### Option B: Stay on transformers 4.57.3; defer MOSS-TTSD (and Higgs v3)
- Pros: lowest risk; keeps Qwen3/Kokoro/VoxCPM2 working unchanged; no environment churn.
- Cons: MOSS-TTSD and Higgs v3 cannot be offered at all; the Phase 5.2 goal of enabling these models would be unmet.

### Option C: Force MOSS-TTSD onto transformers 4.x via shims
- Pros: no transformers upgrade; keeps qwen-tts.
- Cons: fragile — would require faking the whole `transformers.initialization` module plus the `PreTrainedConfig` alias, and likely more hidden 5.x APIs in the model code; weight-init behavior could differ; high maintenance and correctness risk. Rejected.

## Reasoning

The conflict is structural and unavoidable in a single environment: MOSS-TTSD v1.0 needs transformers ≥5.0 (its remote code imports the 5.x `transformers.initialization` module and `PreTrainedConfig`), while `qwen-tts` 0.1.1 (latest) hard-pins `transformers==4.57.3`. The user prioritized the two new transformers-5.x models (MOSS-TTSD, Higgs v3) over the Qwen3-TTS adapter. Empirically, after upgrading to transformers 5.12.1 + huggingface-hub 1.20.1 and unregistering Qwen3, the full backend suite (730 tests) passes with no other code changes — Kokoro and VoxCPM2 adapter tests (which mock their packages) and all HF-Hub usage remained compatible — so the migration's blast radius on our code is limited to the Qwen3 registry test. Full-weight runtime validation of Kokoro/VoxCPM2/MOSS-TTSD on 5.x remains a GPU-host step. The Qwen3 adapter module is retained (unregistered) so it can be restored cheaply if a 5.x-compatible `qwen-tts` ships.

## Human involvement

**Type**: ai-proposed/human-approved

**Notes**: Surfaced during a user-reported MOSS-TTSD load failure (`cannot import name 'PreTrainedConfig'`). The agent diagnosed the transformers-version conflict and presented three options; the user selected "Upgrade to transformers 5.x" (2026-06-20).

## Changelog

| Date | Change | Involvement |
|------|--------|-------------|
| 2026-06-20 | Initial decision: move backend baseline to transformers>=5.5; drop qwen-tts and unregister the Qwen3-TTS adapter | ai-proposed/human-approved |
