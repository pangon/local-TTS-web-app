# Tasks

## Status Legend

| Symbol | Status |
|--------|--------|
| `Todo` | Not started |
| `In Progress` | Currently being worked on |
| `Blocked` | Waiting on a dependency or decision (reason **must** be noted in the Notes column) |
| `Done` | Completed |
| `Cancelled` | No longer needed (reason **must** be noted in the Notes column) |

## Priority Legend

| Priority | Meaning |
|----------|---------|
| `P0` | Infrastructure / cross-cutting — required before feature work |
| `P1` | Implements a Must-have goal |
| `P2` | Implements a Should-have goal |
| `P3` | Implements a Could-have goal |

---

## Task Table

<!-- Req column: links to requirements this task implements (comma-separated), or "-" if none. -->

### Setup & Infrastructure

| ID | Task | Priority | Status | Req | Dependencies | Updated | Notes |
|----|------|----------|--------|-----|--------------|---------|-------|
| TASK-python-project-scaffold | Initialize Python project with pyproject.toml, src layout, and dependencies | P0 | Done | - | - | 2026-03-14 | |
| TASK-vue-project-scaffold | Initialize Vue 3 + Vite project with Vue Router | P0 | Done | - | - | 2026-03-14 | |

### Backend

| ID | Task | Priority | Status | Req | Dependencies | Updated | Notes |
|----|------|----------|--------|-----|--------------|---------|-------|
| TASK-fastapi-app-skeleton | Create FastAPI app with Uvicorn, localhost binding, and startup URL display | P0 | Done | [REQ-SEC-localhost-binding](../1-objectives/requirements/REQ-SEC-localhost-binding.md) | TASK-python-project-scaffold | 2026-03-14 | |
| TASK-sqlite-schema-init | Implement SQLite database initialization with full schema on startup | P0 | Done | - | TASK-fastapi-app-skeleton | 2026-03-14 | |
| TASK-static-file-serving | Configure FastAPI to serve Vue production build as static files | P0 | Done | - | TASK-fastapi-app-skeleton, TASK-vue-project-scaffold | 2026-03-14 | |
| TASK-startup-gpu-check | Integrate GPU validation into FastAPI startup sequence | P1 | Done | [REQ-F-gpu-validation](../1-objectives/requirements/REQ-F-gpu-validation.md) | TASK-fastapi-app-skeleton, TASK-tts-engine-interface | 2026-03-14 | |
| TASK-startup-ffmpeg-check | Validate ffmpeg availability at startup with clear error message | P1 | Done | [REQ-F-synthesize-audiobook](../1-objectives/requirements/REQ-F-synthesize-audiobook.md) | TASK-fastapi-app-skeleton, TASK-synthesizer | 2026-03-14 | ffmpeg is a system dependency required by pydub for MP3 encoding |
| TASK-sse-endpoint | Implement SSE endpoint with keepalive and event broadcasting | P0 | Done | - | TASK-fastapi-app-skeleton | 2026-03-14 | |
| TASK-model-service | Implement Model Service and API: list, download, load with VRAM check | P1 | Done | [REQ-F-model-listing](../1-objectives/requirements/REQ-F-model-listing.md), [REQ-F-model-download](../1-objectives/requirements/REQ-F-model-download.md), [REQ-F-gpu-validation](../1-objectives/requirements/REQ-F-gpu-validation.md) | TASK-tts-engine-interface | 2026-03-14 | |
| TASK-model-download-sse | Wire model download progress to SSE events | P1 | Done | [REQ-F-model-download](../1-objectives/requirements/REQ-F-model-download.md) | TASK-model-service, TASK-sse-endpoint | 2026-03-14 | Already implemented and tested as part of TASK-model-service |
| TASK-job-service | Implement job queue with background thread processing | P1 | Done | [REQ-F-synthesize-audiobook](../1-objectives/requirements/REQ-F-synthesize-audiobook.md) | TASK-tts-engine-interface, TASK-sqlite-schema-init | 2026-04-11 | |
| TASK-synthesis-job-api | Implement POST /jobs/synthesis with file upload, validation, and disk space check | P1 | Done | [REQ-F-upload-text-file](../1-objectives/requirements/REQ-F-upload-text-file.md), [REQ-F-disk-space-preflight](../1-objectives/requirements/REQ-F-disk-space-preflight.md) | TASK-job-service | 2026-06-16 | Multipart contract superseded by TASK-synthesis-api-text-input (JSON confirmed text); file upload moved to TASK-preprocess-api per DEC-preprocess-review-flow |
| TASK-job-progress-sse | Wire job progress, completed, and failed events to SSE | P1 | Done | [REQ-F-synthesis-progress](../1-objectives/requirements/REQ-F-synthesis-progress.md) | TASK-job-service, TASK-sse-endpoint | 2026-04-12 | |
| TASK-library-service-create | Implement audiobook and chapter record creation on synthesis completion | P1 | Done | [REQ-F-synthesize-audiobook](../1-objectives/requirements/REQ-F-synthesize-audiobook.md), [REQ-F-chapter-split-output](../1-objectives/requirements/REQ-F-chapter-split-output.md) | TASK-job-service, TASK-sqlite-schema-init | 2026-04-12 | |
| TASK-library-api | Implement audiobook list, get, and delete API endpoints with cascade cleanup | P1 | Done | [REQ-F-library-listing](../1-objectives/requirements/REQ-F-library-listing.md), [REQ-F-delete-audiobook](../1-objectives/requirements/REQ-F-delete-audiobook.md) | TASK-library-service-create | 2026-06-15 | |
| TASK-chapter-audio-streaming | Implement chapter audio streaming with HTTP Range support | P1 | Done | [REQ-F-audiobook-playback](../1-objectives/requirements/REQ-F-audiobook-playback.md) | TASK-library-api | 2026-06-15 | Range support provided by Starlette FileResponse (206/Content-Range/416); served inline (no attachment disposition) |
| TASK-playback-position-api | Implement GET and PUT playback position endpoints | P1 | Done | [REQ-F-playback-resume](../1-objectives/requirements/REQ-F-playback-resume.md) | TASK-sqlite-schema-init | 2026-06-15 | Two-level upsert (PlaybackService); GET defaults to chapter 1/empty when never played |
| TASK-model-voices-api | Implement GET /models/{id}/voices endpoint for voice and language listing | P2 | Todo | [REQ-F-voice-language-selection](../1-objectives/requirements/REQ-F-voice-language-selection.md) | TASK-model-service | 2026-03-12 | |
| TASK-preview-job-service | Implement preview job API: POST /jobs/preview and GET /jobs/{id}/audio | P2 | Todo | [REQ-F-text-preview](../1-objectives/requirements/REQ-F-text-preview.md) | TASK-job-service, TASK-preprocess-api | 2026-06-16 | POST /jobs/preview consumes already-normalized text and does not re-preprocess (DEC-preprocess-review-flow) |
| TASK-performance-logging | Record synthesis performance metrics in database on job completion | P2 | Todo | [REQ-F-performance-logging](../1-objectives/requirements/REQ-F-performance-logging.md) | TASK-job-service | 2026-03-12 | |
| TASK-job-monitoring-api | Implement GET /jobs and GET /jobs/{id} with error and performance details | P2 | Todo | [REQ-F-job-monitoring](../1-objectives/requirements/REQ-F-job-monitoring.md) | TASK-performance-logging | 2026-03-12 | |
| TASK-resource-monitoring-api | Implement GET /system/status with CPU, memory, GPU, and loaded model | P2 | Todo | [REQ-F-resource-monitoring](../1-objectives/requirements/REQ-F-resource-monitoring.md) | TASK-tts-engine-interface | 2026-03-12 | |
| TASK-audiobook-download-api | Implement GET /audiobooks/{id}/download as ZIP archive | P2 | Todo | [REQ-F-download-audiobook](../1-objectives/requirements/REQ-F-download-audiobook.md) | TASK-library-api | 2026-03-12 | |
| TASK-model-cache-api | Implement GET /models/cache and DELETE /models/{id}/cache endpoints | P2 | Todo | [REQ-F-model-cache-view](../1-objectives/requirements/REQ-F-model-cache-view.md), [REQ-F-model-delete](../1-objectives/requirements/REQ-F-model-delete.md) | TASK-model-service | 2026-03-12 | |
| TASK-gpu-validator | Implement NVIDIA GPU/CUDA detection and VRAM availability checking | P1 | Done | [REQ-F-gpu-validation](../1-objectives/requirements/REQ-F-gpu-validation.md) | TASK-python-project-scaffold | 2026-03-14 | Moved from TTS Engine section per DEC-tts-as-backend-module |
| TASK-model-loader | Implement HuggingFace model download, caching, and GPU loading | P1 | Done | [REQ-F-model-download](../1-objectives/requirements/REQ-F-model-download.md) | TASK-gpu-validator | 2026-03-14 | Moved from TTS Engine section per DEC-tts-as-backend-module |
| TASK-chapter-parser | Implement chapter structure detection and text splitting | P1 | Done | [REQ-F-chapter-split-output](../1-objectives/requirements/REQ-F-chapter-split-output.md) | TASK-python-project-scaffold | 2026-03-14 | Moved from TTS Engine section per DEC-tts-as-backend-module |
| TASK-synthesizer | Implement text-to-MP3 synthesis with progress callbacks | P1 | Done | [REQ-F-synthesize-audiobook](../1-objectives/requirements/REQ-F-synthesize-audiobook.md) | TASK-model-loader, TASK-chapter-parser | 2026-03-14 | Moved from TTS Engine section per DEC-tts-as-backend-module |
| TASK-tts-engine-interface | Assemble TTSEngine class with clean public interface | P2 | Done | [REQ-MNT-modular-ai-layer](../1-objectives/requirements/REQ-MNT-modular-ai-layer.md) | TASK-synthesizer | 2026-03-14 | Moved from TTS Engine section per DEC-tts-as-backend-module |
| TASK-default-voice-config | Configure and document default model, voice, and language (Italian) | P2 | Todo | [REQ-F-default-voice-quality](../1-objectives/requirements/REQ-F-default-voice-quality.md) | TASK-tts-engine-interface | 2026-03-14 | Moved from TTS Engine section per DEC-tts-as-backend-module |
| TASK-model-adapter-interface | Define ModelAdapter protocol and refactor ModelLoader to use adapter-based loading and inference | P1 | Done | [REQ-F-model-download](../1-objectives/requirements/REQ-F-model-download.md), [REQ-F-synthesize-audiobook](../1-objectives/requirements/REQ-F-synthesize-audiobook.md) | TASK-model-loader, TASK-synthesizer | 2026-04-11 | See architecture.md § Model-Specific Loading Requirements |
| TASK-model-loader-status | Add loader_available flag to COMPATIBLE_MODELS and expose via API; disable download and load in frontend for models without an adapter | P1 | Done | [REQ-F-model-listing](../1-objectives/requirements/REQ-F-model-listing.md) | TASK-model-adapter-interface | 2026-04-11 | Spans backend + frontend |
| TASK-loader-kokoro | Implement Kokoro-82M adapter using kokoro pip package (KPipeline) | P1 | Done | [REQ-F-synthesize-audiobook](../1-objectives/requirements/REQ-F-synthesize-audiobook.md) | TASK-model-adapter-interface | 2026-04-11 | Dep: kokoro>=0.9.2; Italian voices: if_sara, im_nicola |
| TASK-loader-chatterbox | Implement Chatterbox adapter using chatterbox-tts pip package | P1 | Todo | [REQ-F-synthesize-audiobook](../1-objectives/requirements/REQ-F-synthesize-audiobook.md) | TASK-model-adapter-interface | 2026-04-11 | Dep: chatterbox-tts; 23 langs incl. Italian |
| TASK-loader-xtts-v2 | Implement XTTS-v2 adapter using Coqui TTS pip package | P1 | Todo | [REQ-F-synthesize-audiobook](../1-objectives/requirements/REQ-F-synthesize-audiobook.md) | TASK-model-adapter-interface | 2026-04-11 | Dep: TTS (Coqui); first-class Italian support |
| TASK-loader-cosyvoice | Implement CosyVoice 3 adapter using CosyVoice repo/package | P1 | Todo | [REQ-F-synthesize-audiobook](../1-objectives/requirements/REQ-F-synthesize-audiobook.md) | TASK-model-adapter-interface | 2026-04-11 | Dep: CosyVoice; 9 langs incl. Italian |
| TASK-loader-qwen3-tts | Implement Qwen3-TTS adapter using qwen-tts pip package | P1 | Done | [REQ-F-synthesize-audiobook](../1-objectives/requirements/REQ-F-synthesize-audiobook.md) | TASK-model-adapter-interface | 2026-04-12 | Dep: qwen-tts; 10 langs incl. Italian |
| TASK-loader-parler-tts | Implement Parler-TTS adapter using parler-tts GitHub package | P1 | Todo | [REQ-F-synthesize-audiobook](../1-objectives/requirements/REQ-F-synthesize-audiobook.md) | TASK-model-adapter-interface | 2026-04-11 | Dep: parler-tts; 8 langs incl. Italian |
| TASK-loader-dia | Implement Dia adapter using dia pip package or transformers>=5.x | P2 | Todo | [REQ-F-synthesize-audiobook](../1-objectives/requirements/REQ-F-synthesize-audiobook.md) | TASK-model-adapter-interface | 2026-04-11 | English only; lower priority |
| TASK-loader-f5-tts | Implement F5-TTS adapter using f5-tts pip package | P2 | Todo | [REQ-F-synthesize-audiobook](../1-objectives/requirements/REQ-F-synthesize-audiobook.md) | TASK-model-adapter-interface | 2026-04-11 | Dep: f5-tts; Italian cross-lingual only |
| TASK-loader-orpheus | Implement Orpheus TTS adapter using orpheus-speech pip package | P2 | Todo | [REQ-F-synthesize-audiobook](../1-objectives/requirements/REQ-F-synthesize-audiobook.md) | TASK-model-adapter-interface | 2026-04-11 | Dep: orpheus-speech; Italian experimental |
| TASK-loader-zonos | Implement Zonos adapter using zonos pip package | P2 | Todo | [REQ-F-synthesize-audiobook](../1-objectives/requirements/REQ-F-synthesize-audiobook.md) | TASK-model-adapter-interface | 2026-04-11 | Dep: zonos; Italian limited |
| TASK-loader-fish-speech | Implement Fish Speech adapter using Fish Speech repo | P2 | Todo | [REQ-F-synthesize-audiobook](../1-objectives/requirements/REQ-F-synthesize-audiobook.md) | TASK-model-adapter-interface | 2026-04-11 | Dep: fish-speech; Italian <10K hrs training data |
| TASK-loader-higgs-audio | Implement Higgs Audio V2 adapter (transformers>=5.3 or dedicated package) | P2 | Todo | [REQ-F-synthesize-audiobook](../1-objectives/requirements/REQ-F-synthesize-audiobook.md) | TASK-model-adapter-interface | 2026-04-11 | Requires transformers 5.3+; Italian partial |
| TASK-model-license-metadata | Add license metadata (license, license_is_foss, license_notice) to COMPATIBLE_MODELS and expose it in GET /models | P2 | Done | [REQ-F-model-listing](../1-objectives/requirements/REQ-F-model-listing.md) | TASK-model-service | 2026-06-20 | Phase 5.2. Per DEC-model-license-disclosure. `COMPATIBLE_MODELS` is now `dict[str, ModelCatalogEntry]` (name + license + license_is_foss + license_notice); the three fields added to `ModelInfo` and the `GET /models` `ModelResponse`. All 12 existing models populated from their recorded weights-license. Three already-present models with FOSS code but non-commercial weights flagged non-FOSS with notices: coqui/XTTS-v2 (CPML), fishaudio/fish-speech-1.5 (CC-BY-NC-SA-4.0), SWivid/F5-TTS (CC-BY-NC-4.0). architecture § Model Licensing enumeration reconciled to include these three (minor doc fix). 5 new tests (suite 665 passing) |
| TASK-loader-voxcpm2 | Implement VoxCPM2 adapter; register the model in COMPATIBLE_MODELS with loader_available + license metadata | P2 | Done | [REQ-F-synthesize-audiobook](../1-objectives/requirements/REQ-F-synthesize-audiobook.md) | TASK-model-adapter-interface, TASK-model-license-metadata | 2026-06-20 | Phase 5.2. `tts/adapters/voxcpm2.py` (`VoxCPM2Adapter`) via the `voxcpm` package (`VoxCPM.from_pretrained()`, lazy import; auto-selects CUDA), registered in `_ADAPTER_REGISTRY`; `openbmb/VoxCPM2` added to `COMPATIBLE_MODELS` (**Apache-2.0/FOSS**, no notice). 48 kHz `sample_rate` — pipeline reads the rate dynamically + ffmpeg encodes it (verified by test, no pipeline change; resolves completeness Minor finding 5). **Auto-detect variant** (architecture Compatibility Table): the model detects language from text, so `_resolve_language` validates the ISO 639-1 code + defaults Italian (DEC-default-italian-language) but does NOT forward it (advisory); voice = zero-shot reference-audio cloning (no named voices); `normalize=False` keeps the exact confirmed text (DEC-preprocess-review-flow). `voxcpm>=2.0.3` added to pyproject and installed in the venv (verified against the real 2.0.3 API: `from_pretrained(device=…)`, `_generate(text, prompt_wav_path, prompt_text, normalize=False, …)`; loader-chosen device passed through for GPU inference); tests mock the package. 30 new tests; full backend suite 695 passing |
| TASK-loader-moss-tts | Implement MOSS-TTSD adapter; register the model in COMPATIBLE_MODELS with loader_available + license metadata | P2 | Todo | [REQ-F-synthesize-audiobook](../1-objectives/requirements/REQ-F-synthesize-audiobook.md) | TASK-model-adapter-interface, TASK-model-license-metadata | 2026-06-20 | Phase 5.2 (user "MOSS-TSS" = OpenMOSS MOSS-TTSD). `OpenMOSS-Team/MOSS-TTSD-v1.0`, **Apache-2.0 (FOSS)**. Loader: transformers `AutoModel`/`AutoProcessor` + `trust_remote_code=True` + companion `OpenMOSS-Team/MOSS-Audio-Tokenizer`. 20 langs incl. Italian (v0.5 is CN/EN only). Dialogue/multi-speaker–oriented — architectural mismatch for single-voice narration. 24 kHz; ~8B params, ~19 GB VRAM (exceeds min-spec 4 GB GPU; VRAM preflight blocks on small GPUs). Translate ISO 639-1 → model identifier |
| TASK-loader-fish-s2-pro | Implement Fish Audio S2-Pro adapter; register the model in COMPATIBLE_MODELS with loader_available + license metadata | P2 | Todo | [REQ-F-synthesize-audiobook](../1-objectives/requirements/REQ-F-synthesize-audiobook.md) | TASK-model-adapter-interface, TASK-model-license-metadata | 2026-06-20 | Phase 5.2. `fishaudio/s2-pro` (gated HF download), distinct from TASK-loader-fish-speech (fish-speech-1.5). ⚠️ **Fish Audio Research License — non-commercial, NOT FOSS** (free personal use; commercial paid) → license_is_foss=false + license_notice (DEC-model-license-disclosure). Loader: `fish-speech` repo/package (same family as fish-speech-1.5). 80+ langs incl. Italian; ~5B params, 12–24 GB VRAM. Translate ISO 639-1 → model identifier |
| TASK-loader-higgs-audio-v3 | Implement Higgs Audio v3 adapter; register the model in COMPATIBLE_MODELS with loader_available + license metadata | P2 | Todo | [REQ-F-synthesize-audiobook](../1-objectives/requirements/REQ-F-synthesize-audiobook.md) | TASK-model-adapter-interface, TASK-model-license-metadata | 2026-06-20 | Phase 5.2. `bosonai/higgs-audio-v3-tts-4b`, distinct from TASK-loader-higgs-audio (higgs-audio-v2). ⚠️ **Boson Research & Non-Commercial License — NOT FOSS** (free personal use; commercial paid) → license_is_foss=false + license_notice (DEC-model-license-disclosure). Loader: custom arch `HiggsMultimodalQwen3ForConditionalGeneration`, needs transformers≥5.5 (native, no remote-code); serve via SGLang-Omni/vLLM-Omni. 102 langs incl. Italian; 24 kHz; ~4B params, ~9.3 GB weights. Translate ISO 639-1 → model identifier |
| TASK-preprocessing-pipeline-skeleton | Create Preprocessing Service: stage interface, pipeline runner, and language/model profile config resolution | P1 | Done | [REQ-MNT-preprocessing-pipeline](../1-objectives/requirements/REQ-MNT-preprocessing-pipeline.md) | TASK-python-project-scaffold | 2026-06-16 | Phase 5.1. Separate backend service per DEC-text-preprocessing-pipeline; not in the TTS subpackage. Package `src/local_tts/preprocessing/` (Stage protocol + registry, Pipeline runner, language/model profiles, domain-dict loader, PreprocessingService). Stage name constants + registration seam in `__init__.py` define the contract for the 4 stage tasks |
| TASK-stage-unicode-sanitization | Implement Unicode sanitization stage (invisible/control chars, NBSP/whitespace variants, dash/quote variants, disallowed Unicode, emoji remove-or-verbalize) | P1 | Done | [REQ-F-text-unicode-sanitization](../1-objectives/requirements/REQ-F-text-unicode-sanitization.md) | TASK-preprocessing-pipeline-skeleton | 2026-06-16 | Phase 5.1. `preprocessing/unicode_sanitization.py`: NFC normalization, line-ending normalization, emoji remove/verbalize (config-driven; built-in Italian table + Unicode-name fallback), dash/quote normalization, control/format/surrogate/private-use removal, NBSP/space-variant→space. Registered in `__init__.py`; 51 new tests |
| TASK-stage-layout-repair | Implement layout-repair stage (end-of-line de-hyphenation, sentence reflow, page-number/fragment stripping, whitespace normalization; preserve paragraph/chapter boundaries) | P1 | Done | [REQ-F-text-layout-repair](../1-objectives/requirements/REQ-F-text-layout-repair.md) | TASK-preprocessing-pipeline-skeleton | 2026-06-16 | Phase 5.1. `preprocessing/layout_repair.py`: block-based reflow (blank lines = paragraph boundaries), end-of-line de-hyphenation, isolated page-number/fragment stripping, intra-line + blank-line whitespace collapse; heading- and list-item lines kept standalone so chapter detection survives (verified end-to-end via parse_chapters). Behavior switches via PARAM_* (dehyphenate/reflow/strip_page_numbers/collapse_whitespace). No language data (universal tables only). Registered in `__init__.py`; 30 new tests |
| TASK-stage-numeric-symbolic-verbalization | Implement language-aware numeric, date, percentage, currency, and symbol verbalization stage | P1 | Done | [REQ-F-text-numeric-symbolic-verbalization](../1-objectives/requirements/REQ-F-text-numeric-symbolic-verbalization.md) | TASK-preprocessing-pipeline-skeleton | 2026-06-16 | Phase 5.1. `preprocessing/numeric_symbolic_verbalization.py`: dates, currency, percent/per-mille, temperature, ordinal indicators, plain cardinals/decimals (thousands+decimal separators), and standalone symbols. Number spelling delegated to `num2words` (LGPL, now a direct dep) keyed by `num2words_lang` from the language profile — no language branching in shared logic; full no-op without language data. Built-in Italian tables (DEC-default-italian-language). Registered in `__init__.py`; 47 new tests; 2 stale subset-assertion tests updated to clear the registry first |
| TASK-stage-abbreviation-expansion | Implement abbreviation expansion stage with built-in language set and optional on-disk domain dictionary | P2 | Done | [REQ-F-abbreviation-expansion](../1-objectives/requirements/REQ-F-abbreviation-expansion.md) | TASK-preprocessing-pipeline-skeleton | 2026-06-16 | Phase 5.1. `preprocessing/abbreviation_expansion.py`: two passes — optional caller-supplied domain dictionary (language-independent, case-sensitive by default) then language-specific built-in set (Italian `BUILTIN_LANGUAGE_DATA`, case-insensitive). Trailing period re-added only at end-of-text/line so honorifics survive (`sig. Rossi`→`signor Rossi`). PARAM_* switches (expand_abbreviations/apply_domain_dictionary + per-pass case). Domain dict at `config/preprocessing/domain_dictionary.json` (absent by default; `.example.json` + README committed). Registered in `__init__.py`; 37 new tests, suite 595 passing |
| TASK-preprocess-api | Implement POST /preprocess (file or text input), apply loaded-model preprocessing profile, return normalized text | P1 | Done | [REQ-F-upload-text-file](../1-objectives/requirements/REQ-F-upload-text-file.md), [REQ-USA-normalized-text-review](../1-objectives/requirements/REQ-USA-normalized-text-review.md), [REQ-PERF-preprocessing-overhead](../1-objectives/requirements/REQ-PERF-preprocessing-overhead.md) | TASK-preprocessing-pipeline-skeleton, TASK-stage-unicode-sanitization, TASK-stage-layout-repair, TASK-stage-numeric-symbolic-verbalization, TASK-stage-abbreviation-expansion, TASK-model-service | 2026-06-16 | Phase 5.1. `api/preprocess.py`: synchronous `POST /preprocess` (multipart file or text + optional language); validates `.txt`/≤2MB/UTF-8/non-empty + exactly-one-of file/text (400), 409 when no model loaded, applies loaded-model profile via PreprocessingService, returns normalized text + before/after counts. Wired into app.state lifespan. 23 new tests incl. latency-bound smoke guards (≤1s/500-char, ≤10s/2MB) |
| TASK-synthesis-api-text-input | Change POST /jobs/synthesis from multipart file upload to JSON confirmed text; derive disk estimate from text length | P1 | Done | [REQ-F-synthesize-audiobook](../1-objectives/requirements/REQ-F-synthesize-audiobook.md), [REQ-USA-normalized-text-review](../1-objectives/requirements/REQ-USA-normalized-text-review.md) | TASK-synthesis-job-api, TASK-preprocess-api | 2026-06-16 | Phase 5.1. Supersedes the multipart contract of TASK-synthesis-job-api; synthesizes exactly the confirmed text, no re-preprocessing. `POST /jobs/synthesis` now takes JSON `{text, source_filename, voice?, language?}`; empty text → 400, no model → 409, disk preflight (from `len(text)`) → 409; file/UTF-8/2MB validation moved to /preprocess. Frontend still on old multipart contract until TASK-creation-view-review-step |
| TASK-schema-migration-mechanism | Implement schema versioning (PRAGMA user_version) and a startup migration runner; baseline current schema as v1 | P0 | Todo | - | TASK-sqlite-schema-init | 2026-06-15 | Phase 10. Evolve the SQLite schema without data loss; record DEC-schema-migrations when executed. Currently init_db uses CREATE TABLE IF NOT EXISTS with no migration path |

