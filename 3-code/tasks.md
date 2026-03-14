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
| TASK-startup-gpu-check | Integrate GPU validation into FastAPI startup sequence | P1 | Todo | [REQ-F-gpu-validation](../1-objectives/requirements/REQ-F-gpu-validation.md) | TASK-fastapi-app-skeleton, TASK-tts-engine-interface | 2026-03-12 | |
| TASK-sse-endpoint | Implement SSE endpoint with keepalive and event broadcasting | P0 | Todo | - | TASK-fastapi-app-skeleton | 2026-03-12 | |
| TASK-model-service | Implement Model Service and API: list, download, load with VRAM check | P1 | Todo | [REQ-F-model-listing](../1-objectives/requirements/REQ-F-model-listing.md), [REQ-F-model-download](../1-objectives/requirements/REQ-F-model-download.md), [REQ-F-gpu-validation](../1-objectives/requirements/REQ-F-gpu-validation.md) | TASK-tts-engine-interface | 2026-03-12 | |
| TASK-model-download-sse | Wire model download progress to SSE events | P1 | Todo | [REQ-F-model-download](../1-objectives/requirements/REQ-F-model-download.md) | TASK-model-service, TASK-sse-endpoint | 2026-03-12 | |
| TASK-job-service | Implement job queue with background thread processing | P1 | Todo | [REQ-F-synthesize-audiobook](../1-objectives/requirements/REQ-F-synthesize-audiobook.md) | TASK-tts-engine-interface, TASK-sqlite-schema-init | 2026-03-12 | |
| TASK-synthesis-job-api | Implement POST /jobs/synthesis with file upload, validation, and disk space check | P1 | Todo | [REQ-F-upload-text-file](../1-objectives/requirements/REQ-F-upload-text-file.md), [REQ-F-disk-space-preflight](../1-objectives/requirements/REQ-F-disk-space-preflight.md) | TASK-job-service | 2026-03-12 | |
| TASK-job-progress-sse | Wire job progress, completed, and failed events to SSE | P1 | Todo | [REQ-F-synthesis-progress](../1-objectives/requirements/REQ-F-synthesis-progress.md) | TASK-job-service, TASK-sse-endpoint | 2026-03-12 | |
| TASK-library-service-create | Implement audiobook and chapter record creation on synthesis completion | P1 | Todo | [REQ-F-synthesize-audiobook](../1-objectives/requirements/REQ-F-synthesize-audiobook.md), [REQ-F-chapter-split-output](../1-objectives/requirements/REQ-F-chapter-split-output.md) | TASK-job-service, TASK-sqlite-schema-init | 2026-03-12 | |
| TASK-library-api | Implement audiobook list, get, and delete API endpoints with cascade cleanup | P1 | Todo | [REQ-F-library-listing](../1-objectives/requirements/REQ-F-library-listing.md), [REQ-F-delete-audiobook](../1-objectives/requirements/REQ-F-delete-audiobook.md) | TASK-library-service-create | 2026-03-12 | |
| TASK-chapter-audio-streaming | Implement chapter audio streaming with HTTP Range support | P1 | Todo | [REQ-F-audiobook-playback](../1-objectives/requirements/REQ-F-audiobook-playback.md) | TASK-library-api | 2026-03-12 | |
| TASK-playback-position-api | Implement GET and PUT playback position endpoints | P1 | Todo | [REQ-F-playback-resume](../1-objectives/requirements/REQ-F-playback-resume.md) | TASK-sqlite-schema-init | 2026-03-12 | |
| TASK-model-voices-api | Implement GET /models/{id}/voices endpoint for voice and language listing | P2 | Todo | [REQ-F-voice-language-selection](../1-objectives/requirements/REQ-F-voice-language-selection.md) | TASK-model-service | 2026-03-12 | |
| TASK-preview-job-service | Implement preview job API: POST /jobs/preview and GET /jobs/{id}/audio | P2 | Todo | [REQ-F-text-preview](../1-objectives/requirements/REQ-F-text-preview.md) | TASK-job-service | 2026-03-12 | |
| TASK-performance-logging | Record synthesis performance metrics in database on job completion | P2 | Todo | [REQ-F-performance-logging](../1-objectives/requirements/REQ-F-performance-logging.md) | TASK-job-service | 2026-03-12 | |
| TASK-job-monitoring-api | Implement GET /jobs and GET /jobs/{id} with error and performance details | P2 | Todo | [REQ-F-job-monitoring](../1-objectives/requirements/REQ-F-job-monitoring.md) | TASK-performance-logging | 2026-03-12 | |
| TASK-resource-monitoring-api | Implement GET /system/status with CPU, memory, GPU, and loaded model | P2 | Todo | [REQ-F-resource-monitoring](../1-objectives/requirements/REQ-F-resource-monitoring.md) | TASK-tts-engine-interface | 2026-03-12 | |
| TASK-audiobook-download-api | Implement GET /audiobooks/{id}/download as ZIP archive | P2 | Todo | [REQ-F-download-audiobook](../1-objectives/requirements/REQ-F-download-audiobook.md) | TASK-library-api | 2026-03-12 | |
| TASK-model-cache-api | Implement GET /models/cache and DELETE /models/{id}/cache endpoints | P2 | Todo | [REQ-F-model-cache-view](../1-objectives/requirements/REQ-F-model-cache-view.md), [REQ-F-model-delete](../1-objectives/requirements/REQ-F-model-delete.md) | TASK-model-service | 2026-03-12 | |
| TASK-gpu-validator | Implement NVIDIA GPU/CUDA detection and VRAM availability checking | P1 | Todo | [REQ-F-gpu-validation](../1-objectives/requirements/REQ-F-gpu-validation.md) | TASK-python-project-scaffold | 2026-03-14 | Moved from TTS Engine section per DEC-tts-as-backend-module |
| TASK-model-loader | Implement HuggingFace model download, caching, and GPU loading | P1 | Todo | [REQ-F-model-download](../1-objectives/requirements/REQ-F-model-download.md) | TASK-gpu-validator | 2026-03-14 | Moved from TTS Engine section per DEC-tts-as-backend-module |
| TASK-chapter-parser | Implement chapter structure detection and text splitting | P1 | Todo | [REQ-F-chapter-split-output](../1-objectives/requirements/REQ-F-chapter-split-output.md) | TASK-python-project-scaffold | 2026-03-14 | Moved from TTS Engine section per DEC-tts-as-backend-module |
| TASK-synthesizer | Implement text-to-MP3 synthesis with progress callbacks | P1 | Todo | [REQ-F-synthesize-audiobook](../1-objectives/requirements/REQ-F-synthesize-audiobook.md) | TASK-model-loader, TASK-chapter-parser | 2026-03-14 | Moved from TTS Engine section per DEC-tts-as-backend-module |
| TASK-tts-engine-interface | Assemble TTSEngine class with clean public interface | P2 | Todo | [REQ-MNT-modular-ai-layer](../1-objectives/requirements/REQ-MNT-modular-ai-layer.md) | TASK-synthesizer | 2026-03-14 | Moved from TTS Engine section per DEC-tts-as-backend-module |
| TASK-default-voice-config | Configure and document default model, voice, and language (Italian) | P2 | Todo | [REQ-F-default-voice-quality](../1-objectives/requirements/REQ-F-default-voice-quality.md) | TASK-tts-engine-interface | 2026-03-14 | Moved from TTS Engine section per DEC-tts-as-backend-module |

