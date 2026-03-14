"""Tests for the synthesizer module.

Covers: sentence splitting, single-segment synthesis, MP3 encoding,
chapter synthesis, multi-chapter synthesis with progress callbacks.
All GPU/model dependencies are mocked.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from local_tts.tts.chapter_parser import Chapter
from local_tts.tts.synthesizer import (
    SynthesisError,
    SynthesisResult,
    encode_to_mp3,
    split_into_sentences,
    synthesize_chapter,
    synthesize_chapters,
    synthesize_segment,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_RATE = 16000


def _make_mock_model(sample_rate: int = SAMPLE_RATE) -> MagicMock:
    """Create a mock TTS model that returns a deterministic waveform."""
    model = MagicMock()
    model.device = "cpu"

    def forward(**kwargs):
        # Generate a short sine wave as fake audio (0.1 seconds)
        num_samples = sample_rate // 10
        t = np.linspace(0, 0.1, num_samples, dtype=np.float32)
        waveform = np.sin(2 * np.pi * 440 * t)
        import torch

        return SimpleNamespace(waveform=torch.tensor(waveform).unsqueeze(0))

    model.__call__ = forward
    model.side_effect = forward
    return model


def _make_mock_tokenizer() -> MagicMock:
    """Create a mock tokenizer that returns dummy input tensors."""
    import torch

    tokenizer = MagicMock()

    def tokenize(text, return_tensors=None):
        return {"input_ids": torch.tensor([[1, 2, 3]])}

    tokenizer.side_effect = tokenize
    tokenizer.__call__ = tokenize
    return tokenizer


# ---------------------------------------------------------------------------
# split_into_sentences
# ---------------------------------------------------------------------------


class TestSplitIntoSentences:
    def test_simple_sentences(self):
        text = "Hello world. How are you? I am fine!"
        result = split_into_sentences(text)
        assert result == ["Hello world.", "How are you?", "I am fine!"]

    def test_single_sentence_no_punctuation(self):
        text = "Hello world"
        result = split_into_sentences(text)
        assert result == ["Hello world"]

    def test_empty_text(self):
        assert split_into_sentences("") == []

    def test_whitespace_only(self):
        assert split_into_sentences("   ") == []

    def test_multiple_spaces_between_sentences(self):
        text = "First sentence.   Second sentence."
        result = split_into_sentences(text)
        assert result == ["First sentence.", "Second sentence."]

    def test_preserves_abbreviations_without_space(self):
        # "Dr.Jones" should not be split since there's no space after the period
        text = "Dr.Jones said hello. Then left."
        result = split_into_sentences(text)
        assert result == ["Dr.Jones said hello.", "Then left."]

    def test_newlines_within_sentence(self):
        text = "First sentence.\nSecond sentence."
        result = split_into_sentences(text)
        assert result == ["First sentence.", "Second sentence."]


# ---------------------------------------------------------------------------
# synthesize_segment
# ---------------------------------------------------------------------------


class TestSynthesizeSegment:
    def test_returns_numpy_array(self):
        model = _make_mock_model()
        tokenizer = _make_mock_tokenizer()
        result = synthesize_segment("Hello world", model, tokenizer)
        assert isinstance(result, np.ndarray)
        assert result.dtype == np.float32
        assert len(result) > 0

    def test_calls_model_with_tokenized_input(self):
        model = _make_mock_model()
        tokenizer = _make_mock_tokenizer()
        synthesize_segment("Test text", model, tokenizer)
        tokenizer.assert_called_once_with("Test text", return_tensors="pt")

    def test_raises_synthesis_error_on_failure(self):
        model = MagicMock()
        model.device = "cpu"
        model.side_effect = RuntimeError("CUDA OOM")
        tokenizer = _make_mock_tokenizer()
        with pytest.raises(SynthesisError, match="Failed to synthesize"):
            synthesize_segment("Test", model, tokenizer)


# ---------------------------------------------------------------------------
# encode_to_mp3
# ---------------------------------------------------------------------------


class TestEncodeToMp3:
    def test_creates_mp3_file(self, tmp_path: Path):
        waveform = np.sin(
            np.linspace(0, 2 * np.pi * 440, SAMPLE_RATE, dtype=np.float32)
        )
        output = tmp_path / "test.mp3"
        duration = encode_to_mp3(waveform, SAMPLE_RATE, output)
        assert output.exists()
        assert output.stat().st_size > 0
        assert duration > 0

    def test_returns_correct_duration(self, tmp_path: Path):
        # 2 seconds of audio
        num_samples = SAMPLE_RATE * 2
        waveform = np.zeros(num_samples, dtype=np.float32)
        output = tmp_path / "silence.mp3"
        duration = encode_to_mp3(waveform, SAMPLE_RATE, output)
        # MP3 encoding may add slight padding, allow tolerance
        assert abs(duration - 2.0) < 0.1

    def test_creates_parent_directories(self, tmp_path: Path):
        output = tmp_path / "nested" / "dir" / "test.mp3"
        waveform = np.zeros(SAMPLE_RATE, dtype=np.float32)
        encode_to_mp3(waveform, SAMPLE_RATE, output)
        assert output.exists()

    def test_clips_values_outside_range(self, tmp_path: Path):
        # Values outside [-1, 1] should be clipped, not cause errors
        waveform = np.array([2.0, -2.0, 0.5, -0.5], dtype=np.float32)
        waveform = np.tile(waveform, SAMPLE_RATE // 4)
        output = tmp_path / "clipped.mp3"
        duration = encode_to_mp3(waveform, SAMPLE_RATE, output)
        assert duration > 0


# ---------------------------------------------------------------------------
# synthesize_chapter
# ---------------------------------------------------------------------------


class TestSynthesizeChapter:
    def test_synthesizes_text_to_mp3(self, tmp_path: Path):
        model = _make_mock_model()
        tokenizer = _make_mock_tokenizer()
        output = tmp_path / "chapter.mp3"
        duration = synthesize_chapter(
            "Hello world. How are you?", model, tokenizer, SAMPLE_RATE, output
        )
        assert output.exists()
        assert duration > 0

    def test_empty_text_produces_silence(self, tmp_path: Path):
        model = _make_mock_model()
        tokenizer = _make_mock_tokenizer()
        output = tmp_path / "empty.mp3"
        duration = synthesize_chapter(
            "", model, tokenizer, SAMPLE_RATE, output
        )
        assert output.exists()
        assert duration > 0
        # Model should not have been called for empty text
        model.assert_not_called()

    def test_multiple_sentences_concatenated(self, tmp_path: Path):
        model = _make_mock_model()
        tokenizer = _make_mock_tokenizer()
        output = tmp_path / "multi.mp3"
        duration = synthesize_chapter(
            "First sentence. Second sentence. Third sentence.",
            model,
            tokenizer,
            SAMPLE_RATE,
            output,
        )
        assert output.exists()
        # Model should be called 3 times (once per sentence)
        assert model.call_count == 3
        assert duration > 0


# ---------------------------------------------------------------------------
# synthesize_chapters
# ---------------------------------------------------------------------------


class TestSynthesizeChapters:
    def _make_chapters(self, count: int = 3) -> list[Chapter]:
        return [
            Chapter(
                number=i + 1,
                title=f"Chapter {i + 1}",
                text=f"Content of chapter {i + 1}.",
            )
            for i in range(count)
        ]

    def test_produces_one_mp3_per_chapter(self, tmp_path: Path):
        model = _make_mock_model()
        tokenizer = _make_mock_tokenizer()
        chapters = self._make_chapters(3)
        results = synthesize_chapters(
            chapters, model, tokenizer, SAMPLE_RATE, tmp_path
        )
        assert len(results) == 3
        for result in results:
            mp3_path = tmp_path / result.audio_filename
            assert mp3_path.exists()
            assert mp3_path.stat().st_size > 0

    def test_filenames_follow_convention(self, tmp_path: Path):
        model = _make_mock_model()
        tokenizer = _make_mock_tokenizer()
        chapters = self._make_chapters(2)
        results = synthesize_chapters(
            chapters, model, tokenizer, SAMPLE_RATE, tmp_path
        )
        assert results[0].audio_filename == "chapter-01.mp3"
        assert results[1].audio_filename == "chapter-02.mp3"

    def test_progress_callback_called(self, tmp_path: Path):
        model = _make_mock_model()
        tokenizer = _make_mock_tokenizer()
        chapters = self._make_chapters(4)
        progress_values: list[int] = []
        results = synthesize_chapters(
            chapters,
            model,
            tokenizer,
            SAMPLE_RATE,
            tmp_path,
            progress_callback=progress_values.append,
        )
        assert len(results) == 4
        assert progress_values == [25, 50, 75, 100]

    def test_progress_callback_single_chapter(self, tmp_path: Path):
        model = _make_mock_model()
        tokenizer = _make_mock_tokenizer()
        chapters = self._make_chapters(1)
        progress_values: list[int] = []
        synthesize_chapters(
            chapters,
            model,
            tokenizer,
            SAMPLE_RATE,
            tmp_path,
            progress_callback=progress_values.append,
        )
        assert progress_values == [100]

    def test_no_callback_no_error(self, tmp_path: Path):
        model = _make_mock_model()
        tokenizer = _make_mock_tokenizer()
        chapters = self._make_chapters(1)
        results = synthesize_chapters(
            chapters, model, tokenizer, SAMPLE_RATE, tmp_path
        )
        assert len(results) == 1

    def test_creates_output_directory(self, tmp_path: Path):
        model = _make_mock_model()
        tokenizer = _make_mock_tokenizer()
        chapters = self._make_chapters(1)
        output_dir = tmp_path / "new_dir"
        results = synthesize_chapters(
            chapters, model, tokenizer, SAMPLE_RATE, output_dir
        )
        assert output_dir.exists()
        assert len(results) == 1

    def test_results_contain_correct_chapter_numbers(self, tmp_path: Path):
        model = _make_mock_model()
        tokenizer = _make_mock_tokenizer()
        chapters = self._make_chapters(3)
        results = synthesize_chapters(
            chapters, model, tokenizer, SAMPLE_RATE, tmp_path
        )
        assert [r.chapter_number for r in results] == [1, 2, 3]

    def test_results_contain_positive_durations(self, tmp_path: Path):
        model = _make_mock_model()
        tokenizer = _make_mock_tokenizer()
        chapters = self._make_chapters(2)
        results = synthesize_chapters(
            chapters, model, tokenizer, SAMPLE_RATE, tmp_path
        )
        for result in results:
            assert result.duration_seconds > 0

    def test_synthesis_error_propagates(self, tmp_path: Path):
        model = MagicMock()
        model.device = "cpu"
        model.side_effect = RuntimeError("CUDA error")
        tokenizer = _make_mock_tokenizer()
        chapters = self._make_chapters(1)
        with pytest.raises(SynthesisError):
            synthesize_chapters(
                chapters, model, tokenizer, SAMPLE_RATE, tmp_path
            )
