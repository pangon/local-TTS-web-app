"""Tests for the synthesizer module.

Covers: sentence splitting, single-segment synthesis, MP3 encoding,
chapter synthesis, multi-chapter synthesis with progress callbacks.
All GPU/model dependencies are mocked via adapter fakes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

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


class _FakeAdapter:
    """Fake model adapter for testing synthesis."""

    def __init__(self, sr: int = SAMPLE_RATE) -> None:
        self._sr = sr
        self.call_count = 0

    def load(self, model_id: str, device: str) -> None:
        pass

    def synthesize(self, text: str, **kwargs: Any) -> np.ndarray:
        self.call_count += 1
        num_samples = self._sr // 10  # 0.1 seconds of audio
        t = np.linspace(0, 0.1, num_samples, dtype=np.float32)
        return np.sin(2 * np.pi * 440 * t).astype(np.float32)

    @property
    def sample_rate(self) -> int:
        return self._sr

    def unload(self) -> None:
        pass


class _FailingAdapter:
    """Adapter whose synthesize always fails."""

    def load(self, model_id: str, device: str) -> None:
        pass

    def synthesize(self, text: str, **kwargs: Any) -> np.ndarray:
        raise RuntimeError("CUDA error")

    @property
    def sample_rate(self) -> int:
        return SAMPLE_RATE

    def unload(self) -> None:
        pass


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
        adapter = _FakeAdapter()
        result = synthesize_segment("Hello world", adapter)
        assert isinstance(result, np.ndarray)
        assert result.dtype == np.float32
        assert len(result) > 0

    def test_delegates_to_adapter(self):
        adapter = _FakeAdapter()
        synthesize_segment("Test text", adapter)
        assert adapter.call_count == 1

    def test_raises_synthesis_error_on_failure(self):
        adapter = _FailingAdapter()
        with pytest.raises(SynthesisError, match="Failed to synthesize"):
            synthesize_segment("Test", adapter)


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
        adapter = _FakeAdapter()
        output = tmp_path / "chapter.mp3"
        duration = synthesize_chapter(
            "Hello world. How are you?", adapter, output
        )
        assert output.exists()
        assert duration > 0

    def test_empty_text_produces_silence(self, tmp_path: Path):
        adapter = _FakeAdapter()
        output = tmp_path / "empty.mp3"
        duration = synthesize_chapter("", adapter, output)
        assert output.exists()
        assert duration > 0
        # Adapter should not have been called for empty text
        assert adapter.call_count == 0

    def test_multiple_sentences_concatenated(self, tmp_path: Path):
        adapter = _FakeAdapter()
        output = tmp_path / "multi.mp3"
        duration = synthesize_chapter(
            "First sentence. Second sentence. Third sentence.",
            adapter,
            output,
        )
        assert output.exists()
        # Adapter should be called 3 times (once per sentence)
        assert adapter.call_count == 3
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
        adapter = _FakeAdapter()
        chapters = self._make_chapters(3)
        results = synthesize_chapters(chapters, adapter, tmp_path)
        assert len(results) == 3
        for result in results:
            mp3_path = tmp_path / result.audio_filename
            assert mp3_path.exists()
            assert mp3_path.stat().st_size > 0

    def test_filenames_follow_convention(self, tmp_path: Path):
        adapter = _FakeAdapter()
        chapters = self._make_chapters(2)
        results = synthesize_chapters(chapters, adapter, tmp_path)
        assert results[0].audio_filename == "chapter-01.mp3"
        assert results[1].audio_filename == "chapter-02.mp3"

    def test_progress_callback_called(self, tmp_path: Path):
        adapter = _FakeAdapter()
        chapters = self._make_chapters(4)
        progress_values: list[int] = []
        results = synthesize_chapters(
            chapters,
            adapter,
            tmp_path,
            progress_callback=progress_values.append,
        )
        assert len(results) == 4
        assert progress_values == [25, 50, 75, 100]

    def test_progress_callback_single_chapter(self, tmp_path: Path):
        adapter = _FakeAdapter()
        chapters = self._make_chapters(1)
        progress_values: list[int] = []
        synthesize_chapters(
            chapters,
            adapter,
            tmp_path,
            progress_callback=progress_values.append,
        )
        assert progress_values == [100]

    def test_no_callback_no_error(self, tmp_path: Path):
        adapter = _FakeAdapter()
        chapters = self._make_chapters(1)
        results = synthesize_chapters(chapters, adapter, tmp_path)
        assert len(results) == 1

    def test_creates_output_directory(self, tmp_path: Path):
        adapter = _FakeAdapter()
        chapters = self._make_chapters(1)
        output_dir = tmp_path / "new_dir"
        results = synthesize_chapters(chapters, adapter, output_dir)
        assert output_dir.exists()
        assert len(results) == 1

    def test_results_contain_correct_chapter_numbers(self, tmp_path: Path):
        adapter = _FakeAdapter()
        chapters = self._make_chapters(3)
        results = synthesize_chapters(chapters, adapter, tmp_path)
        assert [r.chapter_number for r in results] == [1, 2, 3]

    def test_results_contain_positive_durations(self, tmp_path: Path):
        adapter = _FakeAdapter()
        chapters = self._make_chapters(2)
        results = synthesize_chapters(chapters, adapter, tmp_path)
        for result in results:
            assert result.duration_seconds > 0

    def test_synthesis_error_propagates(self, tmp_path: Path):
        adapter = _FailingAdapter()
        chapters = self._make_chapters(1)
        with pytest.raises(SynthesisError):
            synthesize_chapters(chapters, adapter, tmp_path)
