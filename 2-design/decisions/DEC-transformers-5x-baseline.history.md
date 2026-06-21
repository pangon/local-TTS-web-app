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

### Option D: Exploratory in-flux baseline — flip transformers per model under trial (chosen 2026-06-21)
- Context: Fish Audio S2-Pro's only loader, `fish-speech` v2.0.0, hard-pins `transformers<=4.57.3` + `torch==2.8.0` — the inverse of MOSS-TTSD/Higgs v3 (`>=5.0`/`>=5.5`). No single environment satisfies both.
- Pros: lets the user try each Phase 5.2 model during exploration without committing to one baseline; cheap and reversible (the suite passes on both 4.57.3 and 5.12.1; torch untouched at 2.10 since fish-speech stays GPU-host-only).
- Cons: under a 4.x install MOSS-TTSD/Higgs v3 cannot load at runtime (documented caveat); the baseline is non-deterministic until re-stabilized; requires the operator to flip `transformers` per model.
- Alternatives weighed and declined by the user: environment/process isolation for fish-speech (conflicts with `DEC-single-process`; larger change) and keeping the 5.x baseline + deferring S2-Pro.

### Option E: Re-enable Qwen3-TTS by running the transformers version it requires (4.57.3) (chosen 2026-06-21)
- Context: the user asked to support Qwen3-TTS loading/use again. Investigation: `qwen-tts` 0.1.1 (latest) hard-pins `transformers==4.57.3` and bundles its own model code. On the then-installed transformers 5.12.1 the package could be *imported* with a one-symbol monkeypatch (`check_model_inputs` decorator-factory bridge) installed `--no-deps`, but model **construction** then failed on further 5.x drifts (`config.pad_token_id` removed from the base config; the RoPE-init refactor — `ROPE_INIT_FUNCTIONS['default']` gone). Shimming all of these was assessed as an iceberg / unclean.
- Decision: the user rejected the shim approach ("non mi sembra pulito") and chose to **run the transformers version `qwen-tts` requires** — flip the exploratory baseline's installed `transformers` down to `4.57.3`, where `qwen-tts` works **natively** (no shims). Verified end-to-end on GPU (RTX 4070 Ti): load 7.6 s, 24 kHz Italian generation. The Qwen3-TTS adapter is **re-registered**.
- Pros: clean (no third-party monkeypatching); Qwen3-TTS *and* Fish S2-Pro both load at 4.57.3; registration policy becomes uniform across GPU-host adapters. `voxcpm` (`>=4.36.2`) / `kokoro` (unpinned) stay satisfied; full suite green on both majors.
- Cons: under this 4.57.3 install MOSS-TTSD/Higgs v3 are not loadable at runtime (the inverse trade-off; reversible by flipping back up). Baseline remains non-deterministic until re-stabilized.
- Rejected sub-option: keep the 5.x baseline and ship a compat shim so `qwen-tts` runs on 5.x — declined as unclean given the number of runtime drifts.

## Human involvement

**Type**: ai-proposed/human-approved

**Notes**: Surfaced during a user-reported MOSS-TTSD load failure (`cannot import name 'PreTrainedConfig'`). The agent diagnosed the transformers-version conflict and presented three options; the user selected "Upgrade to transformers 5.x" (2026-06-20). On 2026-06-21, while implementing `TASK-loader-fish-s2-pro`, the agent surfaced the inverse conflict (fish-speech needs `transformers<=4.57.3`) as a constraint tension and presented three options; the user chose to make the baseline exploratory and install a fish-speech-compatible `transformers` for now, to re-fix later. Later on 2026-06-21 the user asked to re-enable Qwen3-TTS; the agent investigated a 5.x shim, found it unclean, and the user directed running the transformers version `qwen-tts` requires (4.57.3) — the agent flipped the installed major down and re-registered the adapter (Option E).

## Changelog

| Date | Change | Involvement |
|------|--------|-------------|
| 2026-06-20 | Initial decision: move backend baseline to transformers>=5.5; drop qwen-tts and unregister the Qwen3-TTS adapter | ai-proposed/human-approved |
| 2026-06-21 | Baseline made **exploratory**: pin widened to `transformers>=4.38`, installed downgraded to 4.57.3 (+ huggingface-hub 0.36.2) to be fish-speech-compatible for Fish S2-Pro. MOSS-TTSD/Higgs v3 not loadable at runtime under 4.x (documented). fish-speech is GPU-host-only (GitHub, pins torch==2.8.0). To be re-stabilized later | ai-proposed/human-approved |
| 2026-06-21 | Installed `transformers` flipped back **up to 5.12.1** (+ huggingface-hub 1.20.1) at the user's request, to exercise Higgs Audio v3 (`TASK-loader-higgs-audio-v3`) / MOSS-TTSD. Under this 5.x install Fish S2-Pro is not runnable (inverse trade-off); full suite (812 tests) green on both 4.57.3 and 5.12.1; torch unchanged at 2.10. Exploratory baseline unchanged in policy (pin stays `>=4.38`) — only the installed major moved | human-requested |
| 2026-06-21 | **Qwen3-TTS re-enabled** (user request). Investigated whether `qwen-tts` could run on transformers 5.x; it imports with one monkeypatch but model construction hits further 5.x drifts (config `pad_token_id`, RoPE-init refactor) — too many to shim cleanly. User rejected shimming and chose to **run the transformers version `qwen-tts` requires**: installed `transformers` flipped **down to 4.57.3** (+ huggingface-hub 0.36.2; accelerate already 1.12.0), `qwen-tts` installed as a GPU-host dep, and the **Qwen3-TTS adapter re-registered** (`loader_available=true`). Verified native load + 24 kHz Italian generation on GPU. Under 4.57.3, MOSS-TTSD/Higgs v3 are not runtime-loadable (inverse, reversible). Registration is now uniform; Qwen3-TTS is no longer the unregistered special case. Full suite 812 green on 4.57.3. See Option E | human-requested |
| 2026-06-21 | **Correction:** Higgs Audio v3 turned out to be **server-only** (vLLM-Omni/SGLang-Omni); `higgs_multimodal_qwen3` is absent from transformers (released + main) and the repo ships no remote code, so it has no in-process loader and does **not** drive the transformers version. Its adapter was **unregistered** (`loader_available=false`; user chose "mark not-yet-loadable"). The ≥5.x baseline now rests on **MOSS-TTSD alone**. Decision still valid; rationale narrowed | ai-noted/human-decided |
| 2026-06-21 | **CosyVoice 3 added as a third GPU-host dependency** (`TASK-loader-cosyvoice`, Phase 5.3). The `cosyvoice` package hard-pins `transformers==4.51.3` / `torch==2.3.1` / `numpy==1.26.4` — distinct from qwen-tts/fish-speech (`<=4.57.3`) and MOSS-TTSD (`>=5.x`) — so it is GPU-host-only (dedicated env, lazy-imported, mocked in tests), not a runtime dep; the `CosyVoice3Adapter` is registered uniformly. Reinforces (does not change) the decision. Full suite 887 green | ai-proposed/human-approved |
