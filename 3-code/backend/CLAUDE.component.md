# Backend

**Responsibility**: HTTP request handling, REST API, SSE endpoint, application services (Library, Job, Model, Monitor), SQLite storage, static file serving, and all TTS inference and GPU interaction via a modular subpackage.

**Technology**: Python, FastAPI, Uvicorn, SQLite (via `sqlite3` stdlib), PyTorch (CUDA), HuggingFace Transformers, huggingface_hub

## Interfaces

- HTTP REST + SSE with frontend: serves API endpoints and pushes real-time events
- TTS subpackage (internal): application services import and call `TTSEngine` for GPU inference, model management, and chapter parsing (`DEC-tts-as-backend-module`)
- Model adapter layer (internal): per-model loading and inference is delegated to concrete adapters implementing the `ModelAdapter` protocol (`src/local_tts/tts/adapters/`). New models are enabled by adding an adapter and registering it in `_ADAPTER_REGISTRY`; `ModelLoader.list_models()` exposes a `loader_available` flag (surfaced through `GET /models`) so the frontend can hide download/load actions for models without an adapter. See `architecture.md` § Model-Specific Loading Requirements.
- Preprocessing service (internal, `src/local_tts/preprocessing/`): a dedicated application service — **not** in the TTS subpackage (`DEC-text-preprocessing-pipeline`). A `Pipeline` runs an ordered list of discrete `Stage` objects (the `Stage` protocol + a name-keyed registry in `stages.py`), configured along two axes — language profile + model profile (`profiles.py`) — with an optional on-disk domain dictionary tolerant of absence. `PreprocessingService.preprocess(text, language, model_id)` returns normalized text + before/after char counts. New stages are added by implementing the `Stage` protocol under the canonical name constants (`STAGE_*`) and registering them via `register_stage` in `preprocessing/__init__.py`; the default model profile runs the registered subset of `DEFAULT_STAGE_ORDER`. The `model_id` of the loaded model is supplied by the caller (the `/preprocess` API layer reads it from the Model Service and owns the "no model loaded" error), keeping the service unit-testable without a GPU.
- Library & playback API (`src/local_tts/api/audiobooks.py`, `playback.py`): the `LibraryService` backs audiobook list/get/delete (delete cascades to chapter records and on-disk audio) and resolves chapter audio paths; chapter audio is streamed inline via `FileResponse` with HTTP Range support (206/`Content-Range`/416). Playback resume is a two-level bookmark (audiobook-level last chapter + per-chapter timestamp) served by the dedicated `PlaybackService` under `GET`/`PUT /audiobooks/{id}/position`.

## Requirements Addressed

