# Backend

**Responsibility**: HTTP request handling, REST API, SSE endpoint, application services (Library, Job, Model, Monitor), SQLite storage, and static file serving.

**Technology**: Python, FastAPI, Uvicorn, SQLite (via `sqlite3` stdlib)

## Interfaces

- HTTP REST + SSE with frontend: serves API endpoints and pushes real-time events
- Python class API with tts-engine: imports and calls `TTSEngine` for GPU inference, model management, and chapter parsing

## Requirements Addressed

| File | Type | Priority | Summary |
|------|------|----------|---------|
| [REQ-F-upload-text-file](../../1-objectives/requirements/REQ-F-upload-text-file.md) | Functional | Must-have | Accept text file uploads via REST API |
| [REQ-F-synthesize-audiobook](../../1-objectives/requirements/REQ-F-synthesize-audiobook.md) | Functional | Must-have | Orchestrate audiobook synthesis jobs |
| [REQ-F-synthesis-progress](../../1-objectives/requirements/REQ-F-synthesis-progress.md) | Functional | Must-have | Report synthesis progress via SSE |
| [REQ-F-disk-space-preflight](../../1-objectives/requirements/REQ-F-disk-space-preflight.md) | Functional | Must-have | Check disk space before synthesis |
| [REQ-F-library-listing](../../1-objectives/requirements/REQ-F-library-listing.md) | Functional | Must-have | List audiobooks in library |
| [REQ-F-audiobook-playback](../../1-objectives/requirements/REQ-F-audiobook-playback.md) | Functional | Must-have | Serve chapter audio for playback |
| [REQ-F-playback-resume](../../1-objectives/requirements/REQ-F-playback-resume.md) | Functional | Must-have | Persist and retrieve playback positions |
| [REQ-F-delete-audiobook](../../1-objectives/requirements/REQ-F-delete-audiobook.md) | Functional | Must-have | Delete audiobook records and files |
| [REQ-F-model-listing](../../1-objectives/requirements/REQ-F-model-listing.md) | Functional | Must-have | List compatible TTS models |
| [REQ-F-model-download](../../1-objectives/requirements/REQ-F-model-download.md) | Functional | Must-have | Manage model downloads with progress |
| [REQ-F-gpu-validation](../../1-objectives/requirements/REQ-F-gpu-validation.md) | Functional | Must-have | Validate GPU/CUDA at startup |
| [REQ-SEC-localhost-binding](../../1-objectives/requirements/REQ-SEC-localhost-binding.md) | Security | Must-have | Bind server to localhost only |
| [REQ-PORT-linux-windows](../../1-objectives/requirements/REQ-PORT-linux-windows.md) | Portability | Must-have | Run on Linux and Windows |
| [REQ-COMP-foss-only](../../1-objectives/requirements/REQ-COMP-foss-only.md) | Compliance | Must-have | Use only FOSS dependencies |
| [REQ-F-download-audiobook](../../1-objectives/requirements/REQ-F-download-audiobook.md) | Functional | Should-have | Download audiobook as ZIP |
| [REQ-F-voice-language-selection](../../1-objectives/requirements/REQ-F-voice-language-selection.md) | Functional | Should-have | Pass voice/language selection to TTS engine |
| [REQ-F-job-monitoring](../../1-objectives/requirements/REQ-F-job-monitoring.md) | Functional | Should-have | Expose job status and history |
| [REQ-F-resource-monitoring](../../1-objectives/requirements/REQ-F-resource-monitoring.md) | Functional | Should-have | Expose system resource metrics |
| [REQ-USA-simple-setup](../../1-objectives/requirements/REQ-USA-simple-setup.md) | Usability | Should-have | Single-command startup with URL display |
| [REQ-F-performance-logging](../../1-objectives/requirements/REQ-F-performance-logging.md) | Functional | Should-have | Log synthesis performance metrics |
| [REQ-F-model-cache-view](../../1-objectives/requirements/REQ-F-model-cache-view.md) | Functional | Should-have | View cached models and disk usage |
| [REQ-F-model-delete](../../1-objectives/requirements/REQ-F-model-delete.md) | Functional | Should-have | Delete cached models |
| [REQ-F-text-preview](../../1-objectives/requirements/REQ-F-text-preview.md) | Functional | Should-have | Handle ephemeral preview synthesis jobs |

## Relevant Decisions

| File | Title | Trigger |
|------|-------|---------|
| [DEC-fastapi-backend](../../2-design/decisions/DEC-fastapi-backend.md) | Python + FastAPI Backend | When implementing any backend functionality |
| [DEC-sqlite-metadata](../../2-design/decisions/DEC-sqlite-metadata.md) | SQLite for Metadata Storage | When implementing any data persistence |
| [DEC-single-process](../../2-design/decisions/DEC-single-process.md) | Monolithic Single-Process Architecture | When implementing background processing or adding new services |
| [DEC-sse-progress](../../2-design/decisions/DEC-sse-progress.md) | Server-Sent Events for Real-Time Updates | When implementing progress reporting or live status updates |
