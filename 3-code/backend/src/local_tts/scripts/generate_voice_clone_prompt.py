"""Offline voice-clone-prompt generator for the Qwen3-TTS Base model.

A **standalone operator tool** — run manually on the GPU host, **not** wired into
the FastAPI app / API / frontend (DEC-voice-clone-prompts). It turns a reference
audio file plus its transcript into a precomputed clone-prompt artifact that the
Qwen3-TTS Base adapter later loads as a (default) voice:

    python -m local_tts.scripts.generate_voice_clone_prompt \\
        path/to/reference.mp3 --text "the exact transcript of the clip"

    # or read the transcript from a file, and name the voice:
    python -m local_tts.scripts.generate_voice_clone_prompt \\
        path/to/reference.mp3 --text-file transcript.txt --name alice

The artifact is serialized with ``torch.save`` to
``<QWEN3_TTS_PROMPTS_DIR>/<name>.pt`` (default ``wavs/qwen3-tts/default.pt``,
gitignored). It holds the ``list[VoiceClonePromptItem]`` returned by the model's
``create_voice_clone_prompt(ref_audio, ref_text)`` — a model-specific artifact
that is **not** portable to other models.

Why offline: building the prompt requires loading the model and running the
clone-prompt builder, which is wasteful to repeat on every synthesis and awkward
inside the request path (DEC-voice-clone-prompts). The builder therefore runs
**only here**.

Requires the GPU-host ``qwen-tts`` package (transformers 4.57.3 baseline,
DEC-transformers-5x-baseline). The Base model weights are downloaded/cached by
HuggingFace Hub on first use.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Any

from local_tts import config

logger = logging.getLogger(__name__)

# The Base variant is the only Qwen3-TTS model exposing create_voice_clone_prompt
# (DEC-voice-clone-prompts). CustomVoice/VoiceDesign reject it.
DEFAULT_MODEL_ID = "Qwen/Qwen3-TTS-12Hz-1.7B-Base"

# Default artifact name when --name is omitted; matches the Base adapter's
# default prompt (wavs/qwen3-tts/default.pt).
DEFAULT_PROMPT_NAME = "default"


def _select_device(requested: str | None) -> str:
    """Resolve the torch device to load the model on.

    ``None``/``"auto"`` picks ``"cuda"`` when available, else ``"cpu"``.
    """
    import torch

    if requested and requested.strip().lower() != "auto":
        return requested.strip()
    return "cuda" if torch.cuda.is_available() else "cpu"


def _build_load_kwargs(device: str) -> dict[str, Any]:
    """Build ``Qwen3TTSModel.from_pretrained`` kwargs for *device*.

    Mirrors the Qwen3-TTS adapter: bf16 on CUDA (with FlashAttention 2 when
    installed), float32 on CPU.
    """
    import torch

    kwargs: dict[str, Any] = {"device_map": device}
    if device.startswith("cuda"):
        kwargs["dtype"] = torch.bfloat16
        try:
            import flash_attn  # noqa: F401

            kwargs["attn_implementation"] = "flash_attention_2"
        except ImportError:
            logger.info(
                "flash-attn not installed; using default attention "
                "(higher VRAM usage during prompt building)."
            )
    else:
        kwargs["dtype"] = torch.float32
    return kwargs


def generate_voice_clone_prompt(
    audio_path: Path,
    transcript: str,
    output_path: Path,
    *,
    model_id: str = DEFAULT_MODEL_ID,
    device: str | None = None,
) -> Path:
    """Build and persist a Qwen3-TTS voice-clone prompt from a reference clip.

    Loads the Base model, runs ``create_voice_clone_prompt(audio_path, transcript)``
    (ICL mode — the transcript is required), and ``torch.save``s the resulting
    ``list[VoiceClonePromptItem]`` to *output_path*.

    Args:
        audio_path: Reference audio file (e.g. ``.mp3`` / ``.wav``).
        transcript: The exact transcript of the reference clip (non-empty).
        output_path: Destination ``.pt`` file; parent dirs are created.
        model_id: HuggingFace repo id of the Qwen3-TTS **Base** model.
        device: Torch device, or ``None``/``"auto"`` to auto-select.

    Returns:
        The *output_path* the artifact was written to.

    Raises:
        FileNotFoundError: If *audio_path* does not exist.
        ValueError: If *transcript* is empty.
    """
    import torch
    from qwen_tts import Qwen3TTSModel

    if not audio_path.exists():
        raise FileNotFoundError(f"Reference audio not found: {audio_path}")
    if not transcript.strip():
        raise ValueError("Transcript must be a non-empty string (ICL voice cloning).")

    resolved_device = _select_device(device)
    logger.info("Loading Qwen3-TTS Base model %s on %s", model_id, resolved_device)
    model = Qwen3TTSModel.from_pretrained(model_id, **_build_load_kwargs(resolved_device))

    logger.info("Building voice-clone prompt from %s", audio_path)
    prompt_items = model.create_voice_clone_prompt(
        ref_audio=str(audio_path),
        ref_text=transcript,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(prompt_items, str(output_path))
    logger.info("Saved voice-clone prompt to %s", output_path)
    return output_path


def _read_transcript(args: argparse.Namespace) -> str:
    """Resolve the transcript text from ``--text`` or ``--text-file``."""
    if args.text is not None:
        return args.text
    return Path(args.text_file).read_text(encoding="utf-8")


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="generate_voice_clone_prompt",
        description=(
            "Build a precomputed Qwen3-TTS voice-clone prompt from a reference "
            "audio clip and its transcript, saved as a .pt artifact under the "
            "Qwen3-TTS prompts directory (default wavs/qwen3-tts/)."
        ),
    )
    parser.add_argument(
        "audio",
        type=Path,
        help="Path to the reference audio clip (e.g. reference.mp3).",
    )
    text_group = parser.add_mutually_exclusive_group(required=True)
    text_group.add_argument(
        "--text",
        help="The exact transcript of the reference clip (inline).",
    )
    text_group.add_argument(
        "--text-file",
        help="Path to a UTF-8 text file containing the transcript.",
    )
    parser.add_argument(
        "--name",
        default=DEFAULT_PROMPT_NAME,
        help=(
            "Voice name; the artifact is written to <prompts-dir>/<name>.pt "
            f"(default {DEFAULT_PROMPT_NAME!r}, consumed as the Base adapter's "
            "default voice)."
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=config.QWEN3_TTS_PROMPTS_DIR,
        help=(
            "Directory to write the .pt artifact into "
            f"(default: {config.QWEN3_TTS_PROMPTS_DIR})."
        ),
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL_ID,
        help=f"Qwen3-TTS Base model repo id (default: {DEFAULT_MODEL_ID}).",
    )
    parser.add_argument(
        "--device",
        default="auto",
        help="Torch device (e.g. cuda, cuda:0, cpu) or 'auto' (default).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns a process exit code."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:     %(message)s")
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    output_path = (args.output_dir / f"{args.name}.pt").resolve()

    try:
        transcript = _read_transcript(args)
        generate_voice_clone_prompt(
            audio_path=args.audio,
            transcript=transcript,
            output_path=output_path,
            model_id=args.model,
            device=args.device,
        )
    except (FileNotFoundError, ValueError) as exc:
        parser.error(str(exc))
    except Exception as exc:  # pragma: no cover - surfaced to the operator
        logger.error("Failed to generate voice-clone prompt: %s: %s", type(exc).__name__, exc)
        return 1

    print(f"Voice-clone prompt written to {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
