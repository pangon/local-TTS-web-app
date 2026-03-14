"""Chapter structure detection and text splitting.

Detects chapter boundaries in plain text using common heading patterns
and splits the text into labeled chunks. When no chapter structure is
detected, the entire text is returned as a single chunk.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Chapter:
    """A detected chapter with its number, title, and text content."""

    number: int
    title: str
    text: str


# Patterns that indicate a chapter heading, tested in order.
# Each pattern is compiled with IGNORECASE and MULTILINE.
_CHAPTER_PATTERNS: list[re.Pattern[str]] = [
    # "Chapter 1: Title", "Chapter 1 - Title", "Chapter 1 Title", "Chapter 1"
    re.compile(
        r"^chapter[^\S\n]+(\d+)[^\S\n]*[:\-\u2013\u2014.]?[^\S\n]*(.*)",
        re.IGNORECASE | re.MULTILINE,
    ),
    # "Chapter One: Title" (word-form numbers)
    re.compile(
        r"^chapter[^\S\n]+(one|two|three|four|five|six|seven|eight|nine|ten"
        r"|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen"
        r"|eighteen|nineteen|twenty"
        r"(?:[^\S\n]*[-\u2013][^\S\n]*(?:one|two|three|four|five|six|seven|eight|nine))?)"
        r"[^\S\n]*[:\-\u2013\u2014.]?[^\S\n]*(.*)",
        re.IGNORECASE | re.MULTILINE,
    ),
    # "Part 1: Title", "Part I: Title"
    re.compile(
        r"^part[^\S\n]+(\d+|[IVXLC]+)[^\S\n]*[:\-\u2013\u2014.]?[^\S\n]*(.*)",
        re.IGNORECASE | re.MULTILINE,
    ),
]

_WORD_TO_NUM: dict[str, int] = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20,
    "twenty-one": 21, "twenty-two": 22, "twenty-three": 23,
    "twenty-four": 24, "twenty-five": 25, "twenty-six": 26,
    "twenty-seven": 27, "twenty-eight": 28, "twenty-nine": 29,
}

_ROMAN_VALUES: dict[str, int] = {
    "I": 1, "V": 5, "X": 10, "L": 50, "C": 100,
}


def _roman_to_int(s: str) -> int | None:
    """Convert a Roman numeral string to an integer, or None if invalid."""
    s = s.upper().strip()
    if not s or not all(c in _ROMAN_VALUES for c in s):
        return None
    total = 0
    prev = 0
    for char in reversed(s):
        val = _ROMAN_VALUES[char]
        if val < prev:
            total -= val
        else:
            total += val
        prev = val
    return total if total > 0 else None


def _parse_chapter_number(raw: str) -> int | None:
    """Parse a chapter number from a digit string, word, or Roman numeral."""
    raw = raw.strip().lower()
    if raw.isdigit():
        return int(raw)
    if raw in _WORD_TO_NUM:
        return _WORD_TO_NUM[raw]
    # Try with hyphens normalized
    normalized = re.sub(r"\s+", "-", raw)
    if normalized in _WORD_TO_NUM:
        return _WORD_TO_NUM[normalized]
    return _roman_to_int(raw)


def parse_chapters(text: str) -> list[Chapter]:
    """Parse text into chapters based on detected heading patterns.

    Scans the text for common chapter heading patterns. When chapter
    headings are found, the text is split at each heading and each
    section becomes a Chapter with its detected number and title.

    When no chapter headings are detected, a single Chapter is returned
    containing the entire text with title "Chapter 1".

    Args:
        text: The full input text to parse.

    Returns:
        A list of Chapter objects, 1-based numbered in order of appearance.
    """
    text = text.strip()
    if not text:
        return [Chapter(number=1, title="Chapter 1", text="")]

    # Try each pattern and use the first one that finds matches
    for pattern in _CHAPTER_PATTERNS:
        matches = list(pattern.finditer(text))
        if len(matches) >= 2:
            return _split_by_matches(text, matches, pattern)
        # Single match: only treat as chapter structure if it appears
        # near the beginning (within first 5% of text or 200 chars)
        if len(matches) == 1:
            threshold = max(200, len(text) // 20)
            if matches[0].start() <= threshold:
                return _split_by_matches(text, matches, pattern)

    # No chapter structure detected — return entire text as single chapter
    return [Chapter(number=1, title="Chapter 1", text=text)]


def _split_by_matches(
    text: str,
    matches: list[re.Match[str]],
    pattern: re.Pattern[str],
) -> list[Chapter]:
    """Split text into chapters at the matched heading positions."""
    chapters: list[Chapter] = []

    # If there's significant text before the first match, include it as a preamble
    preamble = text[: matches[0].start()].strip()
    if preamble and len(preamble) > 100:
        chapters.append(Chapter(number=0, title="Preamble", text=preamble))

    for i, match in enumerate(matches):
        raw_num = match.group(1)
        raw_title = match.group(2).strip() if match.group(2) else ""

        parsed_num = _parse_chapter_number(raw_num)
        chapter_number = parsed_num if parsed_num is not None else i + 1

        # Determine chapter text: from end of heading line to start of next match
        heading_end = match.end()
        if i + 1 < len(matches):
            chapter_text = text[heading_end: matches[i + 1].start()]
        else:
            chapter_text = text[heading_end:]
        chapter_text = chapter_text.strip()

        # Build title
        if raw_title:
            title = raw_title.rstrip(".")
        else:
            title = f"Chapter {chapter_number}"

        chapters.append(Chapter(
            number=chapter_number,
            title=title,
            text=chapter_text,
        ))

    # Renumber sequentially (1-based), preserving preamble as chapter 0 if present
    return _renumber_chapters(chapters)


def _renumber_chapters(chapters: list[Chapter]) -> list[Chapter]:
    """Ensure chapters are sequentially numbered starting from 1.

    If a preamble (number=0) exists, it becomes chapter 1 and all
    subsequent chapters are shifted accordingly.
    """
    result: list[Chapter] = []
    for i, ch in enumerate(chapters):
        new_number = i + 1
        title = ch.title
        # Update generic titles to match new numbering
        if ch.number == 0 and ch.title == "Preamble":
            title = "Preamble"
        elif title == f"Chapter {ch.number}" and new_number != ch.number:
            title = f"Chapter {new_number}"
        result.append(Chapter(number=new_number, title=title, text=ch.text))
    return result