### Frontend

| ID | Task | Priority | Status | Req | Dependencies | Updated | Notes |
|----|------|----------|--------|-----|--------------|---------|-------|
| TASK-vite-dev-proxy | Configure Vite dev server to proxy /api requests to FastAPI | P0 | Done | - | TASK-vue-project-scaffold, TASK-fastapi-app-skeleton | 2026-03-14 | |
| TASK-frontend-sse-client | Implement EventSource SSE client service in Vue | P0 | Done | - | TASK-sse-endpoint, TASK-vue-project-scaffold | 2026-03-14 | |
| TASK-model-management-view | Implement model management view: list, download with progress, load | P1 | Done | [REQ-F-model-listing](../1-objectives/requirements/REQ-F-model-listing.md), [REQ-F-model-download](../1-objectives/requirements/REQ-F-model-download.md) | TASK-model-service, TASK-frontend-sse-client | 2026-03-14 | |
| TASK-audiobook-creation-view | Implement audiobook creation view: file upload, trigger, progress display | P1 | Done | [REQ-F-upload-text-file](../1-objectives/requirements/REQ-F-upload-text-file.md), [REQ-F-synthesis-progress](../1-objectives/requirements/REQ-F-synthesis-progress.md) | TASK-synthesis-job-api, TASK-frontend-sse-client | 2026-06-16 | Normalized-text review step added by TASK-creation-view-review-step per DEC-preprocess-review-flow |
| TASK-library-view | Implement library view: browse audiobooks, delete with confirmation | P1 | Done | [REQ-F-library-listing](../1-objectives/requirements/REQ-F-library-listing.md), [REQ-F-delete-audiobook](../1-objectives/requirements/REQ-F-delete-audiobook.md) | TASK-library-api | 2026-06-15 | Inline (in-row) delete confirmation; rows link to /playback/:id |
| TASK-playback-view | Implement playback view: audio player, chapter navigation, playback resume | P1 | Done | [REQ-F-audiobook-playback](../1-objectives/requirements/REQ-F-audiobook-playback.md), [REQ-F-playback-resume](../1-objectives/requirements/REQ-F-playback-resume.md) | TASK-chapter-audio-streaming, TASK-playback-position-api | 2026-06-15 | Native &lt;audio&gt; player; resume seeks on loadedmetadata; bookmark saved on pause/end/chapter-change/unmount (best-effort) |
| TASK-creation-view-review-step | Rework audiobook-creation view: upload → call /preprocess → review/confirm normalized text → synthesize confirmed text | P1 | Done | [REQ-USA-normalized-text-review](../1-objectives/requirements/REQ-USA-normalized-text-review.md) | TASK-audiobook-creation-view, TASK-preprocess-api, TASK-synthesis-api-text-input | 2026-06-16 | Phase 5.1. Two-step flow: new `api/preprocess.ts` (`preprocessFile`) + `api/jobs.ts` switched to JSON `{text, source_filename, voice?, language?}`. `CreateView.vue` reworked: select .txt → "Preprocess & Review" (busy state) → editable normalized-text textarea with before/after char counts → "Confirm & Start Synthesis" (no auto-start). Resolved `language` from /preprocess is forwarded verbatim to /jobs/synthesis so both agree. Tests: rewrote `CreateView.spec.ts` + `api-jobs.spec.ts`, added `api-preprocess.spec.ts` (123 frontend tests passing, type-check clean) |
| TASK-model-list-adapter-grouping | Split the model-listing view into two lists: adapter-available and adapter-not-yet-available | P2 | Done | [REQ-F-model-listing](../1-objectives/requirements/REQ-F-model-listing.md) | TASK-model-management-view | 2026-06-20 | Phase 5.2 (first task). Frontend-only; uses the existing `loader_available` flag from `GET /models`. First list = `loader_available=true` (downloadable/loadable); second list = `loader_available=false` (shown for visibility, download/load unavailable). See architecture § Adapter Pattern |
| TASK-model-license-notice-ui | Display a license notice in the model-listing view for models with license_is_foss=false | P2 | Done | [REQ-F-model-listing](../1-objectives/requirements/REQ-F-model-listing.md) | TASK-model-license-metadata, TASK-model-management-view | 2026-06-20 | Phase 5.2. Per DEC-model-license-disclosure. Frontend-only: added `license`/`license_is_foss`/`license_notice` (already on `GET /models`) to the `Model` type (`api/models.ts`); `ModelsView.vue` renders a visible `.license-notice` (license-name badge + notice text) for every `license_is_foss=false` model in **both** the available and adapter-not-yet-available lists, with a defensive fallback when `license_notice` is null. 5 new ModelsView tests (suite 134 passing, type-check clean); frontend component doc updated. No backend/API change |
| TASK-voice-language-selection-ui | Add voice and language selection to audiobook creation form | P2 | Todo | [REQ-F-voice-language-selection](../1-objectives/requirements/REQ-F-voice-language-selection.md) | TASK-model-voices-api, TASK-audiobook-creation-view | 2026-03-12 | |
| TASK-text-preview-view | Implement text preview view: text input, synthesize, play ephemeral audio | P2 | Todo | [REQ-F-text-preview](../1-objectives/requirements/REQ-F-text-preview.md), [REQ-USA-normalized-text-review](../1-objectives/requirements/REQ-USA-normalized-text-review.md) | TASK-preview-job-service, TASK-frontend-sse-client | 2026-06-16 | Run input through /preprocess; review satisfied inline (no separate confirmation screen) per DEC-preprocess-review-flow |
| TASK-monitoring-view | Implement monitoring view: job list, error details, resource usage | P2 | Todo | [REQ-F-job-monitoring](../1-objectives/requirements/REQ-F-job-monitoring.md), [REQ-F-resource-monitoring](../1-objectives/requirements/REQ-F-resource-monitoring.md) | TASK-job-monitoring-api, TASK-resource-monitoring-api | 2026-03-12 | |
| TASK-audiobook-download-ui | Add download button to library view | P2 | Todo | [REQ-F-download-audiobook](../1-objectives/requirements/REQ-F-download-audiobook.md) | TASK-audiobook-download-api, TASK-library-view | 2026-03-12 | |
| TASK-model-cache-ui | Add cache view with disk usage and delete to model management | P2 | Todo | [REQ-F-model-cache-view](../1-objectives/requirements/REQ-F-model-cache-view.md), [REQ-F-model-delete](../1-objectives/requirements/REQ-F-model-delete.md) | TASK-model-cache-api, TASK-model-management-view | 2026-03-12 | |

