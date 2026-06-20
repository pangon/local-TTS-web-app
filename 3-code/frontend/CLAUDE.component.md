# Frontend

**Responsibility**: User interface, client-side routing, audio playback, and SSE event consumption.

**Technology**: Vue 3 (Composition API), Vite, Vue Router

## Interfaces

- HTTP REST with backend: sends API requests for all user actions (CRUD, job creation, model management)
- SSE with backend: receives real-time progress and status events via `EventSource` API (`/api/v1/events`)
- Audiobook creation review flow (`views/CreateView.vue`, `api/preprocess.ts`, `api/jobs.ts`): a two-step preprocess-then-confirm flow (`DEC-preprocess-review-flow`). Step 1 uploads the selected `.txt` to `POST /api/v1/preprocess` (`preprocessFile`, multipart) and presents the returned normalized text in an **editable** review textarea with before/after char counts; step 2 sends the confirmed text to `POST /api/v1/jobs/synthesis` as JSON (`createSynthesisJob`), forwarding the `language` resolved by `/preprocess` so both calls agree. Synthesis never auto-starts — it requires an explicit "Confirm & Start Synthesis" action (`REQ-USA-normalized-text-review`). The voice/language selector itself is deferred to Phase 6.
- Model listing (`views/ModelsView.vue`, `api/models.ts`): lists `GET /api/v1/models` grouped into **two sections by the `loader_available` flag** (architecture § Adapter Pattern) — first "Available models" (`loader_available = true`, with Download/Load actions and cache-status badges), then "Adapter not yet available" (`loader_available = false`, listed for visibility with a "No adapter" badge and no Download/Load actions). Each section is hidden when empty; the global "No models available" empty state shows only when the list is entirely empty. The per-model license notice for non-FOSS models is a separate Phase 5.2 step (`TASK-model-license-notice-ui`, `DEC-model-license-disclosure`).
- Audio playback (`views/PlaybackView.vue`): uses the native `<audio>` element pointed at the chapter audio URL; chapter navigation is index-based over the sorted chapter list, and the two-level resume bookmark is read on load (seeking on `loadedmetadata`) and persisted best-effort via the playback API service (`api/playback.ts`) on pause/end/chapter-change/unmount, periodically every 20 seconds while playing, and on page navigation/reload/close (`pagehide`/`visibilitychange`, using a `keepalive` fetch so the save survives document teardown).

## Requirements Addressed

| File | Type | Priority | Summary |
|------|------|----------|---------|
| [REQ-F-upload-text-file](../../1-objectives/requirements/REQ-F-upload-text-file.md) | Functional | Must-have | Upload text file for synthesis |
| [REQ-F-synthesis-progress](../../1-objectives/requirements/REQ-F-synthesis-progress.md) | Functional | Must-have | Display synthesis progress in real time |
| [REQ-F-library-listing](../../1-objectives/requirements/REQ-F-library-listing.md) | Functional | Must-have | List audiobooks in library |
| [REQ-F-audiobook-playback](../../1-objectives/requirements/REQ-F-audiobook-playback.md) | Functional | Must-have | Play audiobook audio in browser |
| [REQ-F-playback-resume](../../1-objectives/requirements/REQ-F-playback-resume.md) | Functional | Must-have | Resume playback from saved position |
| [REQ-PORT-linux-windows](../../1-objectives/requirements/REQ-PORT-linux-windows.md) | Portability | Must-have | Run on Linux and Windows |
| [REQ-COMP-foss-only](../../1-objectives/requirements/REQ-COMP-foss-only.md) | Compliance | Must-have | Use only FOSS dependencies |
| [REQ-F-download-audiobook](../../1-objectives/requirements/REQ-F-download-audiobook.md) | Functional | Should-have | Download audiobook as ZIP |
| [REQ-F-voice-language-selection](../../1-objectives/requirements/REQ-F-voice-language-selection.md) | Functional | Should-have | Select voice and language |
| [REQ-F-job-monitoring](../../1-objectives/requirements/REQ-F-job-monitoring.md) | Functional | Should-have | Monitor job status and history |
| [REQ-F-resource-monitoring](../../1-objectives/requirements/REQ-F-resource-monitoring.md) | Functional | Should-have | View system resource usage |
| [REQ-F-text-preview](../../1-objectives/requirements/REQ-F-text-preview.md) | Functional | Should-have | Preview TTS with sample text |
| [REQ-PORT-browser-compat](../../1-objectives/requirements/REQ-PORT-browser-compat.md) | Portability | Should-have | Support major browsers |
| [REQ-USA-normalized-text-review](../../1-objectives/requirements/REQ-USA-normalized-text-review.md) | Usability | Should-have | Review and confirm normalized text before generation |

## Relevant Decisions

| File | Title | Trigger |
|------|-------|---------|
| [DEC-vue3-frontend](../../2-design/decisions/DEC-vue3-frontend.md) | Vue 3 + Vite Frontend | When implementing any frontend functionality |
| [DEC-sse-progress](../../2-design/decisions/DEC-sse-progress.md) | Server-Sent Events for Real-Time Updates | When implementing progress reporting or live status updates |
| [DEC-frontend-dev-env](../../2-design/decisions/DEC-frontend-dev-env.md) | Frontend Development Environment Conventions | When installing dependencies, running tests, building, or adding new frontend modules |
| [DEC-preprocess-review-flow](../../2-design/decisions/DEC-preprocess-review-flow.md) | Synchronous Preprocess-then-Confirm Synthesis Flow | When implementing the audiobook-creation review step or the text-preview inline review |
| [DEC-model-license-disclosure](../../2-design/decisions/DEC-model-license-disclosure.md) | Permit Open-Weight Non-FOSS Models with Frontend License Disclosure | When implementing or modifying the model-listing view (license notice for non-FOSS models) |
