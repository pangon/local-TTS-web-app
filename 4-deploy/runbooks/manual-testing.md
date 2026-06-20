# Runbook: Manual Testing

## Overview

Step-by-step instructions to build, run, and manually test the Local TTS Web App. This runbook is updated incrementally as new phases are completed.

**Current coverage:** Phases 1-5 (Project Scaffolding, TTS Engine Foundation, Model Management End-to-End, Model Adapter Abstraction & Loaders [Phase 3.1], Audiobook Synthesis End-to-End, Library & Playback) and Phase 5.1 (Text Preprocessing & Normalized-Text Review)

> **API base path:** all REST and SSE endpoints are mounted under `/api/v1` (e.g. `http://127.0.0.1:8000/api/v1/preprocess`, SSE at `/api/v1/events`). The Phase 5.1 procedures below use the full `/api/v1/...` paths.

## Prerequisites

- Python >= 3.10
- Node.js ^20.19.0 or >= 22.12.0 (managed via nvm)
- NVIDIA GPU with CUDA drivers (required for TTS inference; GPU validation runs at startup)
- ffmpeg installed and on PATH (required for MP3 encoding)
- espeak-ng installed and on PATH (required for non-English TTS with Kokoro; install via `sudo apt-get install espeak-ng` on Debian/Ubuntu)
- Git (to clone the repository)

## Environment Setup

### Backend

```bash
cd 3-code/backend
python3 -m venv .venv
. .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

### Frontend

```bash
cd 3-code/frontend
nvm use                       # picks up .nvmrc (Node 22)
npm install
```

## Running Tests

### Backend Tests

```bash
cd 3-code/backend
. .venv/bin/activate
pytest
```

Expected outcome: all tests pass. Tests cover GPU validator, model loader, chapter parser, synthesizer, TTS engine interface, SSE endpoint, model service/API, database initialization, static file serving, startup checks, app scaffold, job service, synthesis job API (now a JSON `{text, source_filename, voice?, language?}` contract — empty-text 400, no-model 409, disk preflight from text length, verbatim passthrough with no re-preprocessing), library service (audiobook/chapter persistence and chapter audio path resolution), the library API (list/get/delete with cascade cleanup and chapter audio streaming with HTTP Range support), the playback position API (two-level GET/PUT bookmark, defaults, 404/422 handling), SSE event wiring for job progress/completed/failed, the model adapter registry/protocol (`has_adapter`/`get_adapter`, `loader_available` flag), the Kokoro and Qwen3-TTS adapters (including ISO 639-1 → model-specific language-code mapping, e.g. `it`→`i`/`Italian`), and the text-preprocessing pipeline — the pipeline skeleton (Stage protocol + registry, Pipeline runner, language/model profile resolution, domain-dictionary loader), the five concrete stages in isolation (Unicode sanitization, layout repair, numeric/symbolic verbalization, abbreviation expansion, sentence segmentation — one sentence per line, run last), and the `POST /preprocess` endpoint (file or text input, validation/no-model errors, before/after counts, latency-bound smoke guards).

### Frontend Tests

```bash
cd 3-code/frontend
nvm use
npm run test:unit
```

Expected outcome: all tests pass. Tests cover Vue app rendering, router configuration, Vite proxy config, SSE client composable, model API service, ModelsView component, the preprocess API service (`preprocessFile`, multipart upload, 400/409 handling), the jobs API service (JSON synthesis-job creation, disk-space error fields, error handling), CreateView component (the two-step preprocess-then-confirm flow: file validation, "Preprocess & Review" busy state, normalized-text review textarea with before/after char counts, "Confirm & Start Synthesis" sending the exact reviewed text, progress display, SSE event handling, form reset), the audiobooks API service (list/get/delete, chapter audio URL helper), the playback API service (get/save position, with the `keepalive` flag for unload saves), LibraryView component (listing with total chapter duration, empty state, inline delete confirmation, error handling), and PlaybackView component (chapter navigation, resume seek, TTS model and per-chapter file-size display, and bookmark persistence on pause/chapter-change, every 20 seconds while playing, and on page navigation/reload/close).

### Frontend Type Check

```bash
cd 3-code/frontend
npm run type-check
```

Expected outcome: no type errors.

## Building the Frontend for Production

```bash
cd 3-code/frontend
nvm use
npm run build
```

Expected outcome: production bundle created in `3-code/frontend/dist/`.

## Starting the Application

### Development Mode (two terminals)

**Terminal 1 — Backend:**

```bash
cd 3-code/backend
. .venv/bin/activate
python -m local_tts
```

Expected outcome: prints `Starting Local TTS Web App at http://127.0.0.1:8000` and starts serving.

**Terminal 2 — Frontend dev server:**

```bash
cd 3-code/frontend
nvm use
npm run dev
```

Expected outcome: Vite dev server starts (default `http://localhost:5173`), proxying `/api` requests to `http://127.0.0.1:8000`.

### Production Mode (single process)

Build the frontend first (see above), then:

```bash
cd 3-code/backend
. .venv/bin/activate
python -m local_tts
```

Expected outcome: FastAPI serves the Vue static build at `http://127.0.0.1:8000`. The SPA fallback serves `index.html` for client-side routes.

## Manual Test Procedures

### Phase 1: Project Scaffolding & Dev Environment

#### 1.1 Backend starts and binds to localhost

1. Start the backend (see above).
2. Verify the console prints the startup URL with `127.0.0.1`.
3. Open `http://127.0.0.1:8000/api/v1/events` in a browser — should establish an SSE connection (event stream content type).
4. Verify the app is NOT accessible from other machines on the network (bound to localhost only).

Expected outcome: backend runs, bound to localhost.

