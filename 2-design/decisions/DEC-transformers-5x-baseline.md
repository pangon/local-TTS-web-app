# DEC-transformers-5x-baseline: Backend Baseline on transformers 5.x (drop qwen-tts / Qwen3-TTS adapter)

**Status**: Active

**Category**: Architecture

**Scope**: backend

**Source**: [REQ-F-synthesize-audiobook](../../1-objectives/requirements/REQ-F-synthesize-audiobook.md), [REQ-MNT-modular-ai-layer](../../1-objectives/requirements/REQ-MNT-modular-ai-layer.md)

**Last updated**: 2026-06-20

## Context

The backend originally pinned `transformers>=4.38` (installed 4.57.3). Two priority Phase 5.2 model adapters require **transformers 5.x**:

- **MOSS-TTSD v1.0** (`OpenMOSS-Team/MOSS-TTSD-v1.0`): its `trust_remote_code` model code imports `from transformers import initialization` (a module new in 5.x) and its companion audio tokenizer (`OpenMOSS-Team/MOSS-Audio-Tokenizer`, loaded via `codec_path`) imports `PreTrainedConfig` (the 5.x rename of `PretrainedConfig`). On 4.57.3 loading fails with `cannot import name 'PreTrainedConfig'`. Every codec revision uses the 5.x name, so pinning an older codec revision cannot help.
- **Higgs Audio v3** (`bosonai/higgs-audio-v3-tts-4b`, a later Phase 5.2 task): custom architecture native in **transformers>=5.5**.

The `qwen-tts` package (the Qwen3-TTS adapter's dependency) hard-pins `transformers==4.57.3`, and `0.1.1` is its latest release — there is no 5.x-compatible version. So the backend cannot host both the transformers-5.x models and `qwen-tts` in one environment. The user chose (2026-06-20) to move the backend baseline to transformers 5.x and drop the Qwen3-TTS adapter rather than forgo MOSS-TTSD / Higgs v3.

## Decision

The backend baseline is **`transformers>=5.5`** (covers MOSS-TTSD ≥5.0 and Higgs Audio v3 ≥5.5). Consequences:

- **`qwen-tts` is removed** from the runtime dependencies, and the **Qwen3-TTS adapter is unregistered** (`Qwen3TTSAdapter` removed from `_ADAPTER_REGISTRY`, so `loader_available=false` for `Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice`). The adapter module (`tts/adapters/qwen3_tts.py`) and its tests are **kept** so it can be re-registered if a transformers-5.x-compatible `qwen-tts` is released.
- The `Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice` entry stays in `COMPATIBLE_MODELS` (it remains a valid, FOSS catalog model); it simply lists with no available adapter.
- `transformers` 5.x requires `huggingface-hub` 1.x; the project's `huggingface_hub` usage (`scan_cache_dir`, `snapshot_download`, `model_info`, `HF_HUB_CACHE`) is compatible (verified by the test suite).

Remote-code adapters built on transformers must follow the `trust_remote_code` hardening recorded in the backend component doc: prefer pinning the model repo `revision` (except where the loader forwards `revision` into a different-repo sub-component — MOSS-TTSD propagates it to its companion codec, so it loads at HEAD), and bridge any renamed transformers symbols defensively (e.g. MOSS-TTSD's `_install_transformers_compat`, a no-op on 5.x).

## Enforcement

### Trigger conditions

- **Design phase**: when adding a model to the architecture Compatibility Table or choosing a model-loading library/approach (it must be compatible with the transformers 5.x baseline).
- **Code phase**: when adding/upgrading a backend dependency that constrains `transformers`; when adding a model adapter (pick libraries compatible with transformers 5.x); when changing the adapter registry.

### Required patterns

- `pyproject.toml` keeps `transformers>=5.5`. New TTS-model packages must be compatible with transformers 5.x (no hard pin to a 4.x release).
- A model package that conflicts with the transformers-5.x baseline is not added as a runtime dependency; if its adapter exists it is left **unregistered** with a code comment explaining the conflict.

### Required checks

1. After changing dependencies, run `pip install -e ".[dev]"` and the full backend test suite; confirm all adapters' tests pass on transformers 5.x.
2. A newly added TTS package does not re-pin `transformers` below 5.5.

### Prohibited patterns

- Re-adding `qwen-tts` (or any package that pins `transformers==4.57.3` / `<5`) to the runtime dependencies while the 5.x baseline stands.
- Registering an adapter whose package is incompatible with transformers 5.x.
- Downgrading `transformers` below 5.5 (would break MOSS-TTSD and Higgs v3).
