# DEC-voice-clone-prompts: Trail

> Companion to `DEC-voice-clone-prompts.md`.
> AI agents read this only when evaluating whether the decision is still
> valid or when proposing a change or supersession.

## Alternatives considered

### Option A: Precomputed prompt artifacts generated offline (chosen)
- Pros: clone-prompt build (model run + transcript) happens once, offline; request path stays fast; artifact is reusable; matches the `qwen-tts` Base workflow (`create_voice_clone_prompt` → `generate_voice_clone`); keeps the manual cloning operation out of the product surface (no API/UI).
- Cons: requires a manual operator step (run a script) before the Base model is usable; artifacts are model-specific and not portable.

### Option B: Runtime cloning from a raw clip on every request (the DEFAULT_VOICE_PATH pattern)
- Pros: zero extra artifacts; reuses the existing `wavs/default.mp3` stopgap; one mechanism for all cloning adapters.
- Cons: for Qwen3-Base, no transcript is available for `wavs/default.mp3`, forcing x-vector-only mode (degraded quality vs ICL with a transcript); recomputes the prompt every synthesis; does not match the intended Base workflow.

### Option C: Fall back from a missing precomputed prompt to runtime clip cloning
- Pros: zero-config — the Base model works even before the script is run.
- Cons: a second code path and a silently degraded voice; the user chose an explicit clear error instead (mirrors CosyVoice 3 requiring a clip).

## Reasoning

The Qwen3-TTS Base model is built around a precomputed clone prompt, and the user explicitly wants the cloning done offline (mp3 + transcript → a stored voice under `wavs/qwen3-tts/`) and kept out of the product. Option A matches both the API and the desired separation of concerns. A missing-prompt fallback (Option C) was considered and declined in favor of a clear error, keeping the default-voice behavior predictable and high quality. The mechanism is written generically ("for some models") so future precomputed-prompt models reuse it, but currently only Qwen3-Base does.

Conditions that would invalidate this reasoning: Phase 6 voice selection lands (the default-prompt stopgap is then superseded by per-request selection); or a future model makes runtime clip cloning equivalent in quality and cheap enough to drop the offline step.

## Human involvement

**Type**: ai-proposed/human-approved

**Notes**: User directed the feature (Qwen3-TTS-12Hz-1.7B-Base with an offline-cloned default voice under `wavs/qwen3-tts/`, cloning done by a manual backend script from an mp3 + transcript, not integrated into the product). User chose, when asked, that a missing prompt should raise a clear error rather than fall back to `wavs/default.mp3`.

## Changelog

| Date | Change | Involvement |
|------|--------|-------------|
| 2026-06-21 | Initial decision | ai-proposed/human-approved |
