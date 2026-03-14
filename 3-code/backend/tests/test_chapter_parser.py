"""Tests for the chapter parser module."""

import pytest

from local_tts.tts.chapter_parser import Chapter, parse_chapters


class TestNoChapterStructure:
    """AC: Given text with no recognizable chapter markers,
    the system produces a single chapter."""

    def test_plain_text_returns_single_chapter(self):
        text = "This is a simple text without any chapter markers."
        result = parse_chapters(text)
        assert len(result) == 1
        assert result[0].number == 1
        assert result[0].title == "Chapter 1"
        assert result[0].text == text

    def test_empty_text_returns_single_chapter(self):
        result = parse_chapters("")
        assert len(result) == 1
        assert result[0].number == 1
        assert result[0].text == ""

    def test_whitespace_only_returns_single_chapter(self):
        result = parse_chapters("   \n\n  ")
        assert len(result) == 1
        assert result[0].number == 1

    def test_text_with_word_chapter_in_sentence_not_detected(self):
        text = (
            "In this chapter we discuss the basics.\n"
            "The next chapter covers advanced topics.\n"
            "Each chapter builds on the previous one."
        )
        result = parse_chapters(text)
        assert len(result) == 1


class TestChapterNumberDetection:
    """AC: Given text with recognizable chapter markers,
    the system produces one chapter per detected marker."""

    def test_chapter_with_arabic_numbers(self):
        text = (
            "Chapter 1: The Beginning\n"
            "Once upon a time...\n\n"
            "Chapter 2: The Middle\n"
            "Things got complicated...\n\n"
            "Chapter 3: The End\n"
            "And they lived happily."
        )
        result = parse_chapters(text)
        assert len(result) == 3
        assert result[0].number == 1
        assert result[1].number == 2
        assert result[2].number == 3

    def test_chapter_with_word_numbers(self):
        text = (
            "Chapter One: The Beginning\n"
            "Once upon a time...\n\n"
            "Chapter Two: The Middle\n"
            "Things got complicated...\n\n"
            "Chapter Three: The End\n"
            "And they lived happily."
        )
        result = parse_chapters(text)
        assert len(result) == 3
        assert result[0].number == 1
        assert result[1].number == 2
        assert result[2].number == 3

    def test_part_with_roman_numerals(self):
        text = (
            "Part I: The Beginning\n"
            "Once upon a time...\n\n"
            "Part II: The Middle\n"
            "Things got complicated...\n\n"
            "Part III: The End\n"
            "And they lived happily."
        )
        result = parse_chapters(text)
        assert len(result) == 3
        assert result[0].number == 1
        assert result[1].number == 2
        assert result[2].number == 3

    def test_part_with_arabic_numbers(self):
        text = (
            "Part 1 The Start\n"
            "First section content.\n\n"
            "Part 2 The Continuation\n"
            "Second section content."
        )
        result = parse_chapters(text)
        assert len(result) == 2


class TestChapterTitles:
    """AC: Each chapter is labeled with its chapter number or title."""

    def test_title_extracted_with_colon_separator(self):
        text = (
            "Chapter 1: The Beginning\n"
            "Content here.\n\n"
            "Chapter 2: The End\n"
            "More content."
        )
        result = parse_chapters(text)
        assert result[0].title == "The Beginning"
        assert result[1].title == "The End"

    def test_title_extracted_with_dash_separator(self):
        text = (
            "Chapter 1 - The Beginning\n"
            "Content here.\n\n"
            "Chapter 2 - The End\n"
            "More content."
        )
        result = parse_chapters(text)
        assert result[0].title == "The Beginning"
        assert result[1].title == "The End"

    def test_no_title_uses_chapter_number(self):
        text = (
            "Chapter 1\n"
            "Content of the first chapter.\n\n"
            "Chapter 2\n"
            "Content of the second chapter."
        )
        result = parse_chapters(text)
        assert result[0].title == "Chapter 1"
        assert result[1].title == "Chapter 2"

    def test_part_titles_extracted(self):
        text = (
            "Part I: The Foundation\n"
            "Content here.\n\n"
            "Part II: The Structure\n"
            "More content."
        )
        result = parse_chapters(text)
        assert result[0].title == "The Foundation"
        assert result[1].title == "The Structure"


class TestChapterTextContent:
    """Verify that chapter text content is correctly extracted."""

    def test_text_between_chapters_is_captured(self):
        text = (
            "Chapter 1: Intro\n"
            "First chapter text.\n"
            "More first chapter text.\n\n"
            "Chapter 2: Body\n"
            "Second chapter text."
        )
        result = parse_chapters(text)
        assert "First chapter text." in result[0].text
        assert "More first chapter text." in result[0].text
        assert "Second chapter text." in result[1].text

    def test_last_chapter_captures_remaining_text(self):
        text = (
            "Chapter 1: Start\n"
            "First part.\n\n"
            "Chapter 2: End\n"
            "Second part.\n"
            "Final paragraph."
        )
        result = parse_chapters(text)
        assert "Final paragraph." in result[1].text

    def test_chapter_text_is_stripped(self):
        text = (
            "Chapter 1: Intro\n"
            "  \n"
            "  Content here.  \n"
            "  \n\n"
            "Chapter 2: More\n"
            "Next content."
        )
        result = parse_chapters(text)
        assert result[0].text == "Content here."


class TestCaseInsensitivity:
    """Chapter headings should be detected regardless of case."""

    def test_uppercase_chapter(self):
        text = (
            "CHAPTER 1: THE START\n"
            "First content.\n\n"
            "CHAPTER 2: THE END\n"
            "Second content."
        )
        result = parse_chapters(text)
        assert len(result) == 2
        assert result[0].title == "THE START"

    def test_mixed_case_chapter(self):
        text = (
            "Chapter 1: First\n"
            "Content one.\n\n"
            "CHAPTER 2: Second\n"
            "Content two."
        )
        result = parse_chapters(text)
        assert len(result) == 2


class TestPreambleHandling:
    """Text before the first chapter heading is handled correctly."""

    def test_short_preamble_is_discarded(self):
        text = (
            "Title of Book\n\n"
            "Chapter 1: First\n"
            "Content one.\n\n"
            "Chapter 2: Second\n"
            "Content two."
        )
        result = parse_chapters(text)
        assert len(result) == 2
        assert result[0].number == 1

    def test_long_preamble_becomes_chapter(self):
        preamble = "A" * 150
        text = (
            f"{preamble}\n\n"
            "Chapter 1: First\n"
            "Content one.\n\n"
            "Chapter 2: Second\n"
            "Content two."
        )
        result = parse_chapters(text)
        assert len(result) == 3
        assert result[0].title == "Preamble"
        assert result[0].number == 1
        assert result[1].number == 2
        assert result[2].number == 3


class TestSingleChapterHeading:
    """A single chapter heading near the start is treated as structure."""

    def test_single_heading_at_start_returns_one_chapter(self):
        text = (
            "Chapter 1: The Story\n"
            "This is the entire story told in one chapter. "
            "It has lots of content and goes on for a while."
        )
        result = parse_chapters(text)
        assert len(result) == 1
        assert result[0].title == "The Story"
        assert result[0].number == 1


class TestChapterDataclass:
    """Verify Chapter dataclass behavior."""

    def test_chapter_is_frozen(self):
        ch = Chapter(number=1, title="Test", text="Content")
        with pytest.raises(AttributeError):
            ch.number = 2  # type: ignore[misc]

    def test_chapter_equality(self):
        a = Chapter(number=1, title="Test", text="Content")
        b = Chapter(number=1, title="Test", text="Content")
        assert a == b
