"""Text-to-MP3 synthesis with progress callbacks.

Converts text chapters to MP3 audio files using a model adapter on GPU.
Text is split into sentences for optimal synthesis quality, and sentences
are synthesized individually then concatenated. Requires ffmpeg installed
on the system for MP3 encoding via pydub.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

import numpy as np
from pydub import AudioSegment

from local_tts.tts.chapter_parser import Chapter

if TYPE_CHECKING:
    from local_tts.tts.adapters import ModelAdapter

logger = logging.getLogger(__name__)

# Silence duration (seconds) inserted between sentences in synthesized audio.
_INTER_SENTENCE_SILENCE_S = 0.3


class SynthesisError(Exception):
    """Raised when synthesis fails."""


@dataclass(frozen=True)
class SynthesisResult:
    """Result of synthesizing one chapter to an MP3 file."""

    chapter_number: int
    title: str
    audio_filename: str
    duration_seconds: float


def split_into_sentences(text: str) -> list[str]:
    """Split text into sentences suitable for individual synthesis.

    Splits on sentence-ending punctuation (.!?) followed by whitespace.
    Preserves sentences that contain no such punctuation as a single chunk.
    """
    text = text.strip()
    if not text:
        return []
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sentences if s.strip()]


def synthesize_segment(
    text: str,
    adapter: ModelAdapter,
    **kwargs: Any,
) -> np.ndarray:
    """Synthesize a single text segment to a waveform numpy array.

    Args:
        text: Text to synthesize (typically one sentence).
        adapter: Loaded model adapter providing inference.
        **kwargs: Passed through to the adapter (voice, language, etc.).

    Returns:
        1-D float32 numpy array of audio samples.

    Raises:
        SynthesisError: If inference fails.
    """
    try:
        return adapter.synthesize(text, **kwargs)
    except Exception as exc:
        raise SynthesisError(f"Failed to synthesize text segment: {exc}") from exc


def encode_to_mp3(
    waveform: np.ndarray,
    sample_rate: int,
    output_path: Path,
) -> float:
    """Encode a waveform array to an MP3 file.

    Args:
        waveform: 1-D float32 numpy array with values in [-1, 1].
        sample_rate: Audio sample rate in Hz.
        output_path: Path where the MP3 file will be written.

    Returns:
        Duration of the audio in seconds.
    """
    audio_int16 = (np.clip(waveform, -1.0, 1.0) * 32767).astype(np.int16)

    audio_segment = AudioSegment(
        data=audio_int16.tobytes(),
        sample_width=2,
        frame_rate=sample_rate,
        channels=1,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    audio_segment.export(str(output_path), format="mp3")

    return len(audio_segment) / 1000.0


def synthesize_chapter(
    text: str,
    adapter: ModelAdapter,
    output_path: Path,
    on_sentence_done: Callable[[int, int], None] | None = None,
    **kwargs: Any,
) -> float:
    """Synthesize a chapter's text to an MP3 file.

    Splits text into sentences, synthesizes each individually, concatenates
    with short silence gaps, and encodes to MP3.

    Args:
        text: Full chapter text.
        adapter: Loaded model adapter providing inference and sample rate.
        output_path: Path where the MP3 file will be written.
        on_sentence_done: Called after each sentence with ``(completed, total)``
            where *completed* is the 1-based count of sentences done so far
            and *total* is the number of sentences in the chapter.
        **kwargs: Passed through to the adapter (voice, language, etc.).

    Returns:
        Duration of the resulting audio in seconds.

    Raises:
        SynthesisError: If synthesis or encoding fails.
    """
    sample_rate = adapter.sample_rate
    sentences = split_into_sentences(text)

    if not sentences:
        # Empty chapter: produce 1 second of silence
        waveform = np.zeros(sample_rate, dtype=np.float32)
        return encode_to_mp3(waveform, sample_rate, output_path)

    silence = np.zeros(
        int(sample_rate * _INTER_SENTENCE_SILENCE_S), dtype=np.float32
    )

    total_sentences = len(sentences)
    waveforms: list[np.ndarray] = []
    for i, sentence in enumerate(sentences):
        waveform = synthesize_segment(sentence, adapter, **kwargs)
        waveforms.append(waveform)
        waveforms.append(silence)
        if on_sentence_done:
            on_sentence_done(i + 1, total_sentences)

    # Remove trailing silence
    if waveforms:
        waveforms.pop()

    combined = np.concatenate(waveforms)
    return encode_to_mp3(combined, sample_rate, output_path)


def synthesize_chapters(
    chapters: list[Chapter],
    adapter: ModelAdapter,
    output_dir: Path,
    progress_callback: Callable[[int], None] | None = None,
    **kwargs: Any,
) -> list[SynthesisResult]:
    """Synthesize all chapters to MP3 files with progress reporting.

    Each chapter is written to ``output_dir/chapter-NN.mp3`` where NN is the
    zero-padded chapter number.

    Progress is reported as percentage of total characters processed, updated
    after each sentence is synthesized for fine-grained feedback.

    Args:
        chapters: Chapters to synthesize (from chapter_parser.parse_chapters).
        adapter: Loaded model adapter providing inference and sample rate.
        output_dir: Directory where MP3 files will be written.
        progress_callback: Called with overall percentage (0-100) as characters
            are processed.
        **kwargs: Passed through to the adapter (voice, language, etc.).

    Returns:
        List of SynthesisResult, one per chapter.

    Raises:
        SynthesisError: If synthesis of any chapter fails.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    results: list[SynthesisResult] = []
    total = len(chapters)
    total_chars = sum(len(ch.text) for ch in chapters)
    chars_done = 0
    last_reported = -1

    for i, chapter in enumerate(chapters):
        filename = f"chapter-{chapter.number:02d}.mp3"
        output_path = output_dir / filename
        ch_chars = len(chapter.text)

        # Build per-chapter sentence callback that maps sentence progress
        # to overall character-based percentage.
        sentence_cb: Callable[[int, int], None] | None = None
        if progress_callback and total_chars > 0:

            def _on_sentence_done(
                done: int,
                sentence_total: int,
                *,
                _ch_chars: int = ch_chars,
            ) -> None:
                nonlocal last_reported
                pct = int(
                    ((chars_done + _ch_chars * done / sentence_total)
                     / total_chars)
                    * 100
                )
                if pct != last_reported:
                    last_reported = pct
                    progress_callback(pct)

            sentence_cb = _on_sentence_done

        logger.info(
            "Synthesizing chapter %d/%d: %s", i + 1, total, chapter.title
        )

        duration = synthesize_chapter(
            text=chapter.text,
            adapter=adapter,
            output_path=output_path,
            on_sentence_done=sentence_cb,
            **kwargs,
        )

        chars_done += ch_chars

        results.append(
            SynthesisResult(
                chapter_number=chapter.number,
                title=chapter.title,
                audio_filename=filename,
                duration_seconds=duration,
            )
        )

        logger.info(
            "Chapter %d/%d complete (%.1fs audio)", i + 1, total, duration
        )

    return results