### Deploy & Operations

| ID | Task | Priority | Status | Req | Dependencies | Updated | Notes |
|----|------|----------|--------|-----|--------------|---------|-------|
| TASK-startup-script | Create cross-platform startup script for Linux and Windows | P2 | Todo | [REQ-USA-simple-setup](../1-objectives/requirements/REQ-USA-simple-setup.md), [REQ-PORT-linux-windows](../1-objectives/requirements/REQ-PORT-linux-windows.md) | TASK-fastapi-app-skeleton, TASK-static-file-serving | 2026-03-12 | |
| TASK-setup-documentation | Write setup instructions with dependencies, system requirements, and quickstart | P2 | Todo | [REQ-USA-simple-setup](../1-objectives/requirements/REQ-USA-simple-setup.md) | TASK-startup-script | 2026-03-12 | |
| TASK-phase-3-manual-testing | Create runbook and document build/run/test commands for model management capabilities | P1 | Done | - | TASK-model-management-view | 2026-03-15 | Covers phases 1-3 |
| TASK-phase-3.1-manual-testing | Update runbook and component docs for model adapter and loader capabilities | P1 | Done | - | TASK-model-loader-status | 2026-06-15 | Covers Phase 3.1 |
| TASK-phase-4-manual-testing | Update runbook and component docs for audiobook synthesis capabilities | P1 | Done | - | TASK-audiobook-creation-view | 2026-04-12 | |
| TASK-phase-5-manual-testing | Update runbook and component docs for library and playback capabilities | P1 | Done | - | TASK-playback-view | 2026-06-15 | |
| TASK-phase-5.1-manual-testing | Update runbook and component docs for text preprocessing and the normalized-text review flow | P1 | Done | - | TASK-creation-view-review-step | 2026-06-20 | Covers Phase 5.1. Added runbook §Phase 5.1 (12 procedures: /preprocess file/text/validation/409, the four stages, per-language/per-model config + domain dictionary, latency bound, creation-view review flow, exact-text guarantee, and a messy PDF-style sample for GOAL-text-normalization criterion 6) + preprocessing troubleshooting rows; updated test-coverage descriptions; added preprocess/synthesis API bullet (backend) and creation-view review-flow bullet (frontend) to component docs. Also aligned all Phase 1-5 runbook REST/SSE references to the actual `/api/v1/...` prefix (SSE `/api/v1/events`), leaving the Vite-proxy `/api`/`/api/*` glob references as-is since they correctly describe the proxy prefix. Verified 2026-06-20 against the mounted prefix (`app.py` `prefix="/api/v1"`) and the Vite proxy config: no `/api`-vs-`/api/v1` discrepancy remains (the earlier "flagged, not swept" note was stale) |
| TASK-phase-6-manual-testing | Update runbook and component docs for voice selection and text preview capabilities | P2 | Todo | - | TASK-text-preview-view | 2026-03-15 | |
| TASK-phase-7-manual-testing | Update runbook and component docs for monitoring, downloads, and cache management | P2 | Todo | - | TASK-model-cache-ui | 2026-03-15 | |
| TASK-phase-8-manual-testing | Update runbook and component docs for deployment and setup documentation | P2 | Todo | - | TASK-setup-documentation | 2026-03-15 | |
| TASK-phase-10-manual-testing | Update runbook and component docs for the database migration mechanism (version check, upgrade, reset) | P1 | Todo | - | TASK-schema-migration-mechanism | 2026-06-15 | Covers Phase 10 |

