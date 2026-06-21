# DEC-voice-clone-prompts: Precomputed Offline Voice-Clone Prompts for Cloning Adapters

**Status**: Active

**Category**: Architecture

**Scope**: backend

**Source**: [REQ-F-synthesize-audiobook](../../1-objectives/requirements/REQ-F-synthesize-audiobook.md), [REQ-F-voice-language-selection](../../1-objectives/requirements/REQ-F-voice-language-selection.md)

**Last updated**: 2026-06-21

## Context

Some TTS models clone a target voice not from a raw reference clip at synthesis time but from a **precomputed prompt artifact** that the model itself produces from a reference clip plus its transcript. The driving case is `Qwen/Qwen3-TTS-12Hz-1.7B-Base`: its `qwen-tts` API exposes `create_voice_clone_prompt(ref_audio, ref_text) -> list[VoiceClonePromptItem]` (speaker embedding + reference codes as torch tensors), which is then passed to `generate_voice_clone(text, language, voice_clone_prompt=…)`. Building this prompt requires running the model and a transcript, so it is wasteful to recompute on every synthesis and awkward to do inside the request path.

This differs from the existing raw-clip stopgap (`config.DEFAULT_VOICE_PATH` → `wavs/default.mp3`), where adapters that clone at runtime (CosyVoice 3, F5-TTS) are handed a clip path and do the cloning themselves each call. Precomputed-prompt models instead need a model-specific artifact prepared **ahead of time**.

Voice selection through the product UI is deferred to Phase 6 (`TASK-voice-language-selection-ui`), so until then a cloning adapter needs a **default** voice to use.

## Decision

Support **precomputed voice-clone prompts** as an opt-in capability of cloning adapters, currently used only by the Qwen3-TTS Base adapter:

1. **Offline generation.** A standalone backend **script** (not part of the product runtime and **not** exposed via any API or the frontend) takes an `.mp3` (or other audio) plus its transcript, runs the model's clone-prompt builder, and serializes the result to disk with `torch.save`. The script is a manual operator tool run on the GPU host.
2. **On-disk storage layout.** Prompt artifacts live under a **per-model-family subfolder** of the repo-root `wavs/` directory — e.g. `wavs/qwen3-tts/<voice-name>.pt`. Artifacts are model-specific and **not** portable across models. The `wavs/` tree is gitignored (user-provided assets).
3. **Adapter consumption.** A cloning adapter loads the configured **default** prompt artifact (a path from `config`, e.g. `LOCAL_TTS_QWEN3_TTS_DEFAULT_VOICE_PROMPT` → `wavs/qwen3-tts/default.pt`) at synthesis time and passes the deserialized prompt to the model. The path is read at call time.
4. **No silent fallback.** If the configured prompt artifact is absent, the adapter raises a **clear error** instructing the operator to run the cloning script — it does **not** fall back to raw-clip cloning or to a built-in speaker. This mirrors CosyVoice 3 requiring a reference clip.
5. **Phase 6 supersession.** Per-request voice selection (Phase 6) will let the user choose among the prepared prompts in the model-family folder; the default-prompt mechanism is the stopgap until then.

## Enforcement

### Trigger conditions

- **Design phase**: when adding a model that clones from a precomputed prompt, or changing the prompt storage layout / offline-generation approach.
- **Code phase**: when implementing the offline cloning script, a precomputed-prompt cloning adapter, or the related `config` paths.

### Required patterns

- The clone-prompt builder runs **only** in the offline script, never in the request/synthesis path.
- Prompt artifacts are stored under `wavs/<model-family>/` and are model-specific.
- The adapter resolves the default prompt path from `config` (env-overridable) and reads it at call time.
- An absent prompt artifact raises a clear, actionable error.

### Required checks

1. Verify the offline script is not imported by, or reachable from, the FastAPI app / API layer.
2. Verify the adapter raises a clear error (not a deep model traceback) when the prompt file is missing.
3. Verify prompt artifacts are gitignored (under `wavs/`).

### Prohibited patterns

- Calling the model's clone-prompt builder inside `synthesize()` or any request handler.
- Exposing the cloning operation via an API endpoint or the frontend (it is a manual backend operation).
- Silently substituting a different voice when the configured prompt is missing.
- Committing prompt artifacts or reference clips to the repository.
