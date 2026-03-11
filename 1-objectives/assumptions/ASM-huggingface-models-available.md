# ASM-huggingface-models-available: Suitable Open-Weight TTS Models Exist on HuggingFace

**Category**: Technology

**Status**: Verified

**Risk if wrong**: High — GOAL-huggingface-models depends entirely on this; without suitable models, the core TTS feature cannot function as designed.

## Statement

HuggingFace hosts open-weight TTS models that produce acceptable audio quality, fit within 4 GB VRAM, and can be loaded on-demand via standard tooling (e.g., transformers, huggingface_hub).

## Rationale

Several open-weight TTS models are currently available on HuggingFace, including Coqui XTTS, Bark, Piper, and others. The HuggingFace ecosystem provides standardized model hosting, versioning, and download APIs.

## Verification

Verified 2026-03-11 via HuggingFace model survey. Three viable candidates meet all criteria (open-weight, ≤ 4 GB VRAM, natural speech, Italian support):

| Model | License | VRAM (est.) | Italian | Loading |
|-------|---------|-------------|---------|---------|
| `suno/bark-small` | MIT | ~2 GB (FP16) | Yes — 10 Italian speaker presets (`v2/it_speaker_0`–`9`), 13 languages total | Native `transformers` (`BarkModel`) |
| `Qwen/Qwen3-TTS-12Hz-0.6B-Base` | Apache 2.0 | ~2.5–3.2 GB (bf16) | Yes — Italian WER=1.534, 10 languages | `qwen-tts` pip package (wraps `transformers`) |
| `ResembleAI/chatterbox` | MIT | ~3.2 GB (tight) | Yes — 23 languages | `chatterbox-tts` pip package |

**Note on voice/language metadata**: discoverability varies by model. Bark has discoverable speaker presets; Qwen3-TTS has language tags in model card metadata; Chatterbox uses a `language_id` parameter. The `GET /models/{id}/voices` API endpoint will likely need model-specific adapters — this is an implementation concern, not a blocker.

## Related Artifacts

- [GOAL-huggingface-models](../goals/GOAL-huggingface-models.md)
- [GOAL-audio-quality](../goals/GOAL-audio-quality.md)
- [ASM-user-has-nvidia-gpu](ASM-user-has-nvidia-gpu.md)
