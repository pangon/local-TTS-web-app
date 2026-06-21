# DEC-transformers-5x-baseline: Backend Baseline on transformers 5.x (drop qwen-tts / Qwen3-TTS adapter)

**Status**: Active

**Category**: Architecture

**Scope**: backend

**Source**: [REQ-F-synthesize-audiobook](../../1-objectives/requirements/REQ-F-synthesize-audiobook.md), [REQ-MNT-modular-ai-layer](../../1-objectives/requirements/REQ-MNT-modular-ai-layer.md)

**Last updated**: 2026-06-21

> **Exploratory baseline (2026-06-21):** the baseline is currently **in flux** — see the *Exploratory baseline* subsection under **Decision**. Fish Audio S2-Pro needs `transformers<=4.57.3`, the inverse of MOSS-TTSD/Higgs v3 (`>=5.0`/`>=5.5`), and one environment cannot host both. The user chose (2026-06-21) to widen the pin and flip the installed `transformers` per the model under exploration, to be re-fixed to a single stable baseline later.

## Context

The backend originally pinned `transformers>=4.38` (installed 4.57.3). Two priority Phase 5.2 model adapters require **transformers 5.x**:

- **MOSS-TTSD v1.0** (`OpenMOSS-Team/MOSS-TTSD-v1.0`): its `trust_remote_code` model code imports `from transformers import initialization` (a module new in 5.x) and its companion audio tokenizer (`OpenMOSS-Team/MOSS-Audio-Tokenizer`, loaded via `codec_path`) imports `PreTrainedConfig` (the 5.x rename of `PretrainedConfig`). On 4.57.3 loading fails with `cannot import name 'PreTrainedConfig'`. Every codec revision uses the 5.x name, so pinning an older codec revision cannot help.
- **Higgs Audio v3** (`bosonai/higgs-audio-v3-tts-4b`, a later Phase 5.2 task): custom architecture native in **transformers>=5.5**.

