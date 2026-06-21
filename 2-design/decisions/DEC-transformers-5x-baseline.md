# DEC-transformers-5x-baseline: Backend transformers baseline (exploratory: MOSS-TTSD needs ≥5.x; Qwen3-TTS / Fish S2-Pro need 4.57.3)

**Status**: Active

**Category**: Architecture

**Scope**: backend

**Source**: [REQ-F-synthesize-audiobook](../../1-objectives/requirements/REQ-F-synthesize-audiobook.md), [REQ-MNT-modular-ai-layer](../../1-objectives/requirements/REQ-MNT-modular-ai-layer.md)

**Last updated**: 2026-06-21

> **Exploratory baseline (2026-06-21):** the baseline is currently **in flux** — see the *Exploratory baseline* subsection under **Decision**. **Qwen3-TTS** (`qwen-tts` needs `transformers==4.57.3`) and Fish Audio S2-Pro (`<=4.57.3`) are the inverse of MOSS-TTSD/Higgs v3 (`>=5.0`/`>=5.5`), and one environment cannot host both. The user chose (2026-06-21) to widen the pin and flip the installed `transformers` per the model under exploration — **currently installed at `4.57.3` to support Qwen3-TTS** (with the Qwen3-TTS adapter re-registered) — to be re-fixed to a single stable baseline later.

## Context

The backend originally pinned `transformers>=4.38` (installed 4.57.3). Two priority Phase 5.2 model adapters require **transformers 5.x**:

- **MOSS-TTSD v1.0** (`OpenMOSS-Team/MOSS-TTSD-v1.0`): its `trust_remote_code` model code imports `from transformers import initialization` (a module new in 5.x) and its companion audio tokenizer (`OpenMOSS-Team/MOSS-Audio-Tokenizer`, loaded via `codec_path`) imports `PreTrainedConfig` (the 5.x rename of `PretrainedConfig`). On 4.57.3 loading fails with `cannot import name 'PreTrainedConfig'`. Every codec revision uses the 5.x name, so pinning an older codec revision cannot help.
- **Higgs Audio v3** (`bosonai/higgs-audio-v3-tts-4b`, a later Phase 5.2 task): was *expected* to be a custom architecture native in **transformers>=5.5**. **Correction (2026-06-21):** this proved false on attempting to load it — `higgs_multimodal_qwen3` is **not in transformers** (released 5.12.1 or `main`) and the repo ships no remote code; Boson publishes v3 **server-only** (vLLM-Omni / SGLang-Omni). It therefore has **no in-process loader** and does **not** drive the transformers version at all (its adapter is unregistered, `TASK-loader-higgs-audio-v3`). **MOSS-TTSD v1.0 (≥5.0) is the binding driver** of the 5.x baseline; if MOSS-TTSD were ever dropped, the ≥5.x requirement would disappear and the baseline could collapse back toward Fish S2-Pro's `<=4.57.3`.