---

## Execution Plan

Defines the order in which tasks should be executed. Tasks are grouped into phases; complete all tasks in a phase before moving to the next. Within a phase, execute tasks in the listed order. Each phase ends with a deployable or testable system.

### Phase 1: Project Scaffolding & Dev Environment

**Capabilities delivered:**
- Running FastAPI backend bound to localhost with startup URL display
- SQLite database initialized with full schema
- Running Vue 3 + Vite frontend with dev proxy to backend
- Production mode: FastAPI serves Vue static build

**Tasks:**
1. TASK-python-project-scaffold
2. TASK-vue-project-scaffold
3. TASK-fastapi-app-skeleton
4. TASK-sqlite-schema-init
5. TASK-vite-dev-proxy
6. TASK-static-file-serving

### Phase 2: TTS Engine Foundation (Backend Subpackage)

**Capabilities delivered:**
- GPU and CUDA validation at startup with clear error messages
- ffmpeg availability validation at startup with clear error messages
- HuggingFace model download, caching, and GPU loading
- Chapter detection and text splitting
- Text-to-MP3 synthesis with progress callbacks
- Clean TTSEngine interface within the backend component (`DEC-tts-as-backend-module`)

**Tasks:**
1. TASK-gpu-validator
2. TASK-model-loader
3. TASK-chapter-parser
4. TASK-synthesizer
5. TASK-tts-engine-interface
6. TASK-startup-gpu-check
7. TASK-startup-ffmpeg-check