### Frontend

| ID | Task | Priority | Status | Req | Dependencies | Updated | Notes |
|----|------|----------|--------|-----|--------------|---------|-------|
| TASK-vite-dev-proxy | Configure Vite dev server to proxy /api requests to FastAPI | P0 | Done | - | TASK-vue-project-scaffold, TASK-fastapi-app-skeleton | 2026-03-14 | |
| TASK-frontend-sse-client | Implement EventSource SSE client service in Vue | P0 | Todo | - | TASK-sse-endpoint, TASK-vue-project-scaffold | 2026-03-12 | |
| TASK-model-management-view | Implement model management view: list, download with progress, load | P1 | Todo | [REQ-F-model-listing](../1-objectives/requirements/REQ-F-model-listing.md), [REQ-F-model-download](../1-objectives/requirements/REQ-F-model-download.md) | TASK-model-service, TASK-frontend-sse-client | 2026-03-12 | |
| TASK-audiobook-creation-view | Implement audiobook creation view: file upload, trigger, progress display | P1 | Todo | [REQ-F-upload-text-file](../1-objectives/requirements/REQ-F-upload-text-file.md), [REQ-F-synthesis-progress](../1-objectives/requirements/REQ-F-synthesis-progress.md) | TASK-synthesis-job-api, TASK-frontend-sse-client | 2026-03-12 | |
| TASK-library-view | Implement library view: browse audiobooks, delete with confirmation | P1 | Todo | [REQ-F-library-listing](../1-objectives/requirements/REQ-F-library-listing.md), [REQ-F-delete-audiobook](../1-objectives/requirements/REQ-F-delete-audiobook.md) | TASK-library-api | 2026-03-12 | |
| TASK-playback-view | Implement playback view: audio player, chapter navigation, playback resume | P1 | Todo | [REQ-F-audiobook-playback](../1-objectives/requirements/REQ-F-audiobook-playback.md), [REQ-F-playback-resume](../1-objectives/requirements/REQ-F-playback-resume.md) | TASK-chapter-audio-streaming, TASK-playback-position-api | 2026-03-12 | |
| TASK-voice-language-selection-ui | Add voice and language selection to audiobook creation form | P2 | Todo | [REQ-F-voice-language-selection](../1-objectives/requirements/REQ-F-voice-language-selection.md) | TASK-model-voices-api, TASK-audiobook-creation-view | 2026-03-12 | |
| TASK-text-preview-view | Implement text preview view: text input, synthesize, play ephemeral audio | P2 | Todo | [REQ-F-text-preview](../1-objectives/requirements/REQ-F-text-preview.md) | TASK-preview-job-service, TASK-frontend-sse-client | 2026-03-12 | |
| TASK-monitoring-view | Implement monitoring view: job list, error details, resource usage | P2 | Todo | [REQ-F-job-monitoring](../1-objectives/requirements/REQ-F-job-monitoring.md), [REQ-F-resource-monitoring](../1-objectives/requirements/REQ-F-resource-monitoring.md) | TASK-job-monitoring-api, TASK-resource-monitoring-api | 2026-03-12 | |
| TASK-audiobook-download-ui | Add download button to library view | P2 | Todo | [REQ-F-download-audiobook](../1-objectives/requirements/REQ-F-download-audiobook.md) | TASK-audiobook-download-api, TASK-library-view | 2026-03-12 | |
| TASK-model-cache-ui | Add cache view with disk usage and delete to model management | P2 | Todo | [REQ-F-model-cache-view](../1-objectives/requirements/REQ-F-model-cache-view.md), [REQ-F-model-delete](../1-objectives/requirements/REQ-F-model-delete.md) | TASK-model-cache-api, TASK-model-management-view | 2026-03-12 | |

### Deploy & Operations

| ID | Task | Priority | Status | Req | Dependencies | Updated | Notes |
|----|------|----------|--------|-----|--------------|---------|-------|
| TASK-startup-script | Create cross-platform startup script for Linux and Windows | P2 | Todo | [REQ-USA-simple-setup](../1-objectives/requirements/REQ-USA-simple-setup.md), [REQ-PORT-linux-windows](../1-objectives/requirements/REQ-PORT-linux-windows.md) | TASK-fastapi-app-skeleton, TASK-static-file-serving | 2026-03-12 | |
| TASK-setup-documentation | Write setup instructions with dependencies, system requirements, and quickstart | P2 | Todo | [REQ-USA-simple-setup](../1-objectives/requirements/REQ-USA-simple-setup.md) | TASK-startup-script | 2026-03-12 | |

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

### Phase 8: Deployment & Documentation

**Capabilities delivered:**
- Cross-platform startup script for Linux and Windows
- Complete setup documentation with dependencies and system requirements
- 5-or-fewer-commands setup flow

**Tasks:**
1. TASK-startup-script
2. TASK-setup-documentation
