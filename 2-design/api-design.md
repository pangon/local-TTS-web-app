# API Design

## Overview

RESTful JSON API served by FastAPI (`DEC-fastapi-backend`) on `127.0.0.1` (`REQ-SEC-localhost-binding`). All endpoints are prefixed with `/api/v1/`. Real-time updates use Server-Sent Events (`DEC-sse-progress`). The Vue 3 SPA (`DEC-vue3-frontend`) is the sole consumer.

## Conventions

- **Content types**: JSON for request/response bodies, `multipart/form-data` for file uploads, `audio/mpeg` for audio streaming, `application/zip` for archive downloads, `text/event-stream` for SSE.
- **IDs**: UUIDs for audiobooks, chapters, and jobs. HuggingFace model IDs (e.g., `facebook/mms-tts-eng`) for models, passed as path parameters via `{model_id:path}`.
- **Timestamps**: ISO 8601 UTC with a trailing `Z` (e.g., `2026-03-11T14:30:00Z`). All timestamp fields in API responses use this format. The backend produces it consistently: SQLite column defaults use `strftime('%Y-%m-%dT%H:%M:%SZ', 'now')` and service-layer code uses an equivalent UTC helper, so timestamps coming from either path are interchangeable.
- **Errors**: All error responses use `{"detail": "Human-readable message"}`. Structured fields are added where the UI needs specifics (e.g., disk space errors include `estimated_mb` and `available_mb`). FastAPI's validation errors (422) include field-level details automatically.
- **Currently loaded model**: Synthesis and preview jobs use whichever model is currently loaded. The frontend orchestrates download → load → synthesize. If no model is loaded, job creation returns 409.

## Status Codes

| Code | Usage |
|------|-------|
| 200 | Successful GET, PUT |
| 201 | Resource created (POST /jobs) |
| 202 | Accepted (POST model download — async) |
| 204 | Successful DELETE (no body) |
| 400 | Invalid input (wrong file type, file too large, empty text) |
| 404 | Resource not found |
| 409 | Conflict (no model loaded, cannot delete loaded model, already cached, insufficient disk/VRAM, job not complete) |
| 422 | Validation error (FastAPI automatic) |

---

## Audiobooks

### List Audiobooks

`GET /api/v1/audiobooks`

Returns all audiobooks for the library view (`REQ-F-library-listing`).

**Response 200:**

```json
[
  {
    "id": "uuid",
    "title": "My Book",
    "source_filename": "my-book.txt",
    "model_id": "facebook/mms-tts-eng",
    "voice": "default",
    "language": "it",
    "created_at": "2026-03-11T14:30:00Z",
    "chapter_count": 5,
    "total_duration_seconds": 1830.4
  }
]
```

`total_duration_seconds` is the sum of the audiobook's chapter durations; it is `null` when the audiobook has no chapters with a recorded duration.

### Get Audiobook

`GET /api/v1/audiobooks/{audiobook_id}`

Returns audiobook details with full chapter list (`REQ-F-audiobook-playback`).

**Response 200:**

```json
{
  "id": "uuid",
  "title": "My Book",
  "source_filename": "my-book.txt",
  "model_id": "facebook/mms-tts-eng",
  "voice": "default",
  "language": "it",
  "created_at": "2026-03-11T14:30:00Z",
  "chapters": [
    {"chapter_number": 1, "title": "Chapter 1", "duration_seconds": 120.5, "file_size_bytes": 1932800},
    {"chapter_number": 2, "title": "Chapter 2", "duration_seconds": 98.3, "file_size_bytes": 1572864}
  ]
}
```

`model_id` is the TTS model used to generate the audiobook (shown in the playback view). `file_size_bytes` is the on-disk size of each chapter's MP3 file; it is `null` when the audio file is missing or unreadable.

**Response 404:** Audiobook not found.

### Delete Audiobook

`DELETE /api/v1/audiobooks/{audiobook_id}`

Deletes audiobook record, chapters, playback positions, and audio files on disk (`REQ-F-delete-audiobook`). Confirmation is handled by the frontend before calling this endpoint.

**Response 204:** Deleted successfully.

**Response 404:** Audiobook not found.

### Stream Chapter Audio

`GET /api/v1/audiobooks/{audiobook_id}/chapters/{chapter_number}/audio`

Streams the MP3 file for a specific chapter (`REQ-F-audiobook-playback`). Supports HTTP Range requests for seeking.

**Response 200:** `Content-Type: audio/mpeg`. Supports `Accept-Ranges: bytes`.