### Phase 3: Model Management End-to-End

**Capabilities delivered:**
- SSE infrastructure for real-time server-to-client events
- Browse available HuggingFace TTS models with cache status in the UI
- Download models with real-time progress bar
- Load models onto GPU with VRAM preflight check

**Tasks:**
1. TASK-sse-endpoint
2. TASK-model-service
3. TASK-model-download-sse
4. TASK-frontend-sse-client
5. TASK-model-management-view
6. TASK-phase-3-manual-testing

### Phase 3.1: Model Adapter Abstraction & Kokoro Loader

**Capabilities delivered:**
- Model adapter protocol defining a common interface for loading, inference, and unloading across heterogeneous TTS models
- Each compatible model annotated with loader availability; models without an adapter are disabled in the frontend (download and load buttons hidden)
- Kokoro-82M adapter enabling actual TTS inference
- System remains functional throughout: models are progressively enabled as their adapters are implemented

**Tasks:**
1. TASK-model-adapter-interface
2. TASK-model-loader-status
3. TASK-loader-kokoro
4. TASK-loader-qwen3-tts
5. TASK-phase-3.1-manual-testing

### Phase 4: Audiobook Synthesis End-to-End

**Capabilities delivered:**
- Upload .txt file and trigger audiobook synthesis
- Background synthesis with real-time progress in the UI
- Disk space preflight check before synthesis
- Audiobook automatically created and persisted on completion with chapter-based output

