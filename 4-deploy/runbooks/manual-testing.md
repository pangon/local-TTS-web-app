# Runbook: Manual Testing

## Overview

Step-by-step instructions to build, run, and manually test the Local TTS Web App. This runbook is updated incrementally as new phases are completed.

**Current coverage:** Phases 1-4 (Project Scaffolding, TTS Engine Foundation, Model Management End-to-End, Audiobook Synthesis End-to-End)

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

Expected outcome: all tests pass. Tests cover GPU validator, model loader, chapter parser, synthesizer, TTS engine interface, SSE endpoint, model service/API, database initialization, static file serving, startup checks, app scaffold, job service, synthesis job API (file upload, validation, disk space check), library service (audiobook/chapter persistence), and SSE event wiring for job progress/completed/failed.

### Frontend Tests

```bash
cd 3-code/frontend
nvm use
npm run test:unit
```

Expected outcome: all tests pass. Tests cover Vue app rendering, router configuration, Vite proxy config, SSE client composable, model API service, ModelsView component, jobs API service (synthesis job creation, error handling), and CreateView component (file validation, progress display, SSE event handling, form reset).

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
3. Open `http://127.0.0.1:8000/api/sse` in a browser — should establish an SSE connection (event stream content type).
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
4. Verify an SSE connection is established to `/api/sse`.
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
| Synthesis job stays "queued" indefinitely | Check backend logs for worker thread errors; ensure the job service started correctly |
| Progress bar not updating | Verify SSE connection is active in DevTools Network tab; check for `job-progress` events |
| "Insufficient disk space" error | Free up disk space or use a smaller text file; the estimate is ~0.002 MB per character |
| Audiobook title has underscores/hyphens | Expected: title is derived from filename with `-` and `_` replaced by spaces |
