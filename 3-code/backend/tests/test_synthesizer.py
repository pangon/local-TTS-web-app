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
    """Chunking is one chunk per line — splitting on newlines only, following
    the preprocessing pipeline's segmentation (no punctuation logic)."""

    def test_splits_on_newlines(self):
        text = "Prima frase.\nSeconda frase.\nTerza frase."
        result = split_into_sentences(text)
        assert result == ["Prima frase.", "Seconda frase.", "Terza frase."]

    def test_single_line_with_multiple_sentences_is_one_chunk(self):
        # Punctuation is deliberately NOT a split point: a line stays whole.
        text = "Prima frase. Seconda frase. Terza frase."
        result = split_into_sentences(text)
        assert result == ["Prima frase. Seconda frase. Terza frase."]

    def test_single_line_no_punctuation(self):
        assert split_into_sentences("Solo un titolo") == ["Solo un titolo"]

    def test_empty_text(self):
        assert split_into_sentences("") == []

    def test_whitespace_only(self):
        assert split_into_sentences("   ") == []

    def test_blank_lines_are_dropped(self):
        text = "Uno.\n\n\nDue."
        assert split_into_sentences(text) == ["Uno.", "Due."]

    def test_each_line_is_stripped(self):
        text = "  Uno.  \n\t Due. \n"
        assert split_into_sentences(text) == ["Uno.", "Due."]

    def test_dialogue_tag_is_its_own_chunk(self):
        # The whole point of the change: a dialogue tag isolated onto its own
        # line by preprocessing becomes a distinct synthesis chunk.
        text = 'Preparatevi all\'atterraggio"\ncomunicò.'
        assert split_into_sentences(text) == [
            'Preparatevi all\'atterraggio"',
            "comunicò.",
        ]


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

    def test_forwards_kwargs_to_adapter(self):
        adapter = MagicMock()
        adapter.synthesize.return_value = np.zeros(100, dtype=np.float32)
        synthesize_segment("Ciao", adapter, voice="if_sara", language="i")
        adapter.synthesize.assert_called_once_with(
            "Ciao", voice="if_sara", language="i",
        )


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
            "First sentence.\nSecond sentence.\nThird sentence.",
            adapter,
            output,
        )
        assert output.exists()
        # Adapter should be called 3 times (once per line/chunk)
        assert adapter.call_count == 3
        assert duration > 0

    def test_on_sentence_done_callback(self, tmp_path: Path):
        adapter = _FakeAdapter()
        output = tmp_path / "cb.mp3"
        calls: list[tuple[int, int]] = []
        synthesize_chapter(
            "First.\nSecond.\nThird.",
            adapter,
            output,
            on_sentence_done=lambda done, total: calls.append((done, total)),
        )
        assert calls == [(1, 3), (2, 3), (3, 3)]

    def test_on_sentence_done_not_called_for_empty_text(self, tmp_path: Path):
        adapter = _FakeAdapter()
        output = tmp_path / "empty_cb.mp3"
        calls: list[tuple[int, int]] = []
        synthesize_chapter(
            "",
            adapter,
            output,
            on_sentence_done=lambda done, total: calls.append((done, total)),
        )
        assert calls == []


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

    def test_progress_character_based_multi_sentence(self, tmp_path: Path):
        """Progress updates per sentence within a single chapter."""
        adapter = _FakeAdapter()
        # 3 lines of roughly equal length → ~33%, ~66%, 100%
        chapters = [Chapter(number=1, title="Ch1", text="AAAA.\nBBBB.\nCCCC.")]
        progress_values: list[int] = []
        synthesize_chapters(
            chapters, adapter, tmp_path,
            progress_callback=progress_values.append,
        )
        assert len(progress_values) == 3
        assert progress_values[-1] == 100
        # Each value should increase
        assert progress_values == sorted(progress_values)

    def test_progress_character_based_uneven_chapters(self, tmp_path: Path):
        """Longer chapters get a bigger share of the progress bar."""
        adapter = _FakeAdapter()
        # Chapter 1: short (10 chars), Chapter 2: long (30 chars)
        chapters = [
            Chapter(number=1, title="Short", text="Short one."),
            Chapter(number=2, title="Long", text="A much longer chapter text here for testing progress."),
        ]
        progress_values: list[int] = []
        synthesize_chapters(
            chapters, adapter, tmp_path,
            progress_callback=progress_values.append,
        )
        # Short chapter (10 chars) should report a small percentage, not 50%
        assert progress_values[0] < 30
        assert progress_values[-1] == 100

    def test_progress_deduplicates_same_percentage(self, tmp_path: Path):
        """Duplicate percentage values are not reported twice."""
        adapter = _FakeAdapter()
        # 200 single-char lines → many will map to the same percentage
        text = "\n".join("X." for _ in range(200))
        chapters = [Chapter(number=1, title="Ch1", text=text)]
        progress_values: list[int] = []
        synthesize_chapters(
            chapters, adapter, tmp_path,
            progress_callback=progress_values.append,
        )
        # No duplicates
        assert len(progress_values) == len(set(progress_values))
        assert progress_values[-1] == 100

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