**Tasks:**
1. TASK-job-service
2. TASK-synthesis-job-api
3. TASK-job-progress-sse
4. TASK-library-service-create
5. TASK-audiobook-creation-view
6. TASK-phase-4-manual-testing

### Phase 5: Library & Playback

**Capabilities delivered:**
- Browse all generated audiobooks with title, date, and chapter count
- Play audiobooks in the browser with chapter navigation
- Resume playback from where the user left off (two-level bookmarks)
- Delete audiobooks with confirmation

**Tasks:**
1. TASK-library-api
2. TASK-chapter-audio-streaming
3. TASK-playback-position-api
4. TASK-library-view
5. TASK-playback-view
6. TASK-phase-5-manual-testing

### Phase 5.1: Text Preprocessing & Normalized-Text Review

**Capabilities delivered:**
- Raw input (uploaded file or pasted text) normalized into TTS-ready form via a modular pipeline: Unicode sanitization, layout repair, numeric/symbolic verbalization, abbreviation expansion (`GOAL-text-normalization` success criteria 1–4)
- Per-language and per-model pipeline configuration with an optional domain dictionary (success criterion 5)
- `POST /preprocess` returns normalized text synchronously within bounded latency
- User reviews and confirms the normalized text before audiobook generation; synthesis uses exactly the confirmed text (no re-preprocessing)

