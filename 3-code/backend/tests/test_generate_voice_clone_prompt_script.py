"""Tests for the offline Qwen3-TTS voice-clone-prompt generator script.

Covers: device selection, load-kwarg construction, the core
``generate_voice_clone_prompt`` builder (argument passing, torch.save, output
dir creation, input validation), the CLI ``main`` (transcript sources, --name
output path, error handling), and the DEC-voice-clone-prompts requirement that
the script is NOT reachable from the FastAPI app / API layer.

All ``qwen_tts`` package dependencies are mocked.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from local_tts import config
from local_tts.scripts import generate_voice_clone_prompt as script


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fake_qwen_tts(prompt_items: object | None = None) -> tuple[MagicMock, MagicMock]:
    """Build a fake ``qwen_tts`` module with a mocked Qwen3TTSModel.

    Returns ``(fake_module, mock_model_instance)``.
    """
    mock_model = MagicMock()
    mock_model.create_voice_clone_prompt.return_value = (
        prompt_items if prompt_items is not None else [MagicMock(name="VoiceClonePromptItem")]
    )
    mock_model_cls = MagicMock()
    mock_model_cls.from_pretrained.return_value = mock_model

    fake_module = MagicMock()
    fake_module.Qwen3TTSModel = mock_model_cls
    return fake_module, mock_model


# ---------------------------------------------------------------------------
# Device selection
# ---------------------------------------------------------------------------

def test_select_device_explicit_value_is_returned() -> None:
    assert script._select_device("cuda:1") == "cuda:1"


def test_select_device_auto_prefers_cuda_when_available() -> None:
    with patch("torch.cuda.is_available", return_value=True):
        assert script._select_device("auto") == "cuda"


def test_select_device_auto_falls_back_to_cpu() -> None:
    with patch("torch.cuda.is_available", return_value=False):
        assert script._select_device(None) == "cpu"


# ---------------------------------------------------------------------------
# Load kwargs
# ---------------------------------------------------------------------------

def test_build_load_kwargs_cuda_uses_bfloat16() -> None:
    import torch

    with patch.dict(sys.modules, {"flash_attn": None}):
        kwargs = script._build_load_kwargs("cuda")
    assert kwargs["device_map"] == "cuda"
    assert kwargs["dtype"] == torch.bfloat16
    # flash-attn unavailable -> no attn_implementation key
    assert "attn_implementation" not in kwargs


def test_build_load_kwargs_cuda_with_flash_attn() -> None:
    with patch.dict(sys.modules, {"flash_attn": MagicMock()}):
        kwargs = script._build_load_kwargs("cuda:0")
    assert kwargs["attn_implementation"] == "flash_attention_2"


def test_build_load_kwargs_cpu_uses_float32_and_no_flash() -> None:
    import torch

    kwargs = script._build_load_kwargs("cpu")
    assert kwargs["dtype"] == torch.float32
    assert "attn_implementation" not in kwargs


# ---------------------------------------------------------------------------
# Core builder
# ---------------------------------------------------------------------------

def test_generate_builds_prompt_and_saves(tmp_path: Path) -> None:
    audio = tmp_path / "ref.mp3"
    audio.write_bytes(b"fake-audio")
    out = tmp_path / "nested" / "alice.pt"
    items = ["prompt-item"]
    fake_module, mock_model = _fake_qwen_tts(prompt_items=items)

    with patch.dict(sys.modules, {"qwen_tts": fake_module}), \
         patch("torch.save") as mock_save, \
         patch("torch.cuda.is_available", return_value=False):
        result = script.generate_voice_clone_prompt(
            audio_path=audio,
            transcript="ciao mondo",
            output_path=out,
            device="auto",
        )

    # Base model loaded from the default repo id
    fake_module.Qwen3TTSModel.from_pretrained.assert_called_once()
    assert fake_module.Qwen3TTSModel.from_pretrained.call_args.args[0] == script.DEFAULT_MODEL_ID

    # Clone prompt built from the audio path string + transcript
    mock_model.create_voice_clone_prompt.assert_called_once_with(
        ref_audio=str(audio),
        ref_text="ciao mondo",
    )

    # Saved the returned items to the output path; parent dir created
    mock_save.assert_called_once_with(items, str(out))
    assert out.parent.is_dir()
    assert result == out


def test_generate_honors_custom_model_id(tmp_path: Path) -> None:
    audio = tmp_path / "ref.wav"
    audio.write_bytes(b"x")
    fake_module, _ = _fake_qwen_tts()

    with patch.dict(sys.modules, {"qwen_tts": fake_module}), \
         patch("torch.save"), \
         patch("torch.cuda.is_available", return_value=False):
        script.generate_voice_clone_prompt(
            audio_path=audio,
            transcript="t",
            output_path=tmp_path / "x.pt",
            model_id="some/other-model",
        )

    assert fake_module.Qwen3TTSModel.from_pretrained.call_args.args[0] == "some/other-model"


def test_generate_missing_audio_raises(tmp_path: Path) -> None:
    fake_module, _ = _fake_qwen_tts()
    with patch.dict(sys.modules, {"qwen_tts": fake_module}):
        with pytest.raises(FileNotFoundError):
            script.generate_voice_clone_prompt(
                audio_path=tmp_path / "missing.mp3",
                transcript="t",
                output_path=tmp_path / "x.pt",
            )


def test_generate_empty_transcript_raises(tmp_path: Path) -> None:
    audio = tmp_path / "ref.mp3"
    audio.write_bytes(b"x")
    fake_module, _ = _fake_qwen_tts()
    with patch.dict(sys.modules, {"qwen_tts": fake_module}):
        with pytest.raises(ValueError):
            script.generate_voice_clone_prompt(
                audio_path=audio,
                transcript="   ",
                output_path=tmp_path / "x.pt",
            )


# ---------------------------------------------------------------------------
# CLI: main
# ---------------------------------------------------------------------------

def test_main_inline_text_default_name(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    audio = tmp_path / "ref.mp3"
    audio.write_bytes(b"x")
    fake_module, mock_model = _fake_qwen_tts()

    with patch.dict(sys.modules, {"qwen_tts": fake_module}), \
         patch("torch.save"), \
         patch("torch.cuda.is_available", return_value=False):
        rc = script.main([str(audio), "--text", "hello", "--output-dir", str(tmp_path)])

    assert rc == 0
    mock_model.create_voice_clone_prompt.assert_called_once_with(
        ref_audio=str(audio), ref_text="hello"
    )
    expected = (tmp_path / f"{script.DEFAULT_PROMPT_NAME}.pt").resolve()
    assert str(expected) in capsys.readouterr().out


def test_main_text_file_and_custom_name(tmp_path: Path) -> None:
    audio = tmp_path / "ref.mp3"
    audio.write_bytes(b"x")
    transcript_file = tmp_path / "t.txt"
    transcript_file.write_text("from file", encoding="utf-8")
    fake_module, mock_model = _fake_qwen_tts()

    saved: dict[str, object] = {}

    def _capture_save(obj: object, path: str) -> None:
        saved["path"] = path

    with patch.dict(sys.modules, {"qwen_tts": fake_module}), \
         patch("torch.save", side_effect=_capture_save), \
         patch("torch.cuda.is_available", return_value=False):
        rc = script.main([
            str(audio),
            "--text-file", str(transcript_file),
            "--name", "alice",
            "--output-dir", str(tmp_path),
        ])

    assert rc == 0
    mock_model.create_voice_clone_prompt.assert_called_once_with(
        ref_audio=str(audio), ref_text="from file"
    )
    assert saved["path"] == str((tmp_path / "alice.pt").resolve())


def test_main_defaults_output_dir_to_config(tmp_path: Path) -> None:
    audio = tmp_path / "ref.mp3"
    audio.write_bytes(b"x")
    fake_module, _ = _fake_qwen_tts()
    saved: dict[str, object] = {}

    with patch.dict(sys.modules, {"qwen_tts": fake_module}), \
         patch("torch.save", side_effect=lambda obj, path: saved.update(path=path)), \
         patch("torch.cuda.is_available", return_value=False):
        rc = script.main([str(audio), "--text", "hi"])

    assert rc == 0
    assert saved["path"] == str((config.QWEN3_TTS_PROMPTS_DIR / "default.pt").resolve())


def test_main_requires_a_transcript_source(tmp_path: Path) -> None:
    audio = tmp_path / "ref.mp3"
    audio.write_bytes(b"x")
    with pytest.raises(SystemExit) as exc:
        script.main([str(audio)])
    assert exc.value.code == 2  # argparse usage error


def test_main_missing_audio_is_usage_error(tmp_path: Path) -> None:
    fake_module, _ = _fake_qwen_tts()
    with patch.dict(sys.modules, {"qwen_tts": fake_module}):
        with pytest.raises(SystemExit) as exc:
            script.main([str(tmp_path / "nope.mp3"), "--text", "hi"])
    assert exc.value.code == 2  # parser.error -> exit code 2


def test_main_returns_1_on_unexpected_failure(tmp_path: Path) -> None:
    audio = tmp_path / "ref.mp3"
    audio.write_bytes(b"x")
    fake_module, mock_model = _fake_qwen_tts()
    mock_model.create_voice_clone_prompt.side_effect = RuntimeError("CUDA OOM")

    with patch.dict(sys.modules, {"qwen_tts": fake_module}), \
         patch("torch.cuda.is_available", return_value=False):
        rc = script.main([str(audio), "--text", "hi", "--output-dir", str(tmp_path)])

    assert rc == 1


# ---------------------------------------------------------------------------
# DEC-voice-clone-prompts: script must not be reachable from the app / API
# ---------------------------------------------------------------------------

def test_script_not_imported_by_app_or_api() -> None:
    """The offline script must not be imported by the FastAPI app / API layer.

    Static source scan over app.py + the api/ package (DEC-voice-clone-prompts
    Required check #1): no runtime module references the scripts subpackage.
    """
    src_root = Path(script.__file__).resolve().parents[1]  # local_tts/
    runtime_files = [src_root / "app.py", *(src_root / "api").rglob("*.py")]
    offenders = [
        f for f in runtime_files
        if f.exists() and "local_tts.scripts" in f.read_text(encoding="utf-8")
    ]
    assert offenders == [], f"scripts package referenced by runtime files: {offenders}"