| File | Type | Priority | Summary |
|------|------|----------|---------|
| [REQ-F-upload-text-file](../../1-objectives/requirements/REQ-F-upload-text-file.md) | Functional | Must-have | Accept text file uploads via REST API |
| [REQ-F-synthesize-audiobook](../../1-objectives/requirements/REQ-F-synthesize-audiobook.md) | Functional | Must-have | Convert text to MP3 audio via GPU inference; orchestrate synthesis jobs |
| [REQ-F-chapter-split-output](../../1-objectives/requirements/REQ-F-chapter-split-output.md) | Functional | Must-have | Detect and split chapter structure in text |
| [REQ-F-synthesis-progress](../../1-objectives/requirements/REQ-F-synthesis-progress.md) | Functional | Must-have | Report synthesis progress via SSE |
| [REQ-F-disk-space-preflight](../../1-objectives/requirements/REQ-F-disk-space-preflight.md) | Functional | Must-have | Check disk space before synthesis |
| [REQ-F-library-listing](../../1-objectives/requirements/REQ-F-library-listing.md) | Functional | Must-have | List audiobooks in library |
| [REQ-F-audiobook-playback](../../1-objectives/requirements/REQ-F-audiobook-playback.md) | Functional | Must-have | Serve chapter audio for playback |
| [REQ-F-playback-resume](../../1-objectives/requirements/REQ-F-playback-resume.md) | Functional | Must-have | Persist and retrieve playback positions |
| [REQ-F-delete-audiobook](../../1-objectives/requirements/REQ-F-delete-audiobook.md) | Functional | Must-have | Delete audiobook records and files |
| [REQ-F-model-listing](../../1-objectives/requirements/REQ-F-model-listing.md) | Functional | Must-have | List compatible TTS models |
| [REQ-F-model-download](../../1-objectives/requirements/REQ-F-model-download.md) | Functional | Must-have | Manage model downloads with progress |
| [REQ-F-gpu-validation](../../1-objectives/requirements/REQ-F-gpu-validation.md) | Functional | Must-have | Verify NVIDIA GPU + CUDA availability and VRAM |
| [REQ-SEC-localhost-binding](../../1-objectives/requirements/REQ-SEC-localhost-binding.md) | Security | Must-have | Bind server to localhost only |
| [REQ-PORT-linux-windows](../../1-objectives/requirements/REQ-PORT-linux-windows.md) | Portability | Must-have | Run on Linux and Windows |
| [REQ-COMP-foss-only](../../1-objectives/requirements/REQ-COMP-foss-only.md) | Compliance | Must-have | Use only FOSS dependencies |
| [REQ-F-download-audiobook](../../1-objectives/requirements/REQ-F-download-audiobook.md) | Functional | Should-have | Download audiobook as ZIP |
| [REQ-F-voice-language-selection](../../1-objectives/requirements/REQ-F-voice-language-selection.md) | Functional | Should-have | Support voice and language selection per model |
| [REQ-F-job-monitoring](../../1-objectives/requirements/REQ-F-job-monitoring.md) | Functional | Should-have | Expose job status and history |
| [REQ-F-resource-monitoring](../../1-objectives/requirements/REQ-F-resource-monitoring.md) | Functional | Should-have | Report GPU status metrics; expose system resource metrics |
| [REQ-USA-simple-setup](../../1-objectives/requirements/REQ-USA-simple-setup.md) | Usability | Should-have | Single-command startup with URL display |
| [REQ-F-performance-logging](../../1-objectives/requirements/REQ-F-performance-logging.md) | Functional | Should-have | Log synthesis performance metrics |
| [REQ-MNT-modular-ai-layer](../../1-objectives/requirements/REQ-MNT-modular-ai-layer.md) | Maintainability | Should-have | Clean interface boundary for TTS subpackage |
| [REQ-F-model-cache-view](../../1-objectives/requirements/REQ-F-model-cache-view.md) | Functional | Should-have | View cached models and disk usage |
| [REQ-F-model-delete](../../1-objectives/requirements/REQ-F-model-delete.md) | Functional | Should-have | Delete cached models |
| [REQ-F-text-preview](../../1-objectives/requirements/REQ-F-text-preview.md) | Functional | Should-have | Handle ephemeral preview synthesis jobs |
| [REQ-PERF-synthesis-latency](../../1-objectives/requirements/REQ-PERF-synthesis-latency.md) | Performance | Should-have | Meet synthesis performance targets |
| [REQ-F-default-voice-quality](../../1-objectives/requirements/REQ-F-default-voice-quality.md) | Functional | Should-have | Provide good default voice quality |

## Relevant Decisions

| File | Title | Trigger |
|------|-------|---------|
| [DEC-fastapi-backend](../../2-design/decisions/DEC-fastapi-backend.md) | Python + FastAPI Backend | When implementing any backend functionality |
| [DEC-sqlite-metadata](../../2-design/decisions/DEC-sqlite-metadata.md) | SQLite for Metadata Storage | When implementing any data persistence |
| [DEC-single-process](../../2-design/decisions/DEC-single-process.md) | Monolithic Single-Process Architecture | When implementing background processing or adding new services |
| [DEC-sse-progress](../../2-design/decisions/DEC-sse-progress.md) | Server-Sent Events for Real-Time Updates | When implementing progress reporting or live status updates |
| [DEC-tts-as-backend-module](../../2-design/decisions/DEC-tts-as-backend-module.md) | TTS Engine as Backend Submodule | When implementing TTS engine functionality or organizing backend package structure |
| [DEC-python-backend-env](../../2-design/decisions/DEC-python-backend-env.md) | Python Backend Environment Conventions | When installing dependencies, running tests, or adding new Python modules |
| [DEC-default-italian-language](../../2-design/decisions/DEC-default-italian-language.md) | Italian as Default Language for All Adapters | When implementing a new model adapter or modifying adapter default configuration |
| [DEC-text-preprocessing-pipeline](../../2-design/decisions/DEC-text-preprocessing-pipeline.md) | Modular Backend Text-Preprocessing Pipeline | When implementing or modifying the Preprocessing Service, any pipeline stage, or stage configuration |
| [DEC-preprocess-review-flow](../../2-design/decisions/DEC-preprocess-review-flow.md) | Synchronous Preprocess-then-Confirm Synthesis Flow | When implementing the `/preprocess` endpoint or the `/jobs/synthesis` and `/jobs/preview` request handling |