**Response 404:** Audiobook or chapter not found.

### Download Audiobook

`GET /api/v1/audiobooks/{audiobook_id}/download`

Downloads all chapter files as a ZIP archive (`REQ-F-download-audiobook`).

**Response 200:** `Content-Type: application/zip`, `Content-Disposition: attachment; filename="<title>.zip"`.

**Response 404:** Audiobook not found.

---

## Playback Position

### Get Playback Position

`GET /api/v1/audiobooks/{audiobook_id}/position`

Returns the two-level bookmark for an audiobook (`REQ-F-playback-resume`).

**Response 200:**

```json
{
  "last_chapter_number": 3,
  "chapters": {
    "1": 120.5,
    "2": 300.0,
    "3": 45.2
  }
}
```

`last_chapter_number` is the audiobook-level bookmark (last active chapter). `chapters` maps chapter numbers to saved timestamps (seconds) — only chapters that have been listened to appear. If the audiobook has never been played, returns `{"last_chapter_number": 1, "chapters": {}}`.

**Response 404:** Audiobook not found.

### Update Playback Position

`PUT /api/v1/audiobooks/{audiobook_id}/position`

Saves both the audiobook-level bookmark and the per-chapter timestamp (`REQ-F-playback-resume`). Called by the frontend on pause, stop, or chapter change, periodically (every 20 seconds) during playback, and when leaving the player (in-app route change, page reload, or tab/browser close). Updates `PlaybackPosition.last_chapter_number` and `ChapterPlaybackPosition` for the given chapter. Unload-triggered saves use a `keepalive` request so they survive document teardown.

**Request:**

```json
{
  "chapter_number": 3,
  "position_seconds": 45.2
}
```

**Response 200:**

```json
{
  "chapter_number": 3,
  "position_seconds": 45.2
}
```

**Response 404:** Audiobook not found.

**Response 422:** Invalid chapter number or position.

---

## Text Preprocessing

### Preprocess Text

`POST /api/v1/preprocess`

Runs the text-normalization pipeline synchronously and returns the normalized, TTS-ready text for the user to review before generation (`DEC-text-preprocessing-pipeline`, `DEC-preprocess-review-flow`, `REQ-USA-normalized-text-review`). Covers Unicode sanitization, layout repair, numeric/symbolic verbalization, and abbreviation expansion (`REQ-F-text-unicode-sanitization`, `REQ-F-text-layout-repair`, `REQ-F-text-numeric-symbolic-verbalization`, `REQ-F-abbreviation-expansion`). Completes within bounded time (`REQ-PERF-preprocessing-overhead`). Uses the currently loaded model to select the model-specific preprocessing profile.