#### 1.2 SQLite database initializes on startup

1. Start the backend.
2. Check that `3-code/backend/data/local_tts.db` is created (or the path configured via `LOCAL_TTS_DATA_DIR`).
3. Open the database with `sqlite3` and verify tables exist: `SELECT name FROM sqlite_master WHERE type='table';`

Expected outcome: database file created with the full schema (audiobooks, chapters, playback_positions, jobs, models tables).

#### 1.3 Frontend dev proxy works

1. Start both backend and frontend dev server.
2. Open the Vite dev server URL (`http://localhost:5173`).
3. Open browser DevTools Network tab. Navigate within the app — API calls to `/api/*` should be proxied to the backend (status 200, not 404).

Expected outcome: frontend fetches data from backend via Vite proxy.

#### 1.4 Production static serving works

1. Build the frontend (`npm run build`).
2. Start the backend only.
3. Open `http://127.0.0.1:8000` in a browser.
4. Verify the Vue app loads.
5. Navigate to a client-side route (e.g., `/models`) and refresh — should still load the app (SPA fallback).

Expected outcome: FastAPI serves the Vue production build as static files.

### Phase 2: TTS Engine Foundation

#### 2.1 GPU validation at startup

1. Start the backend on a machine **with** an NVIDIA GPU and CUDA.
2. Check the startup logs — should log successful GPU detection with device name and VRAM.
3. Start the backend on a machine **without** a GPU (or with `CUDA_VISIBLE_DEVICES=""`).
4. Check the startup logs — should log a clear warning that no CUDA GPU was found.

Expected outcome: GPU availability is validated and reported at startup.

#### 2.2 ffmpeg validation at startup

1. Start the backend with ffmpeg installed and on PATH.
2. Check startup logs — should log ffmpeg availability.
3. Temporarily rename/remove ffmpeg from PATH, then start the backend.
4. Check startup logs — should log a clear error that ffmpeg is not found.

Expected outcome: ffmpeg availability is validated and reported at startup.

### Phase 3: Model Management End-to-End

#### 3.1 SSE connection

1. Start the backend.
2. Open the frontend (dev or production mode).
3. Open browser DevTools Network tab, filter by EventSource/SSE.
4. Verify an SSE connection is established to `/api/v1/events`.
5. Verify keepalive events arrive periodically.

Expected outcome: SSE connection established with keepalive heartbeat.

#### 3.2 Model listing