The `qwen-tts` package (the Qwen3-TTS adapter's dependency) hard-pins `transformers==4.57.3`, and `0.1.1` is its latest release — there is no 5.x-compatible version. So the backend cannot host both the transformers-5.x models and `qwen-tts` in one environment. The user chose (2026-06-20) to move the backend baseline to transformers 5.x and drop the Qwen3-TTS adapter rather than forgo MOSS-TTSD / Higgs v3.

**Update (2026-06-21) — the inverse conflict surfaced.** Fish Audio S2-Pro (`fishaudio/s2-pro`, `TASK-loader-fish-s2-pro`) loads only via the **GitHub-only** `fish-speech` v2.0.0 package (PyPI carries only a stale `0.1.0` placeholder), which **hard-pins `transformers<=4.57.3` and `torch==2.8.0`** — the exact opposite of MOSS-TTSD/Higgs v3 (`transformers>=5.0`/`>=5.5`). A single environment cannot satisfy both. The user is in an **exploratory phase** and chose to flip the baseline per the model being tried (rather than isolate environments or defer S2-Pro), to be re-stabilized later.

## Decision

The backend baseline is **`transformers>=5.5`** (covers MOSS-TTSD ≥5.0 and Higgs Audio v3 ≥5.5). Consequences:

- **`qwen-tts` is removed** from the runtime dependencies, and the **Qwen3-TTS adapter is unregistered** (`Qwen3TTSAdapter` removed from `_ADAPTER_REGISTRY`, so `loader_available=false` for `Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice`). The adapter module (`tts/adapters/qwen3_tts.py`) and its tests are **kept** so it can be re-registered if a transformers-5.x-compatible `qwen-tts` is released.
- The `Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice` entry stays in `COMPATIBLE_MODELS` (it remains a valid, FOSS catalog model); it simply lists with no available adapter.
- `transformers` 5.x requires `huggingface-hub` 1.x; the project's `huggingface_hub` usage (`scan_cache_dir`, `snapshot_download`, `model_info`, `HF_HUB_CACHE`) is compatible (verified by the test suite).

Remote-code adapters built on transformers must follow the `trust_remote_code` hardening recorded in the backend component doc: prefer pinning the model repo `revision` (except where the loader forwards `revision` into a different-repo sub-component — MOSS-TTSD propagates it to its companion codec, so it loads at HEAD), and bridge any renamed transformers symbols defensively (e.g. MOSS-TTSD's `_install_transformers_compat`, a no-op on 5.x).

### Exploratory baseline (2026-06-21)

Because Fish Audio S2-Pro requires `transformers<=4.57.3` (and `torch==2.8.0`) — the inverse of MOSS-TTSD/Higgs v3 — and one environment cannot host both, the baseline is **temporarily exploratory** during Phase 5.2 model trials:

- **`pyproject.toml` widens the pin to `transformers>=4.38`** (no upper bound) so the operator can install whichever major the model under exploration needs. A fresh `pip install` resolves to the latest 5.x (which keeps MOSS-TTSD/Higgs/VoxCPM2/Kokoro runnable); the operator manually downgrades to `4.57.3` when exercising Fish S2-Pro.
- **Currently installed: `transformers==4.57.3` + `huggingface-hub==0.36.2`** (downgraded 2026-06-21 to be fish-speech-compatible). The full backend suite (766 tests) passes on both 4.57.3 and 5.12.1; `torch` stays at 2.10.0 (fish-speech itself is **not** installed here — see below).
- **Runtime trade-off:** under a 4.x install, **MOSS-TTSD v1.0 and Higgs Audio v3 cannot load at runtime** (they need ≥5.0/≥5.5). Their adapters remain *registered* (`loader_available=true`) because the adapter modules import fine and their unit tests are mocked — the incompatibility is a documented runtime consequence of the exploratory baseline, not an install conflict, and it reverses when the install returns to 5.x. (Contrast Qwen3-TTS, which is *unregistered* because its `qwen-tts` package cannot even be co-installed.)
- **fish-speech is a GPU-host dependency, not a backend runtime dependency:** it is GitHub-only, pins `torch==2.8.0` (conflicts with this repo's `torch>=2.10` and VoxCPM2's `torchcodec`), and needs 12–24 GB VRAM. The Fish S2-Pro adapter lazy-imports it (raising a clear install hint), unit tests mock it, and full-weight runtime validation is a GPU-host step (the MOSS-TTSD precedent). On the GPU host, install it in a **dedicated environment** (`git clone … fish-speech && pip install -e .`).
- This state is to be **re-fixed to a single stable baseline later** (user choice). When it is, this subsection and the `pyproject` pin should be reconciled.

## Enforcement

### Trigger conditions

- **Design phase**: when adding a model to the architecture Compatibility Table or choosing a model-loading library/approach (it must be compatible with the transformers 5.x baseline).
- **Code phase**: when adding/upgrading a backend dependency that constrains `transformers`; when adding a model adapter (pick libraries compatible with transformers 5.x); when changing the adapter registry.

### Required patterns

- While the baseline is exploratory (2026-06-21), `pyproject.toml` keeps the widened pin `transformers>=4.38` and the operator installs the major required by the model under exploration. (When re-stabilized, restore a single bound such as `transformers>=5.5`.)
- A package whose dependency pins **cannot be co-installed** with the rest of the runtime stack (e.g. `qwen-tts` pinning `transformers==4.57.3`; `fish-speech` pinning `torch==2.8.0`) is **not** added as a backend runtime dependency. Its adapter may still be **registered** if it lazy-imports the package and the package is a GPU-host dependency (Fish S2-Pro); it is **unregistered** only when its mere presence would break the shared environment (Qwen3-TTS). Either way, add a code comment explaining the conflict.

### Required checks

1. After changing dependencies, run `pip install -e ".[dev]"` and the full backend test suite; confirm all adapters' tests pass on transformers 5.x.
2. A newly added TTS package does not re-pin `transformers` below 5.5.

### Prohibited patterns

- Adding any package that **hard-pins** `transformers` (e.g. `qwen-tts` → `==4.57.3`) or `torch` (e.g. `fish-speech` → `==2.8.0`) as a backend **runtime** dependency — it would force-downgrade the shared stack. Such packages stay GPU-host-only and are lazy-imported.
- Silently editing `REQ-COMP-foss-only` or the objectives to accommodate a model.
- (While exploratory) leaving the installed `transformers` mismatched with the model actually being tested without noting it — record the current installed major in this decision's *Exploratory baseline* subsection. Once re-stabilized, downgrading below the chosen stable floor again becomes prohibited.