**Request:** `Content-Type: multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | file | Conditional | `.txt` file, UTF-8 encoded, ≤ 2 MB (audiobook path) (`REQ-F-upload-text-file`) |
| `text` | string | Conditional | Raw text input (preview path) |
| `language` | string | No | Output language for verbalization rules (defaults to `it`). Must be a supported language — one with registered preprocessing data. |

Exactly one of `file` or `text` must be provided. An omitted/empty `language` falls back to the default (`it`); an explicitly supplied language that has no registered preprocessing data is rejected (see 400 below) rather than silently passing the text through unchanged, since preprocessing rewrites are language-specific.

**Response 200:**

```json
{
  "normalized_text": "Normalized, TTS-ready text...",
  "language": "it",
  "model_id": "hexgrad/Kokoro-82M",
  "original_char_count": 12873,
  "normalized_char_count": 12010
}
```

`normalized_text` is the exact text that will be synthesized if the user confirms. `model_id` is the currently loaded model whose profile was applied. `original_char_count` / `normalized_char_count` support a before/after review display.

**Response 400:** Invalid file type (not `.txt`), file exceeds 2 MB, empty input, neither/both of `file` and `text` supplied, or an unsupported output `language` (no registered preprocessing data): `{"detail": "Unsupported output language '<code>'. Supported languages: <list>."}`. Language validation is an input check, so it precedes the model-loaded check.

**Response 409:** No model loaded: `{"detail": "No model loaded"}`.

---

## Jobs

### Create Synthesis Job

`POST /api/v1/jobs/synthesis`

Starts audiobook synthesis from the **confirmed normalized text** returned by `POST /preprocess` and approved by the user (`REQ-F-synthesize-audiobook`, `REQ-USA-normalized-text-review`, `DEC-preprocess-review-flow`). The `.txt` upload happens earlier at `/preprocess`; this endpoint receives the reviewed text as JSON and synthesizes **exactly** that text — it does **not** re-run preprocessing. Chapter detection runs on the provided text. Performs disk space preflight check before queuing (`REQ-F-disk-space-preflight`). Uses the currently loaded model.

**Request:** `Content-Type: application/json`

```json
{
  "text": "Confirmed normalized text...",
  "source_filename": "my-book.txt",
  "voice": "if_sara",
  "language": "it"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `text` | string | Yes | Confirmed normalized text to synthesize |
| `source_filename` | string | Yes | Original uploaded filename, used to derive the audiobook title |
| `voice` | string | No | Voice selection (defaults to model default) |
| `language` | string | No | Language selection (defaults to model default) |

**Response 201:**

```json
{
  "id": "uuid",
  "type": "synthesis",
  "status": "queued",
  "progress": 0,
  "created_at": "2026-03-11T14:30:00Z"
}
```

**Response 400:** Empty `text`.

**Response 409:**
- No model loaded: `{"detail": "No model loaded"}`
- Insufficient disk space: `{"detail": "Insufficient disk space", "estimated_mb": 500, "available_mb": 100}`

### Create Preview Job

`POST /api/v1/jobs/preview`

Submits text for ephemeral TTS preview (`REQ-F-text-preview`). Uses the currently loaded model. The submitted `text` is the already-normalized text (the frontend runs it through `POST /preprocess` first, or the user reviews it inline per `REQ-USA-normalized-text-review`, `DEC-preprocess-review-flow`); this endpoint synthesizes exactly the provided `text` and does not re-run preprocessing. Follows the async job pattern: returns a job ID, reports progress via SSE, audio fetched via `GET /jobs/{id}/audio` on completion. Preview audio is not saved to the library.

**Request:**

```json
{
  "text": "Preview this text.",
  "voice": "default",
  "language": "it"
}
```

`voice` and `language` are optional (default to model defaults).

**Response 201:**

```json
{
  "id": "uuid",
  "type": "preview",
  "status": "queued",
  "progress": 0,
  "created_at": "2026-03-11T14:30:00Z"
}
```

**Response 400:** Empty text.

**Response 409:** No model loaded.

### List Jobs

`GET /api/v1/jobs`

Returns all jobs with status and progress (`REQ-F-job-monitoring`).

**Response 200:**

```json
[
  {
    "id": "uuid",
    "type": "synthesis",
    "status": "completed",
    "progress": 100,
    "audiobook_id": "uuid",
    "error_message": null,
    "created_at": "2026-03-11T14:30:00Z",
    "started_at": "2026-03-11T14:30:01Z",
    "completed_at": "2026-03-11T14:35:00Z"
  }
]
```

### Get Job

`GET /api/v1/jobs/{job_id}`

Returns job details including error message and performance metrics (`REQ-F-job-monitoring`, `REQ-F-performance-logging`).

**Response 200:**

```json
{
  "id": "uuid",
  "type": "synthesis",
  "status": "completed",
  "progress": 100,
  "audiobook_id": "uuid",
  "error_message": null,
  "created_at": "2026-03-11T14:30:00Z",
  "started_at": "2026-03-11T14:30:01Z",
  "completed_at": "2026-03-11T14:35:00Z",
  "performance": {
    "total_duration_seconds": 299.5,
    "audio_duration_seconds": 3600.0,
    "real_time_factor": 0.083,
    "peak_gpu_memory_mb": 4096.0,
    "model_id": "facebook/mms-tts-eng"
  }
}
```

`performance` is `null` if the job has not completed successfully. `audiobook_id` is `null` for preview jobs.

**Response 404:** Job not found.

### Get Preview Audio

`GET /api/v1/jobs/{job_id}/audio`

Returns the ephemeral preview audio for a completed preview job (`REQ-F-text-preview`). Fetching the audio deletes the temporary file; subsequent requests for the same job return 404.

**Response 200:** `Content-Type: audio/mpeg`.

**Response 404:** Job not found, not a preview job, or audio already fetched.

**Response 409:** Job not yet completed.

---

## Models

### List Models

`GET /api/v1/models`

Returns compatible HuggingFace TTS models with cache and load status (`REQ-F-model-listing`).

**Response 200:**

```json
[
  {
    "model_id": "facebook/mms-tts-eng",
    "name": "MMS TTS English",
    "is_cached": true,
    "is_loaded": false,
    "loader_available": true,
    "license": "Apache-2.0",
    "license_is_foss": true,
    "license_notice": null
  }
]
```

`loader_available` indicates whether a model-specific adapter is implemented. Models without an adapter cannot be downloaded or loaded — the frontend hides these actions (see architecture § Adapter Pattern).

`license`, `license_is_foss`, and `license_notice` surface each model's usage terms. When `license_is_foss` is `false` (open-weight but research / non-commercial — e.g. `fishaudio/s2-pro`, `bosonai/higgs-audio-v3-tts-4b`), `license_notice` carries a short description of the terms and the frontend model-listing view displays it (`REQ-F-model-listing`; see architecture § Model Licensing & Frontend Disclosure and `DEC-model-license-disclosure`).

### Download Model

`POST /api/v1/models/{model_id:path}/download`

Starts downloading a model to the local cache (`REQ-F-model-download`). Checks disk space before starting. Progress reported via SSE (`download-progress`, `download-completed`, `download-failed` events).

**Response 202:**

```json
{
  "model_id": "facebook/mms-tts-eng",
  "status": "downloading"
}
```

**Response 409:**
- Already cached: `{"detail": "Model already cached"}`
- Insufficient disk space: `{"detail": "Insufficient disk space", "estimated_mb": 2048, "available_mb": 500}`

### Load Model

`POST /api/v1/models/{model_id:path}/load`

Loads a cached model onto the GPU (`REQ-F-gpu-validation`). Synchronous — returns when the model is loaded and ready for inference. Checks VRAM availability before loading.

**Response 200:**

```json
{
  "model_id": "facebook/mms-tts-eng",
  "status": "loaded"
}
```

**Response 404:** Model not cached.

**Response 409:** Insufficient VRAM: `{"detail": "Insufficient VRAM", "required_mb": 4096, "available_mb": 2048}`.

### Get Cached Models

`GET /api/v1/models/cache`

Returns cached models with disk usage (`REQ-F-model-cache-view`).

**Response 200:**

```json
[
  {
    "model_id": "facebook/mms-tts-eng",
    "name": "MMS TTS English",
    "size_mb": 2048.5,
    "is_loaded": true
  }
]
```

### Delete Cached Model

`DELETE /api/v1/models/{model_id:path}/cache`

Deletes a cached model from disk (`REQ-F-model-delete`). Blocked if the model is currently loaded.

**Response 204:** Deleted.

**Response 404:** Model not cached.

**Response 409:** Model is currently loaded — load a different model first.

### Get Model Voices

`GET /api/v1/models/{model_id:path}/voices`

Returns available voices and languages for a model (`REQ-F-voice-language-selection`). The model must be cached (voices are read from model metadata).

**Response 200:**

```json
{
  "voices": ["default", "voice_a", "voice_b"],
  "languages": ["en", "it", "fr"],
  "default_voice": "default",
  "default_language": "it"
}
```

**Response 404:** Model not found or not cached.

---

## System

### Get System Status

`GET /api/v1/system/status`

Returns current system resource usage and loaded model information (`REQ-F-resource-monitoring`).

**Response 200:**

```json
{
  "cpu_percent": 45.2,
  "memory_percent": 62.1,
  "memory_used_mb": 8192,
  "memory_total_mb": 16384,
  "gpu": {
    "name": "NVIDIA RTX 3080",
    "utilization_percent": 80.5,
    "vram_used_mb": 4096,
    "vram_total_mb": 10240
  },
  "loaded_model": "facebook/mms-tts-eng"
}
```

`loaded_model` is `null` if no model is loaded. `gpu` reflects real-time NVIDIA GPU metrics.

---

## Server-Sent Events

### Event Stream

`GET /api/v1/events`

Single SSE endpoint for all real-time server-to-client updates (`DEC-sse-progress`). The client connects once and filters events by type. Served via FastAPI `StreamingResponse` with `text/event-stream` content type. The Vue frontend consumes events using the browser `EventSource` API, which handles automatic reconnection on connection loss.

The server sends periodic `:keepalive` comments to detect stale connections.

### Event Types

#### `job-progress`

Sent periodically during synthesis or preview processing (`REQ-F-synthesis-progress`).

```
event: job-progress
data: {"job_id": "uuid", "type": "synthesis", "status": "processing", "progress": 42}
```

#### `job-completed`

Sent when a synthesis or preview job finishes successfully.

```
event: job-completed
data: {"job_id": "uuid", "type": "synthesis", "audiobook_id": "uuid"}
```

For preview jobs, `audiobook_id` is `null`.

#### `job-failed`

Sent when a job fails.

```
event: job-failed
data: {"job_id": "uuid", "type": "synthesis", "error_message": "Out of VRAM"}
```

#### `download-progress`

Sent during model download (`REQ-F-model-download`).

```
event: download-progress
data: {"model_id": "facebook/mms-tts-eng", "progress": 65}
```

#### `download-completed`

Sent when a model download finishes successfully.

```
event: download-completed
data: {"model_id": "facebook/mms-tts-eng"}
```

#### `download-failed`

Sent when a model download fails.

```
event: download-failed
data: {"model_id": "facebook/mms-tts-eng", "error_message": "Network error"}
```

---

## Requirement Traceability

| Requirement | Priority | Endpoint(s) |
|-------------|----------|-------------|
| `REQ-F-upload-text-file` | Must-have | `POST /preprocess` (file upload) |
| `REQ-F-synthesize-audiobook` | Must-have | `POST /jobs/synthesis` |
| `REQ-F-chapter-split-output` | Must-have | `GET /audiobooks/{id}` (chapter list) |
| `REQ-F-synthesis-progress` | Must-have | `GET /events` (job-progress, job-completed, job-failed) |
| `REQ-F-disk-space-preflight` | Must-have | `POST /jobs/synthesis` (preflight check) |
| `REQ-F-library-listing` | Must-have | `GET /audiobooks` |
| `REQ-F-audiobook-playback` | Must-have | `GET /audiobooks/{id}`, `GET .../chapters/{num}/audio` |
| `REQ-F-playback-resume` | Must-have | `GET /audiobooks/{id}/position`, `PUT /audiobooks/{id}/position` |
| `REQ-F-delete-audiobook` | Must-have | `DELETE /audiobooks/{id}` |
| `REQ-F-model-listing` | Must-have | `GET /models` |
| `REQ-F-model-download` | Must-have | `POST /models/{id}/download`, `GET /events` (download-progress) |
| `REQ-F-gpu-validation` | Must-have | `POST /models/{id}/load` (VRAM check) |
| `REQ-SEC-localhost-binding` | Must-have | Server binds to `127.0.0.1` (not API-specific) |
| `REQ-PORT-linux-windows` | Must-have | Cross-platform (standard HTTP, not API-specific) |
| `REQ-COMP-foss-only` | Must-have | Dependency selection (not API-specific) |
| `REQ-F-download-audiobook` | Should-have | `GET /audiobooks/{id}/download` |
| `REQ-F-voice-language-selection` | Should-have | `GET /models/{id}/voices`, `POST /jobs/synthesis`, `POST /jobs/preview` |
| `REQ-F-job-monitoring` | Should-have | `GET /jobs`, `GET /jobs/{id}` |
| `REQ-F-resource-monitoring` | Should-have | `GET /system/status` |
| `REQ-USA-simple-setup` | Should-have | Server startup (not API-specific) |
| `REQ-F-performance-logging` | Should-have | `GET /jobs/{id}` (performance field) |
| `REQ-MNT-modular-ai-layer` | Should-have | Architecture concern (not API-specific) |
| `REQ-F-model-cache-view` | Should-have | `GET /models/cache` |
| `REQ-F-model-delete` | Should-have | `DELETE /models/{id}/cache` |
| `REQ-F-text-preview` | Should-have | `POST /jobs/preview`, `GET /jobs/{id}/audio` |
| `REQ-PERF-synthesis-latency` | Should-have | Implementation concern (not API-specific) |
| `REQ-F-default-voice-quality` | Should-have | `GET /models/{id}/voices` (default_voice, default_language) |
| `REQ-PORT-browser-compat` | Should-have | Frontend concern (EventSource API) |
| `REQ-F-text-unicode-sanitization` | Must-have | `POST /preprocess` |
| `REQ-F-text-layout-repair` | Must-have | `POST /preprocess` |
| `REQ-F-text-numeric-symbolic-verbalization` | Must-have | `POST /preprocess` |
| `REQ-F-abbreviation-expansion` | Should-have | `POST /preprocess` |
| `REQ-MNT-preprocessing-pipeline` | Should-have | `POST /preprocess` (pipeline structure; not API-specific) |
| `REQ-PERF-preprocessing-overhead` | Should-have | `POST /preprocess` (synchronous latency bound) |
| `REQ-USA-normalized-text-review` | Should-have | `POST /preprocess`, `POST /jobs/synthesis` (confirmed text) |

## Design Risks

No unverified high-risk assumptions remain. The `GET /models/{id}/voices` endpoint will likely need model-specific adapters due to varying voice/language metadata formats across HuggingFace TTS models (see `ASM-huggingface-models-available` verification notes).