1. Open the app and navigate to the Models page.
2. Verify a list of available TTS models is displayed.
3. Each model should show its name and cache status (whether it's already downloaded).

Expected outcome: models are listed with cache status indicators.

#### 3.3 Model download with progress

1. On the Models page, find a model that is not yet cached.
2. Click the download button.
3. Verify a progress bar appears and updates in real time via SSE.
4. Wait for download to complete — status should update to "cached".

Expected outcome: model downloads with real-time progress feedback.

#### 3.4 Model loading with VRAM check

1. On the Models page, find a cached model.
2. Click the load button.
3. Verify the model loads onto the GPU (status updates to "loaded").
4. If VRAM is insufficient, verify a clear error message is shown.

Expected outcome: model loads onto GPU with VRAM validation.

### Phase 3.1: Model Adapter Abstraction & Loaders

Phase 3.1 introduces the model adapter layer: each model in the compatible list is annotated with a `loader_available` flag indicating whether a concrete adapter is registered for it. Models **without** an adapter cannot be downloaded or loaded and are surfaced as such in the UI. Adapters currently implemented: **Kokoro-82M** (`hexgrad/Kokoro-82M`) and **Qwen3-TTS** (`Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice`).

#### 3.1.1 `loader_available` exposed by the API

1. Start the backend.
2. Request the model list: `curl http://127.0.0.1:8000/api/v1/models`.
3. Verify each entry includes a `loader_available` boolean field.
4. Verify `loader_available` is `true` for `hexgrad/Kokoro-82M` and `Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice`, and `false` for models without an adapter (e.g. `coqui/XTTS-v2`, `ResembleAI/chatterbox`).

Expected outcome: the `GET /models` response reports adapter availability per model.

#### 3.1.2 Models without an adapter are disabled in the UI

1. Open the app and navigate to the Models page.
2. Find a model whose `loader_available` is `false` (e.g. XTTS-v2, Chatterbox).
3. Verify a "No adapter" badge is shown for that model.
4. Verify **no** Download or Load button is rendered for it — the model cannot be downloaded or loaded from the UI.

Expected outcome: models lacking an adapter are clearly marked and their actions are hidden.

#### 3.1.3 Models with an adapter remain fully actionable

1. On the Models page, find an adapter-backed model (Kokoro-82M or Qwen3-TTS).
2. Verify **no** "No adapter" badge is shown.
3. Verify the Download button appears when the model is not cached, and the Load button appears once cached (per Phase 3 tests 3.3 and 3.4).

Expected outcome: adapter-backed models expose the normal download/load workflow.

#### 3.1.4 Adapter-driven inference (Kokoro-82M)

**Prerequisite:** `espeak-ng` must be installed and on PATH for non-English Kokoro synthesis (see Prerequisites). Download and load `hexgrad/Kokoro-82M` first (Phase 3 tests).

1. With Kokoro loaded, run a short synthesis (Phase 4 workflow, or a preview once available).
2. Verify synthesis produces real audio rather than a placeholder — the generated MP3 plays intelligible speech.
3. By default, synthesis uses an Italian voice (`if_sara` or `im_nicola`) per `DEC-default-italian-language`.

Expected outcome: the Kokoro adapter performs actual TTS inference through the `ModelAdapter` interface.

#### 3.1.5 Adapter-driven inference (Qwen3-TTS)

**Prerequisite:** Download and load `Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice` first.

1. With Qwen3-TTS loaded, run a short synthesis.
2. Verify synthesis produces real audio (intelligible speech), using the Italian default per `DEC-default-italian-language`.

Expected outcome: the Qwen3-TTS adapter performs actual TTS inference through the `ModelAdapter` interface.

### Phase 4: Audiobook Synthesis End-to-End

**Prerequisite:** A TTS model must be downloaded and loaded before testing synthesis. Complete Phase 3 tests (model download and load) first.

#### 4.1 Navigate to Create view

1. Open the app and click "Create" in the navigation bar.
2. Verify the URL is `/create` and the page shows "Create Audiobook" heading.
3. Verify a file input is displayed with the label "Select a .txt file (UTF-8, max 2 MB)".
4. Verify the "Start Synthesis" button is present but disabled (no file selected yet).

Expected outcome: Create view loads with file input and disabled submit button.

#### 4.2 File upload validation

1. On the Create page, try selecting a non-.txt file (e.g., a `.pdf` or `.jpg`).
2. Verify an error message appears: "Only .txt files are accepted".
3. Verify the "Start Synthesis" button remains disabled.
4. Select a `.txt` file larger than 2 MB.
5. Verify an error message appears indicating the file exceeds the 2 MB size limit, showing the actual file size.
6. Select a valid `.txt` file under 2 MB.
7. Verify the file name and size (in KB) are displayed below the input.
8. Verify the "Start Synthesis" button becomes enabled.

Expected outcome: invalid files are rejected with clear error messages; valid files enable the submit button.

#### 4.3 Synthesis without a loaded model

1. Ensure no model is loaded (restart the backend without loading a model, or unload the current model).
2. Select a valid `.txt` file and click "Start Synthesis".
3. Verify an error message appears indicating no model is loaded (`"No model loaded"`).
4. Verify the file input remains enabled so the user can retry.

Expected outcome: synthesis is rejected with a clear error when no model is loaded.

#### 4.4 Submit synthesis job with progress

1. Ensure a TTS model is downloaded and loaded (Phase 3 prerequisite).
2. Select a valid `.txt` file and click "Start Synthesis".
3. Verify the button text changes to "Submitting..." briefly.
4. Verify a progress section appears below the form with:
   - Status label showing "queued" (gray) initially.
   - A progress bar starting at 0%.
5. Verify the file input becomes disabled while the job is active.
6. Verify the status transitions to "processing" (blue) and the progress bar updates in real time via SSE.
7. Open browser DevTools Network tab, filter by EventSource — verify `job-progress` SSE events are received with incrementing progress values.

Expected outcome: synthesis job is created, progress updates arrive via SSE, and the UI reflects real-time status.

#### 4.5 Synthesis completes successfully

1. Wait for the synthesis job started in test 4.4 to complete.
2. Verify the status changes to "completed" (green).
3. Verify a success message appears: "Audiobook created successfully!".
4. Verify the progress bar is replaced by the success message.
5. Verify a "New Audiobook" button appears.
6. Open browser DevTools — verify a `job-completed` SSE event was received containing an `audiobook_id`.

Expected outcome: job completes, audiobook is persisted, and the UI shows success state.

#### 4.6 Audiobook persisted in database

1. After a successful synthesis (test 4.5), open the SQLite database.
2. Verify a new row exists in the `audiobook` table with the correct title (derived from the source filename, e.g., `"my-book.txt"` becomes `"my book"`).
3. Verify chapter rows exist in the `chapter` table linked to the audiobook by `audiobook_id`, with sequential `chapter_number` values.
4. Verify the `job` table has a row with `status = 'completed'` and `audiobook_id` set to the new audiobook's ID.
5. Verify audio files exist on disk under `data/audiobooks/<audiobook_id>/`.

Expected outcome: audiobook, chapter records, and audio files are correctly persisted.

#### 4.7 Reset form for new audiobook

1. After a completed or failed job, click the "New Audiobook" button.
2. Verify the form resets: file input is cleared, progress section disappears, and the "Start Synthesis" button is disabled again.
3. Select a new file — verify the form works as in test 4.2.

Expected outcome: form resets cleanly for creating another audiobook.

#### 4.8 Synthesis failure handling

1. Trigger a synthesis failure (e.g., by providing a file that causes an error, or by simulating a GPU OOM condition).
2. Verify the status changes to "failed" (red).
3. Verify the error message from the backend is displayed.
4. Verify a `job-failed` SSE event was received in DevTools.
5. Verify the "New Audiobook" button appears for retry.
6. Verify no audiobook record was created in the database for the failed job.

Expected outcome: failures are reported clearly; no partial audiobook records remain.

#### 4.9 Disk space preflight check

1. Trigger a scenario where insufficient disk space is available (this may require testing with a nearly full disk or mocking the check).
2. Select a valid `.txt` file and click "Start Synthesis".
3. Verify a 409 error is returned with a message indicating insufficient disk space, showing estimated and available MB values.
4. Verify the file input remains enabled so the user can retry.

Expected outcome: disk space is checked before synthesis begins; clear error shown if insufficient.

### Phase 5: Library & Playback

**Prerequisite:** At least one audiobook must exist. Complete a Phase 4 synthesis first (or use a database that already contains audiobooks). The Library is the app's home route (`/`).

#### 5.1 Library lists audiobooks

1. Open the app — it opens on the Library view (`/`), also reachable via the "Library" nav link.
2. Verify each generated audiobook is listed with its title, creation date/time (localized), chapter count (e.g. "3 chapters", or "1 chapter" for a single-chapter book), and the total duration of its chapters (e.g. "1h 02m", "2m 05s").
3. Verify an audiobook whose chapters have no recorded duration shows no duration segment (the chapter count is the last item on the meta line).
4. Cross-check against the API: `curl http://127.0.0.1:8000/api/v1/audiobooks` returns a JSON array; each entry includes `id`, `title`, `source_filename`, `model_id`, `voice`, `language`, `created_at`, `chapter_count`, and `total_duration_seconds` (the summed chapter duration, or `null` when no chapter has a recorded duration).

Expected outcome: all audiobooks are listed with title, date, chapter count, and total duration (REQ-F-library-listing).

#### 5.2 Empty library state

1. Start with a fresh database (no audiobooks), or delete all audiobooks (test 5.7).
2. Open the Library view.
3. Verify the message "No audiobooks yet. Create one from the Create tab." is shown instead of a list.

Expected outcome: a clear empty state is shown when no audiobooks exist.

#### 5.3 Open an audiobook for playback

1. On the Library view, click an audiobook row (the title/meta area is a link).
2. Verify the URL becomes `/playback/<audiobook_id>` and the playback view shows the audiobook title and a "← Library" back link.
3. Verify the TTS model used to generate the audiobook is shown under the title (e.g. "Model: hexgrad/Kokoro-82M").
4. Verify an `<audio>` player with native controls is displayed.
5. Verify the current chapter's title is shown above the player ("now playing"), followed by the chapter's audio file size on disk (e.g. "2.0 MB").

Expected outcome: the playback view loads the selected audiobook with an audio player, the generating TTS model, and the current chapter's file size (REQ-F-audiobook-playback).

#### 5.4 Chapter audio streams with Range support

1. With the playback view open, press play on the audio control and verify intelligible speech plays.
2. Seek within the track (drag the progress bar) and verify playback jumps without re-downloading from the start.
3. Inspect the request: `curl -s -D - -o /dev/null -H "Range: bytes=0-1023" http://127.0.0.1:8000/api/v1/audiobooks/<id>/chapters/1/audio`.
4. Verify the response status is `206 Partial Content`, with `Content-Range`, `Accept-Ranges: bytes`, and `Content-Type: audio/mpeg` headers, and **no** `Content-Disposition: attachment` header (audio is served inline).
5. Verify an out-of-range request (`Range: bytes=99999999-`) returns `416 Range Not Satisfiable`.

Expected outcome: chapter audio is streamed inline and honours HTTP Range requests for seeking (REQ-F-audiobook-playback).

#### 5.5 Chapter navigation (multi-chapter audiobook)

1. Open an audiobook with more than one chapter.
2. Verify a chapter navigation bar appears with "‹ Previous" / "Next ›" buttons and a "Chapter X of N" indicator, plus a clickable chapter list below the player.
3. Verify each chapter row in the list shows the chapter title and its audio file size on disk (e.g. "2.0 MB", "812 KB").
4. Verify "‹ Previous" is disabled on the first chapter and "Next ›" is disabled on the last.
5. Click "Next ›" — verify the player loads the next chapter, the "now playing" title updates, and the active chapter in the list is highlighted.
6. Click a chapter directly in the list — verify playback switches to that chapter.
7. Open a single-chapter audiobook and verify the navigation bar and chapter list are **not** shown (the single chapter's file size still appears next to the "now playing" title, per test 5.3).
8. Cross-check against the API: `curl http://127.0.0.1:8000/api/v1/audiobooks/<id>` returns the `model_id` and a `chapters` array where each entry includes `chapter_number`, `title`, `duration_seconds`, and `file_size_bytes` (the on-disk MP3 size, or `null` when the file is missing).

Expected outcome: chapters can be navigated via buttons and the chapter list, each showing its file size; navigation is hidden for single-chapter books.

#### 5.6 Playback resume (two-level bookmark)

1. Open a multi-chapter audiobook, play chapter 2 for a few seconds, then pause (or navigate to another chapter, or leave the view).
2. Verify the position is saved: `curl http://127.0.0.1:8000/api/v1/audiobooks/<id>/position` returns `last_chapter_number` equal to the chapter you were on and a `chapters` object mapping chapter numbers (as strings) to saved second offsets.
3. Navigate away (back to Library) and reopen the same audiobook.
4. Verify it reopens on the last active chapter, and once the audio metadata loads, the player seeks to the saved timestamp within that chapter.
5. For a never-played audiobook, verify `GET …/position` returns `{"last_chapter_number": 1, "chapters": {}}` and the view starts at the first chapter at 0:00.

The position is saved on pause/end/chapter-change, **and** through these additional triggers:

6. **Periodic save while playing:** start playback and let it run without pausing. Open DevTools Network tab (filter `position`) and verify a `PUT …/position` fires roughly every 20 seconds while audio is playing. Re-query `GET …/position` and confirm the saved offset advances. Pause and verify the periodic `PUT`s stop.
7. **Save on in-app navigation:** while playing, click the "← Library" link (or another nav section). Verify a `PUT …/position` is sent as the view unmounts, and reopening the audiobook resumes at that point.
8. **Save on reload/close:** while playing, reload the page (or close the tab). In DevTools, verify a final `PUT …/position` is sent during unload (it appears as a `keepalive`/`fetch` request that survives teardown). Reopen the audiobook and confirm it resumes near where playback was, not from the earlier pause point.

Expected outcome: playback resumes from the last chapter and per-chapter timestamp; the position is persisted not only on pause/chapter-change but also periodically during playback and when navigating away, reloading, or closing the tab (REQ-F-playback-resume).

#### 5.7 Delete audiobook with confirmation

1. On the Library view, click "Delete" on an audiobook row.
2. Verify an inline confirmation appears in that row: `Delete "<title>"?` with "Confirm" and "Cancel" buttons.
3. Click "Cancel" — verify the row returns to its normal state and nothing is deleted.
4. Click "Delete" again, then "Confirm" — verify the button shows "Deleting…" briefly and the row disappears from the list.
5. Verify the records are gone: the audiobook no longer appears in `GET /api/v1/audiobooks`, and `GET /api/v1/audiobooks/<id>` returns `404`.
6. Verify cascade cleanup: the chapter rows are removed and the audio files under `data/audiobooks/<id>/` are deleted from disk.

Expected outcome: deletion requires confirmation and cascades to chapter records and audio files (REQ-F-delete-audiobook).

#### 5.8 Delete error handling

1. Trigger a delete on an audiobook that no longer exists (e.g. delete it via the API in another terminal first, then confirm the delete in a stale UI).
2. Verify the backend returns `404` and the UI shows an error message ("Failed to delete audiobook") without crashing.

Expected outcome: failed deletions surface a clear error and leave the UI usable.

### Phase 5.1: Text Preprocessing & Normalized-Text Review

Phase 5.1 inserts a **preprocess-then-confirm** step into audiobook creation (`DEC-preprocess-review-flow`). Raw input is normalized by a modular, CPU-only pipeline (`DEC-text-preprocessing-pipeline`) of four stages — Unicode sanitization → layout repair → numeric/symbolic verbalization → abbreviation expansion — and the user reviews (and may edit) the normalized text before any GPU time is spent. Synthesis then reads **exactly** the confirmed text, with no second normalization pass.

The pipeline applies the **currently loaded model's** profile and defaults to the Italian language profile (`it`, per `DEC-default-italian-language`). Verbalization examples below assume the Italian default.

**Prerequisite:** a TTS model must be downloaded **and loaded** (Phase 3 tests). `POST /preprocess` and `POST /jobs/synthesis` both return `409` when no model is loaded.

#### 5.1.1 `POST /preprocess` with an uploaded file

1. Create a small UTF-8 `.txt` file, e.g. `printf 'Il costo è 1.234,56 €.\n' > sample.txt`.
2. Call the endpoint:
   `curl -s -F "file=@sample.txt" http://127.0.0.1:8000/api/v1/preprocess`
3. Verify the JSON response contains `normalized_text`, `language` (`"it"` by default), `model_id` (the loaded model), `original_char_count`, and `normalized_char_count`.
4. Verify `normalized_text` is the cleaned/verbalized text (e.g. the amount is spelled out in Italian words), not the raw input.

Expected outcome: the endpoint returns the normalized, TTS-ready text plus before/after character counts (REQ-USA-normalized-text-review, REQ-F-upload-text-file).

#### 5.1.2 `POST /preprocess` with raw text

1. Call with the `text` form field instead of a file:
   `curl -s -F "text=Pagina 3 di 10" -F "language=it" http://127.0.0.1:8000/api/v1/preprocess`
2. Verify the response shape matches 5.1.1 and `language` echoes the requested `it`.

Expected outcome: raw text is accepted (the preview path) and normalized with the same contract as the file path.

#### 5.1.3 Input validation and "no model loaded"

With a model loaded, verify each of the following returns `400` with a clear `detail`:

1. Non-`.txt` upload: `curl -s -o /dev/null -w "%{http_code}\n" -F "file=@image.png" http://127.0.0.1:8000/api/v1/preprocess` → `400` ("only .txt files are accepted").
2. File over 2 MB → `400` (size limit, reports byte count).
3. Non-UTF-8 file → `400` ("not valid UTF-8").
4. Empty / whitespace-only input (file or `text`) → `400`.
5. Both `file` **and** `text` provided → `400` ("exactly one of 'file' or 'text'").
6. Neither `file` nor `text` provided → `400`.

Then unload the model (or restart the backend without loading one) and repeat 5.1.1:

7. Verify the response is `409` with `detail` `"No model loaded"`. (Input validation runs **before** the model check, matching `POST /jobs/synthesis`.)

Expected outcome: malformed input is rejected with 400 before synthesis; preprocessing is refused with 409 when no model is loaded.

#### 5.1.4 Unicode sanitization stage (REQ-F-text-unicode-sanitization)

1. Build an input mixing artifacts (a non-breaking space, a zero-width character, smart quotes, an em-dash variant, and an emoji), e.g. in Python:
   `python -c "open('uni.txt','w').write('Ciao mondo “virgolette” — trattino \U0001F600 zero​width')"`
2. Preprocess `uni.txt` (5.1.1) and inspect `normalized_text`.
3. Verify: the NBSP and zero-width character are gone (NBSP → normal space), smart/curly quotes and the em-dash are normalized to plain forms, and the emoji is either removed or verbalized per the model profile (the built-in Italian table names common emoji; otherwise a Unicode-name fallback is used).

Expected outcome: invisible/control characters, NBSP/whitespace variants, dash/quote variants, and emoji are normalized or removed.

#### 5.1.5 Layout repair & sentence segmentation stages (REQ-F-text-layout-repair)

Two stages cooperate on line structure: **layout repair** (stage 2) reflows soft-wrapped sentence fragments back together, and **sentence segmentation** (stage 5, the last) then puts each sentence on its own line. Sentence segmentation runs after numbers/abbreviations are expanded so a sentence-ending period is not confused with a thousands separator (`11.988`) or an abbreviation dot.

1. Build an input that mimics PDF-to-text breakage:
   ```
   Questo è un para-
   grafo spezzato su più
   righe dal layout.

   12

   CAPITOLO 2
   Inizio del secondo capitolo.
   ```
   (a word hyphenated across a line break, a sentence wrapped mid-line, an isolated page number `12`, a blank-line paragraph boundary, and a chapter heading).
2. Preprocess it and inspect `normalized_text`.
3. Verify: `para-\ngrafo` is de-hyphenated to `paragrafo`; the wrapped sentence is reflowed onto one line; the isolated `12` page number is stripped; the blank-line paragraph boundary is preserved; and `CAPITOLO 2` remains on its own physical line.
4. **Structural lines not glued:** preprocess book-style front matter with no blank lines, e.g.
   ```
   Gli psicostorici
   1
   HARI SELDON nato nell'anno 11.988, morto nel 12.069. Nel calendario in uso.
   ```
   Verify the title `Gli psicostorici` and the bare chapter number (`1`→`uno`) each stay on their **own** line (a bare-number line is structural and must not be glued onto the surrounding text), and that the body is split **one sentence per line** (`…morto nel dodicimila…nove.` and `Nel calendario in uso.` on separate lines) with `11.988`/`12.069` verbalized, not mis-split on their internal dots.
5. **Dialogue isolation:** preprocess an Italian dialogue line, e.g.
   ```
   Arrivò un ufficiale. «La sala rimarrà chiusa. Preparatevi all'atterraggio» comunicò.
   «Posso restare? Vorrei vedere Trantor.» L'ufficiale sorrise.
   ```
   Verify the spoken span (delimited by `«…»`) is isolated onto its own line(s): the narration before the quote, the quote, and the trailing dialogue tag (`comunicò.`) are **separate** lines/chunks, and the following narration (`L'ufficiale sorrise.`) is **not** glued onto the closing quote. The guillemets are flattened to straight `"` in the output (the Unicode stage leaves `«`/`»` intact so segmentation can use their direction first).
6. **Chapter boundaries survive:** run the normalized text through synthesis (5.1.10) and confirm the resulting audiobook still splits into the expected chapters (layout repair runs before chapter detection and must not defeat it).

Expected outcome: end-of-line hyphenation is resolved, spurious wraps are reflowed, isolated page numbers are stripped, structural lines (titles, bare chapter numbers, headings) are kept standalone, spoken dialogue (`«…»`) is isolated onto its own chunk(s), the body is segmented one sentence per line, and paragraph/chapter boundaries are preserved so chapter detection still functions.

#### 5.1.6 Numeric & symbolic verbalization stage (Italian) (REQ-F-text-numeric-symbolic-verbalization)

Preprocess `text` inputs and verify each verbalizes into Italian words (defaults assume `language=it`):

1. Date: `15/03/2026` → "quindici marzo duemilaventisei" (day 1 becomes the ordinal "primo"; out-of-range day/month are left as plain numbers).
2. Currency: `0,99 €` → "novantanove centesimi"; `1 €` → "un euro" (elided singular).
3. Percent: `25%` → "venticinque per cento"; per-mille `‰` similarly.
4. Temperature: `20°C` → "venti gradi Celsius".
5. Ordinal indicator: `1°` → "primo", `2ª` → "seconda".
6. Cardinal/decimal honouring Italian separators: `1.234,56` → "milleduecentotrentaquattro virgola cinque sei".
7. Standalone symbols: `&` → "e", `+` → "più", `=` → "uguale".

Expected outcome: numbers, dates, percentages, currency, temperatures, ordinals, and symbols are verbalized into language-appropriate words.

#### 5.1.7 Abbreviation expansion + optional domain dictionary (REQ-F-abbreviation-expansion)

1. Built-in Italian set: preprocess `text=Mele, pere, ecc.` → "…eccetera"; `text=il sig. Rossi` → "il signor Rossi" (the trailing period is consumed only at end of text/line, so honorifics followed by a name survive).
2. Domain dictionary (off by default): copy the example to activate it —
   `cp 3-code/backend/config/preprocessing/domain_dictionary.example.json 3-code/backend/config/preprocessing/domain_dictionary.json`
   then **restart the backend** and preprocess `text=Uso di AI e USB.` → the acronyms expand to their configured spoken forms (e.g. "intelligenza artificiale", "u esse bi"). Matching is whole-token and case-sensitive by default, so `AI` ≠ a lowercase `ai`.
3. Absence is safe: remove `domain_dictionary.json` (or supply malformed JSON), restart, and verify preprocessing still works using only the built-in set (a warning may be logged; no error).

Expected outcome: common abbreviations/acronyms are verbalized from the built-in language set, an optional on-disk domain dictionary is applied when present, and its absence never breaks preprocessing.

> The override location for the dictionary is the `LOCAL_TTS_PREPROCESSING_CONFIG_DIR` environment variable; see `3-code/backend/config/preprocessing/README.md`.

#### 5.1.8 Per-language and per-model configuration (REQ-MNT-preprocessing-pipeline)

1. **Per-language:** Italian (`it`) is the only language with built-in data shipped today, so it is the only supported value. Preprocess a numeric input with `language=it` (also the default when `language` is omitted) and verify the Italian verbalization (e.g. `1234` → "milleduecentotrentaquattro"), confirming the language profile (and its `num2words` language) is selected by the request. The per-language *mechanism* — selecting a different rule table / `num2words` code by request — is exercised in the backend unit tests (`tests/test_preprocessing_service.py`, `test_preprocessing_profiles.py`); a new language becomes a valid request value only once its data is registered.
2. **Unsupported language:** preprocess with `language=en` or `language=xx` (no registered data) and verify the request is **rejected with HTTP 400** — body `{"detail": "Unsupported output language '<code>'. Supported languages: it."}` — rather than passing the text through unchanged. An unsupported language is rejected (not a silent no-op) because the rewrites are language-specific, so a passthrough would misrepresent the raw text as "normalized" in the review step. An omitted/empty `language` still defaults to `it` and is accepted. Because this is input validation, it returns 400 even when no model is loaded (before the 409 no-model check).
3. **Per-model:** the pipeline reads the loaded model's profile (keyed by `model_id`, default fallback). With only the default profile registered, all four stages run for every model; switching the loaded model does not change the registered stage logic — only which profile is resolved.

Expected outcome: the pipeline is configurable per output language and per TTS model; language data is selected by the request, the (currently single) supported language `it` is accepted, and an unsupported output language is rejected with 400 rather than silently producing an unchanged "normalized" text.

#### 5.1.9 Latency bound (REQ-PERF-preprocessing-overhead)

1. Short input (≤500 chars): time a `POST /preprocess` call (e.g. `curl -s -o /dev/null -w "%{time_total}\n" -F "text=$(head -c 400 sample.txt)" http://127.0.0.1:8000/api/v1/preprocess`) and verify it completes well under ~1 s.
2. Large input (~2 MB `.txt`): preprocess it and verify it completes within ~10 s on min-spec hardware.

Expected outcome: synchronous preprocessing stays within the bounded latency targets (≤1 s for a ≤500-char preview, ≤10 s for a ~2 MB document).

#### 5.1.10 Creation-view review flow (UI) (REQ-USA-normalized-text-review)

1. Open the app, go to **Create**. Select a valid `.txt` file (the `.txt`/2 MB client-side checks from Phase 4 test 4.2 still apply).
2. Verify a **"Preprocess & Review"** button is shown (not "Start Synthesis"). Click it.
3. Verify a busy state appears ("Preprocessing…" button label and a "Normalizing text…" message) during the synchronous call.
4. On success, verify a **"Review normalized text"** section appears with:
   - a hint explaining this is exactly what will be read aloud,
   - a character-count line "`<original>` → `<normalized>` characters after normalization",
   - an **editable** textarea pre-filled with the normalized text,
   - a **"Confirm & Start Synthesis"** button and a **"Start Over"** button.
5. Verify synthesis does **not** auto-start — nothing is generated until "Confirm & Start Synthesis" is clicked.
6. Click "Confirm & Start Synthesis" and verify the job runs with progress exactly as in Phase 4 tests 4.4–4.5 (the progress/SSE/success behavior is unchanged).
7. Click "Start Over" (before confirming) and verify the review resets back to file selection.

Expected outcome: the user reviews — and may edit — the normalized text and must explicitly confirm before generation begins.

#### 5.1.11 Exact-text guarantee — no re-preprocessing (DEC-preprocess-review-flow)

1. In the review textarea (5.1.10), **edit** the normalized text — e.g. add a distinctive sentence or change a number — then click "Confirm & Start Synthesis".
2. After completion, open the audiobook (Phase 5 playback) and confirm the audio reflects the **edited** text verbatim, with no further normalization applied on top of your edit (e.g. a number you typed as digits is read as digits if you left it that way).
3. Confirm in DevTools that the `POST /api/v1/jobs/synthesis` request body carries the exact reviewed `text` and the `language` resolved by `/preprocess` (both calls must agree on `language`).

Expected outcome: synthesis uses exactly the confirmed text; the preprocessing pipeline is not re-run inside `/jobs/synthesis`.

#### 5.1.12 GOAL-text-normalization criterion 6 — subjective naturalness on a messy PDF-style input

This step subjectively assesses success criterion 6 ("audio generated from normalized text is measurably more natural than audio from raw text on representative messy inputs").

1. Save the following representative PDF-extraction-style sample as `messy.txt`:
   ```
   INTRODUZIONE


   Nel 2026 il fat-
   turato è cresciuto del 12,5% rispetto
   ai 3.400.000 € dell'anno prec.

   Pag. 1


   Il sig. Rossi ha dichiarato:  “Investiremo
   il   25%   delle   risorse”   😀   entro il 1°
   trimestre, ecc.

   12

   CAPITOLO 1

   Risultati
   ```
   (broken hyphenation, mid-sentence wraps, page-number lines, irregular spacing, smart quotes, an emoji, a percentage, currency, an ordinal, an abbreviation, and a chapter heading.)
2. **Baseline (raw):** to hear the un-normalized result, synthesize the raw text directly — call `POST /api/v1/jobs/synthesis` with the raw file contents as `text` (bypassing `/preprocess`):
   `curl -s -X POST -H "Content-Type: application/json" -d "$(python -c "import json,sys;print(json.dumps({'text':open('messy.txt').read(),'source_filename':'messy-raw.txt'}))")" http://127.0.0.1:8000/api/v1/jobs/synthesis`
   Play the resulting audiobook and note artifacts: digits/percent/currency read awkwardly or in English, "Pag. 1" and the stray "12" read aloud, the broken word "fat- turato", and the emoji mis-read or skipped.
3. **Normalized:** run `messy.txt` through the Create view (5.1.10) — preprocess, review, confirm — and play that audiobook.
4. **Compare:** subjectively confirm the normalized audio is clearly more natural — numbers/date/percent/currency/ordinal are spoken as Italian words, the abbreviation is expanded, page numbers are not read, the broken word is rejoined, the emoji is removed/verbalized, and sentences flow without mid-line breaks. Verify chapter detection still produced a "CAPITOLO 1" chapter.

Expected outcome: a reviewer can hear that normalized-text audio is measurably more natural than raw-text audio on a representative messy input (GOAL-text-normalization criterion 6). This is a subjective, qualitative check; record observations rather than a pass/fail metric.

## Rollback

Not applicable — manual testing does not modify production state. If the application is left running, stop it with `Ctrl+C`.

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError: No module named 'local_tts'` | Ensure the venv is activated and `pip install -e ".[dev]"` was run |
| `nvm: command not found` | Install nvm per https://github.com/nvm-sh/nvm |
| Node version mismatch | Run `nvm use` in the frontend directory |
| `No CUDA GPU found` warning at startup | Install NVIDIA drivers and CUDA toolkit; verify with `nvidia-smi` |
| `ffmpeg not found` error at startup | Install ffmpeg: `sudo apt install ffmpeg` (Linux) or download from ffmpeg.org (Windows) |
| Frontend shows blank page in production mode | Ensure `npm run build` was run and `dist/` directory exists |
| API calls return 404 in dev mode | Ensure the backend is running on port 8000 before starting the Vite dev server |
| Database not created | Check write permissions in the data directory; check `LOCAL_TTS_DATA_DIR` env var |
| "No model loaded" when submitting synthesis | Load a model first on the Models page (Phase 3) |
| `Failed to synthesize text segment: Unsupported languages: ['it']` (or similar) | Expected to be handled: the app passes the ISO 639-1 code (`it`) and each adapter translates it to its model identifier (Qwen3 `Italian`, Kokoro `i`). If you see this, confirm the loaded model's adapter maps the requested ISO code in `_resolve_language` (Qwen3) / `_resolve_lang_code` (Kokoro); a genuinely unsupported language raises a clear `ValueError` listing the accepted codes |
| Synthesis job stays "queued" indefinitely | Check backend logs for worker thread errors; ensure the job service started correctly |
| Progress bar not updating | Verify SSE connection is active in DevTools Network tab; check for `job-progress` events |
| "Insufficient disk space" error | Free up disk space or use a smaller text file; the estimate is ~0.002 MB per character |
| Audiobook title has underscores/hyphens | Expected: title is derived from filename with `-` and `_` replaced by spaces |
| Model shows "No adapter" badge with no Download/Load buttons | Expected: no adapter is registered yet for that model. Use an adapter-backed model (Kokoro-82M or Qwen3-TTS), or implement the corresponding `TASK-loader-*` adapter |
| `loader_available` is `false` for a model you expect to work | Confirm the adapter is registered in `_ADAPTER_REGISTRY` (`src/local_tts/tts/adapters/__init__.py`); restart the backend after registering |
| Kokoro produces garbled or English-only audio for non-English text | Ensure `espeak-ng` is installed and on PATH (`sudo apt-get install espeak-ng`) |
| Library view is empty after a successful synthesis | Confirm the job completed (Phase 4 test 4.5) and `GET /api/v1/audiobooks` returns the entry; check the data directory (`LOCAL_TTS_DATA_DIR`) matches between synthesis and the running backend |
| Audio player shows controls but won't play / 404 on the audio URL | Verify the chapter audio file exists under `data/audiobooks/<id>/`; check `GET /api/v1/audiobooks/<id>/chapters/<n>/audio` returns 200/206, not 404 |
| Seeking restarts the track from the beginning | Confirm the audio endpoint returns `206` with `Accept-Ranges: bytes` (test 5.4); a proxy stripping Range headers can force full re-download |
| Playback does not resume at the saved position | The bookmark is best-effort and saved on pause/end/chapter-change/unmount, every 20 seconds while playing, and on page navigation/reload/close (the last via a `keepalive` request); ensure `PUT /api/v1/audiobooks/<id>/position` succeeds and that the saved chapter still exists. The seek is applied on `loadedmetadata`, so a missing/short audio file will not seek |
| Deleted audiobook still shows in the library | Refresh the Library view; if it persists, confirm `DELETE /api/v1/audiobooks/<id>` returned 204 and check backend logs for file-cleanup errors |
| `409 No model loaded` from `POST /api/v1/preprocess` | Preprocessing applies the loaded model's profile — load a model first on the Models page (Phase 3) |
| `POST /api/v1/preprocess` returns `400 Unsupported output language` | The request `language` has no registered data. Only `it` ships today; omit `language` (defaults to `it`) or pass `it`. An unsupported language is rejected by design rather than passing the text through unchanged (test 5.1.8) |
| `/preprocess` returns the raw text unchanged for a supported language | Confirm the four stages self-registered (they register at import via `preprocessing/__init__.py`); for `it`, also confirm the input actually contains normalizable content (numbers/dates/abbreviations/layout artifacts) — clean prose is legitimately returned unchanged |
| Domain-dictionary acronyms not expanded | Ensure `config/preprocessing/domain_dictionary.json` exists (copy from `domain_dictionary.example.json`) and **restart the backend**; matching is whole-token and case-sensitive by default. A malformed file is ignored with a logged warning (built-in set still applies) |
| Numbers/dates spoken in the wrong language | Pass the intended `language` to `/preprocess`; the same resolved `language` must be forwarded to `/jobs/synthesis` (the Create view does this automatically) |
| Chapter detection broke after preprocessing | Layout repair preserves blank-line paragraph boundaries and keeps heading/list lines standalone; verify the input's chapter headings (e.g. `CAPITOLO N`) are on their own line and separated by blank lines (test 5.1.5) |
| Audio doesn't match the reviewed text | `/jobs/synthesis` synthesizes the exact `text` it receives with no re-preprocessing; confirm the request body carries the reviewed text and that you clicked "Confirm & Start Synthesis" after editing (tests 5.1.10–5.1.11) |
| `/preprocess` slower than expected | Check the input size against the bounds (≤1 s for ≤500 chars, ≤10 s for ~2 MB, test 5.1.9); very large inputs above 2 MB are rejected with 400 |
