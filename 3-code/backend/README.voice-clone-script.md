# Voice-Clone Prompt Generator (offline operator script)

> **Scope:** This README documents **only** the standalone offline script
> [`src/local_tts/scripts/generate_voice_clone_prompt.py`](src/local_tts/scripts/generate_voice_clone_prompt.py).
> It is **not** the README of the backend service. The script is a manual
> operator tool — it is not part of the running application and is never invoked
> by the FastAPI app, the REST API, or the frontend (`DEC-voice-clone-prompts`).

## What it does

The Qwen3-TTS **Base** model (`Qwen/Qwen3-TTS-12Hz-1.7B-Base`) clones a voice not
from a raw audio clip at synthesis time, but from a **precomputed prompt
artifact** that the model builds from a reference clip plus its transcript.

This script performs that one-off, offline step:

```
reference audio (.mp3/.wav) + transcript  ──►  <name>.pt  (list[VoiceClonePromptItem])
```

It loads the Base model, runs
`Qwen3TTSModel.create_voice_clone_prompt(ref_audio, ref_text)`, and serializes the
result with `torch.save` to `wavs/qwen3-tts/<name>.pt`.

The Qwen3-TTS Base adapter later **loads** that `.pt` file as a default voice and
passes it to `generate_voice_clone(...)`. Building the prompt once, ahead of
time, avoids re-running the model on every synthesis request and keeps the heavy
operation out of the request path.

## Why it is a separate offline script

Per [`DEC-voice-clone-prompts`](../../2-design/decisions/DEC-voice-clone-prompts.md):

- The clone-prompt builder runs **only** here — never inside `synthesize()` or any
  request handler.
- The operation is **not** exposed via an API endpoint or the frontend.
- A missing prompt artifact makes the adapter raise a **clear error** (it does
  **not** silently fall back to raw-clip cloning or a built-in speaker).

## Prerequisites

Run this on the **GPU host** where Qwen3-TTS itself runs.

1. **The `qwen-tts` package.** It is intentionally *not* a declared backend
   dependency (it hard-pins `transformers==4.57.3`, see
   [`DEC-transformers-5x-baseline`](../../2-design/decisions/DEC-transformers-5x-baseline.md)).
   Install it on a host whose transformers baseline is `4.57.3`:

   ```bash
   pip install qwen-tts
   ```

2. **The model weights.** Downloaded/cached automatically by HuggingFace Hub on
   first run (no manual download needed). A CUDA GPU is strongly recommended;
   CPU works but is slow.

3. **A reference clip + its exact transcript.** A clean, single-speaker recording
   of a few seconds to ~30 s works well. The transcript must match what is
   spoken in the clip (ICL voice cloning conditions on it).

## Usage

Run it as a module from the backend directory (`3-code/backend/`), with the
virtual environment active:

```bash
# Inline transcript, default output name (wavs/qwen3-tts/default.pt)
python -m local_tts.scripts.generate_voice_clone_prompt \
    path/to/reference.mp3 \
    --text "the exact transcript of the reference clip"
```

```bash
# Transcript read from a file, and a named voice (wavs/qwen3-tts/alice.pt)
python -m local_tts.scripts.generate_voice_clone_prompt \
    path/to/reference.mp3 \
    --text-file path/to/transcript.txt \
    --name alice
```

On success it prints the artifact path, e.g.:

```
Voice-clone prompt written to /…/local-TTS-web-app/wavs/qwen3-tts/default.pt
```

### Arguments

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `audio` (positional) | yes | — | Path to the reference audio clip (e.g. `reference.mp3`, `.wav`). |
| `--text TEXT` | one of `--text` / `--text-file` | — | The exact transcript of the clip, inline. |
| `--text-file PATH` | one of `--text` / `--text-file` | — | Path to a UTF-8 text file containing the transcript. |
| `--name NAME` | no | `default` | Voice name. The artifact is written to `<output-dir>/<name>.pt`. The name `default` is the one the Base adapter loads as its default voice. |
| `--output-dir DIR` | no | `config.QWEN3_TTS_PROMPTS_DIR` (repo-root `wavs/qwen3-tts/`) | Directory the `.pt` artifact is written into. |
| `--model ID` | no | `Qwen/Qwen3-TTS-12Hz-1.7B-Base` | HuggingFace repo id of the Qwen3-TTS **Base** model. |
| `--device DEV` | no | `auto` | Torch device: `cuda`, `cuda:0`, `cpu`, or `auto` (CUDA when available, else CPU). |

`--text` and `--text-file` are mutually exclusive and exactly one is required.

## Output & storage layout

- Artifacts live under `wavs/qwen3-tts/` at the repository root (override with
  `--output-dir` or the `LOCAL_TTS_QWEN3_TTS_PROMPTS_DIR` environment variable).
- The whole `wavs/` tree is **gitignored** (`/wavs/`) — prompt artifacts and
  reference clips are user-provided assets and must **not** be committed.
- Each `.pt` holds a `list[VoiceClonePromptItem]` (speaker embedding + reference
  codes as torch tensors). It is **model-specific** and not portable to other
  models.

## How the adapter consumes the artifact

The Qwen3-TTS Base adapter reads the **default** prompt at synthesis time from
the configured path (default `wavs/qwen3-tts/default.pt`). So, for the default
voice to work, generate the prompt with the default name:

```bash
python -m local_tts.scripts.generate_voice_clone_prompt reference.mp3 --text "…"
# → wavs/qwen3-tts/default.pt
```

If that file is missing, the adapter raises a clear error directing you back to
this script (no silent fallback). Per-request selection among multiple prepared
prompts in `wavs/qwen3-tts/` is a later (Phase 6) capability.

## Environment variables

| Variable | Effect |
|----------|--------|
| `LOCAL_TTS_QWEN3_TTS_PROMPTS_DIR` | Overrides the default output directory (`wavs/qwen3-tts/`). The `--output-dir` flag overrides this per run. |

## Troubleshooting

| Symptom | Cause / fix |
|---------|-------------|
| `ModuleNotFoundError: No module named 'qwen_tts'` | The GPU-host dependency is not installed. Run `pip install qwen-tts` on a host whose transformers baseline is `4.57.3`. |
| `error: Reference audio not found: …` | The `audio` path is wrong or the file does not exist. |
| `error: Transcript must be a non-empty string …` | Provide a non-empty `--text` / `--text-file`; the transcript is required for ICL cloning. |
| `… does not support create_voice_clone_prompt …` | `--model` points to a non-Base variant (e.g. CustomVoice). Only the **Base** model exposes clone-prompt building. |
| CUDA out of memory | Use a GPU with more VRAM, a shorter reference clip, or `--device cpu` (slow). |

## Related

- Decision: [`DEC-voice-clone-prompts`](../../2-design/decisions/DEC-voice-clone-prompts.md)
- Decision: [`DEC-transformers-5x-baseline`](../../2-design/decisions/DEC-transformers-5x-baseline.md)
- Decision: [`DEC-default-italian-language`](../../2-design/decisions/DEC-default-italian-language.md)
- Backend component overview: [`CLAUDE.component.md`](CLAUDE.component.md)