The `qwen-tts` package (the Qwen3-TTS adapter's dependency) hard-pins `transformers==4.57.3`, and `0.1.1` is its latest release — there is no 5.x-compatible version. So the backend cannot host both the transformers-5.x models and `qwen-tts` in one environment. The user chose (2026-06-20) to move the backend baseline to transformers 5.x and drop the Qwen3-TTS adapter rather than forgo MOSS-TTSD / Higgs v3.

**Update (2026-06-21) — the inverse conflict surfaced.** Fish Audio S2-Pro (`fishaudio/s2-pro`, `TASK-loader-fish-s2-pro`) loads only via the **GitHub-only** `fish-speech` v2.0.0 package (PyPI carries only a stale `0.1.0` placeholder), which **hard-pins `transformers<=4.57.3` and `torch==2.8.0`** — the exact opposite of MOSS-TTSD/Higgs v3 (`transformers>=5.0`/`>=5.5`). A single environment cannot satisfy both. The user is in an **exploratory phase** and chose to flip the baseline per the model being tried (rather than isolate environments or defer S2-Pro), to be re-stabilized later.

## Decision

The backend baseline is **`transformers>=5.5`** (driven by MOSS-TTSD ≥5.0; the originally-cited Higgs Audio v3 ≥5.5 no longer applies — see the Context correction: v3 is server-only and not a transformers model). Consequences:

- **`qwen-tts` is removed** from the runtime dependencies (it hard-pins `transformers==4.57.3`, so it must not drive a fresh `pip install -e .`). _(Superseded 2026-06-21 re the adapter: see the **Exploratory baseline** subsection — the Qwen3-TTS adapter is **re-registered**. `qwen-tts` is still not a runtime dependency; it is a GPU-host dependency installed when the baseline is at the 4.57.3 it requires.)_
- The `Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice` entry stays in `COMPATIBLE_MODELS` (a valid, FOSS catalog model).
- `transformers` 5.x requires `huggingface-hub` 1.x; the project's `huggingface_hub` usage (`scan_cache_dir`, `snapshot_download`, `model_info`, `HF_HUB_CACHE`) is compatible (verified by the test suite).

Remote-code adapters built on transformers must follow the `trust_remote_code` hardening recorded in the backend component doc: prefer pinning the model repo `revision` (except where the loader forwards `revision` into a different-repo sub-component — MOSS-TTSD propagates it to its companion codec, so it loads at HEAD), and bridge any renamed transformers symbols defensively (e.g. MOSS-TTSD's `_install_transformers_compat`, a no-op on 5.x).

### Exploratory baseline (2026-06-21)

Because Fish Audio S2-Pro requires `transformers<=4.57.3` (and `torch==2.8.0`) — the inverse of MOSS-TTSD/Higgs v3 — and one environment cannot host both, the baseline is **temporarily exploratory** during Phase 5.2 model trials:

- **`pyproject.toml` widens the pin to `transformers>=4.38`** (no upper bound) so the operator can install whichever major the model under exploration needs. The operator installs the latest 5.x to exercise MOSS-TTSD/Higgs/VoxCPM2/Kokoro, or downgrades to `4.57.3` to exercise Qwen3-TTS / Fish S2-Pro.
- **Currently installed: `transformers==4.57.3` + `huggingface-hub==0.36.2`** (flipped **down** 2026-06-21, at the user's request, to support **Qwen3-TTS** — the version its `qwen-tts` package requires — and Fish S2-Pro; the inverse of the earlier flip up to `5.12.1` for MOSS-TTSD/Higgs v3). `accelerate` is at `1.12.0` (the version `qwen-tts` pins) and `torch` stays at `2.10.0`. The full backend suite (812 tests) passes on both 4.57.3 and 5.12.1.
- **Qwen3-TTS re-registered (2026-06-21):** investigation showed `qwen-tts`'s `transformers==4.57.3` pin is a true runtime requirement (on transformers 5.x its bundled model code breaks on several API drifts — `check_model_inputs`, removed config special-token attrs, the RoPE-init refactor — too many to shim cleanly). The user therefore chose to **run the version `qwen-tts` requires** (4.57.3) rather than shim. At that baseline `qwen-tts` installs and runs **natively** (verified end-to-end on GPU: load + 24 kHz Italian generation). So the Qwen3-TTS adapter is **re-registered** (`Qwen3TTSAdapter` in `_ADAPTER_REGISTRY`, `loader_available=true`), lazy-imports the package, and is treated exactly like the other GPU-host adapters. The earlier unregistration (because `qwen-tts` could not be *co-installed* with a 5.x stack) no longer applies: at the 4.57.3 baseline its pin matches the install, and `voxcpm` (`transformers>=4.36.2`) / `kokoro` (unpinned) remain satisfied.
- **Runtime trade-off (direction-dependent):** under the **current 4.57.3 install**, **Qwen3-TTS and Fish Audio S2-Pro load**, but **MOSS-TTSD v1.0 and Higgs Audio v3 cannot load at runtime** (they need transformers ≥5.0/≥5.5); under a **5.x install**, the inverse (MOSS-TTSD loads; Qwen3-TTS / Fish S2-Pro do not). **All four adapters remain *registered* (`loader_available=true`)** — the adapter modules import fine regardless and their unit tests are mocked, so loadability is purely a function of the installed transformers major (a documented, reversible runtime consequence of the exploratory baseline, not an install conflict). Qwen3-TTS is no longer a special unregistered case.
- **fish-speech is a GPU-host dependency, not a backend runtime dependency:** it is GitHub-only, pins `torch==2.8.0` (conflicts with this repo's `torch>=2.10` and VoxCPM2's `torchcodec`), and needs 12–24 GB VRAM. The Fish S2-Pro adapter lazy-imports it (raising a clear install hint), unit tests mock it, and full-weight runtime validation is a GPU-host step (the MOSS-TTSD precedent). On the GPU host, install it in a **dedicated environment** (`git clone … fish-speech && pip install -e .`).
- This state is to be **re-fixed to a single stable baseline later** (user choice). When it is, this subsection and the `pyproject` pin should be reconciled.

## Enforcement

### Trigger conditions

- **Design phase**: when adding a model to the architecture Compatibility Table or choosing a model-loading library/approach (it must be compatible with the transformers 5.x baseline).
- **Code phase**: when adding/upgrading a backend dependency that constrains `transformers`; when adding a model adapter (pick libraries compatible with transformers 5.x); when changing the adapter registry.

### Required patterns

- While the baseline is exploratory (2026-06-21), `pyproject.toml` keeps the widened pin `transformers>=4.38` and the operator installs the major required by the model under exploration. (When re-stabilized, restore a single bound such as `transformers>=5.5`.)
- A package whose dependency pins constrain `transformers`/`torch` (e.g. `qwen-tts` pinning `transformers==4.57.3`; `fish-speech` pinning `torch==2.8.0`) is **not** added as a backend runtime dependency — it must not drive a fresh `pip install -e .`. Its adapter is still **registered** when it lazy-imports the package as a GPU-host dependency (Qwen3-TTS, Fish S2-Pro): registration is uniform and loadability is a runtime function of the installed `transformers` major under the exploratory baseline. Add a code comment explaining the pin. (An adapter is left *unregistered* only when there is genuinely no in-process loader at all — e.g. Higgs v3, which is server-only.)

### Required checks

1. After changing dependencies, run `pip install -e ".[dev]"` and the full backend test suite; confirm all adapters' tests pass on transformers 5.x.
2. A newly added TTS package does not re-pin `transformers` below 5.5.

### Prohibited patterns

- Adding any package that **hard-pins** `transformers` (e.g. `qwen-tts` → `==4.57.3`) or `torch` (e.g. `fish-speech` → `==2.8.0`) as a backend **runtime** dependency — it would force-downgrade the shared stack. Such packages stay GPU-host-only and are lazy-imported.
- Silently editing `REQ-COMP-foss-only` or the objectives to accommodate a model.
- (While exploratory) leaving the installed `transformers` mismatched with the model actually being tested without noting it — record the current installed major in this decision's *Exploratory baseline* subsection. Once re-stabilized, downgrading below the chosen stable floor again becomes prohibited.