**Tasks:**
1. TASK-preprocessing-pipeline-skeleton
2. TASK-stage-unicode-sanitization
3. TASK-stage-layout-repair
4. TASK-stage-numeric-symbolic-verbalization
5. TASK-stage-abbreviation-expansion
6. TASK-preprocess-api
7. TASK-synthesis-api-text-input
8. TASK-creation-view-review-step
9. TASK-phase-5.1-manual-testing

### Phase 5.2: Priority Additional TTS Model Adapters

**Capabilities delivered:**
- Model-listing view split into two lists — models with an available adapter, then models whose adapter is not yet available — by the `loader_available` flag (`REQ-F-model-listing`)
- Model license disclosure: each model carries license metadata in `COMPATIBLE_MODELS` / `GET /models`, and the model-listing view shows a visible license notice for non-FOSS models (`REQ-F-model-listing`, `DEC-model-license-disclosure`)
- Four additional TTS models enabled through the existing `ModelAdapter` abstraction (`REQ-F-synthesize-audiobook`), each registered in `COMPATIBLE_MODELS` and translating the app-layer ISO 639-1 code to its model-specific identifier (architecture § Model-Specific Loading Requirements):
  - `openbmb/VoxCPM2` — Apache-2.0 (FOSS); `voxcpm` package; Italian; 48 kHz
  - `OpenMOSS-Team/MOSS-TTSD-v1.0` — Apache-2.0 (FOSS); transformers + `trust_remote_code`; Italian; dialogue-oriented; ~8B/~19 GB
  - `fishaudio/s2-pro` — ⚠️ Fish Audio Research License (non-commercial, not FOSS); `fish-speech` package; Italian
  - `bosonai/higgs-audio-v3-tts-4b` — ⚠️ Boson Research & Non-Commercial License (not FOSS); transformers≥5.5 custom arch; Italian
- Models progressively enabled via the `loader_available` flag as each adapter lands; the system stays functional throughout
- These are distinct from the Phase 9 entries (`fishaudio/fish-speech-1.5`, `higgs-audio-v2`)

> **Note:** The two non-FOSS models are open-weight and free for personal/local use but carry research/non-commercial licenses (commercial use is paid). They are permitted under the personal-use reading of `REQ-COMP-foss-only` AC2 and surfaced with a license notice per `DEC-model-license-disclosure`; the objectives artifacts were left unchanged (user choice, 2026-06-20). The license-disclosure tasks are sequenced first so the notice is live before the non-FOSS adapters land.

**Tasks:**
1. TASK-model-list-adapter-grouping
2. TASK-model-license-metadata
3. TASK-model-license-notice-ui
4. TASK-loader-voxcpm2
5. TASK-loader-moss-tts
6. TASK-loader-fish-s2-pro
7. TASK-loader-higgs-audio-v3

### Phase 6: Voice Selection & Text Preview

**Capabilities delivered:**
- View available voices and languages per model
- Select voice and language before synthesis
- Pre-tested Italian default voice configuration
- Quick TTS preview from direct text input (ephemeral, not saved to library)

**Tasks:**
1. TASK-model-voices-api
2. TASK-voice-language-selection-ui
3. TASK-default-voice-config
4. TASK-preview-job-service
5. TASK-text-preview-view
6. TASK-phase-6-manual-testing

### Phase 7: Monitoring, Downloads & Cache Management

**Capabilities delivered:**
- Performance metrics recorded per synthesis run
- Job monitoring view with status, progress, and error details
- System resource monitoring (CPU, memory, GPU)
- Download audiobooks as ZIP files
- View cached models with disk usage; delete cached models to free space

**Tasks:**
1. TASK-performance-logging
2. TASK-job-monitoring-api
3. TASK-resource-monitoring-api
4. TASK-monitoring-view
5. TASK-audiobook-download-api
6. TASK-audiobook-download-ui
7. TASK-model-cache-api
8. TASK-model-cache-ui
9. TASK-phase-7-manual-testing

### Phase 8: Deployment & Documentation

**Capabilities delivered:**
- Cross-platform startup script for Linux and Windows
- Complete setup documentation with dependencies and system requirements
- 5-or-fewer-commands setup flow

**Tasks:**
1. TASK-startup-script
2. TASK-setup-documentation
3. TASK-phase-8-manual-testing

### Phase 9: Additional Model Adapters (Optional)

**Capabilities delivered:**
- Per-model adapter implementations enabling TTS inference for additional supported models beyond Kokoro
- Models are progressively enabled as their adapters are implemented

**Tasks:**
1. TASK-loader-chatterbox
2. TASK-loader-xtts-v2
3. TASK-loader-cosyvoice
4. TASK-loader-parler-tts
5. TASK-loader-dia
6. TASK-loader-f5-tts
7. TASK-loader-orpheus
8. TASK-loader-zonos
9. TASK-loader-fish-speech
10. TASK-loader-higgs-audio

### Phase 10: Database Migrations

**Capabilities delivered:**
- Schema version tracking via `PRAGMA user_version`
- Ordered migration runner applied automatically at startup, evolving an existing SQLite database without data loss
- Current schema baselined as version 1
- Documented procedure for upgrading or resetting the local database

> **Note:** Today `init_db` uses `CREATE TABLE IF NOT EXISTS` with no migration path (the `SCHEMA_VERSION` constant is unused), so schema changes (e.g. the ISO 8601 timestamp defaults) only apply to freshly created databases. This phase is **independent of Phases 6–9** and should ideally land before any real (non-disposable) user data accumulates; its position as Phase 10 reflects sequencing in the plan, not low importance.

**Tasks:**
1. TASK-schema-migration-mechanism
2. TASK-phase-10-manual-testing
