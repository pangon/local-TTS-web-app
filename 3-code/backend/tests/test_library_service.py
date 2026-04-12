"""Tests for the LibraryService (TASK-library-service-create).

Covers:
- Audiobook record created with correct fields on synthesis completion
- Title derived from source filename (.txt stripped, hyphens/underscores to spaces)
- Chapter records created for each SynthesisResult
- Single-chapter case (no chapter structure detected)
- Multi-chapter case
- Job record updated with audiobook_id
- Voice and language fields are optional (nullable)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from local_tts.db import init_db
from local_tts.services.job_service import SynthesisJobResult
from local_tts.services.library_service import LibraryService, _derive_title
from local_tts.tts.synthesizer import SynthesisResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_data_dir(tmp_path: Path) -> Path:
    return tmp_path / "data"


@pytest.fixture()
def db_conn(tmp_data_dir: Path):
    conn = init_db(tmp_data_dir)
    yield conn
    conn.close()


@pytest.fixture()
def library_service(tmp_data_dir: Path, db_conn) -> LibraryService:
    """LibraryService wired to the same data dir as the test database."""
    return LibraryService(tmp_data_dir)


def _insert_job(db_conn, job_id: str) -> None:
    """Insert a minimal job record so the FK constraint is satisfied."""
    db_conn.execute(
        "INSERT INTO job (id, type, status, progress, created_at) "
        "VALUES (?, 'synthesis', 'completed', 100, datetime('now'))",
        (job_id,),
    )
    db_conn.commit()


def _make_result(
    *,
    job_id: str = "job-001",
    audiobook_id: str = "book-001",
    source_filename: str = "my-book.txt",
    model_id: str = "hexgrad/Kokoro-82M",
    voice: str | None = "af_heart",
    language: str | None = "en",
    chapter_results: list[SynthesisResult] | None = None,
) -> SynthesisJobResult:
    if chapter_results is None:
        chapter_results = [
            SynthesisResult(
                chapter_number=1,
                title="Chapter 1",
                audio_filename="chapter-01.mp3",
                duration_seconds=120.5,
            ),
        ]
    return SynthesisJobResult(
        job_id=job_id,
        audiobook_id=audiobook_id,
        source_filename=source_filename,
        model_id=model_id,
        voice=voice,
        language=language,
        chapter_results=chapter_results,
    )


# ---------------------------------------------------------------------------
# _derive_title
# ---------------------------------------------------------------------------


class TestDeriveTitle:
    def test_strips_txt_extension(self):
        assert _derive_title("my-book.txt") == "my book"

    def test_replaces_hyphens_with_spaces(self):
        assert _derive_title("the-great-gatsby.txt") == "the great gatsby"

    def test_replaces_underscores_with_spaces(self):
        assert _derive_title("my_great_book.txt") == "my great book"

    def test_mixed_separators(self):
        assert _derive_title("my-great_book.txt") == "my great book"

    def test_no_extension(self):
        assert _derive_title("mybook") == "mybook"

    def test_preserves_spaces(self):
        assert _derive_title("my book.txt") == "my book"


# ---------------------------------------------------------------------------
# create_audiobook_from_job — audiobook record
# ---------------------------------------------------------------------------


class TestCreateAudiobookRecord:
    def test_creates_audiobook_with_correct_fields(
        self, library_service: LibraryService, db_conn
    ):
        _insert_job(db_conn, "job-001")
        result = _make_result()
        library_service.create_audiobook_from_job(result)

        row = db_conn.execute(
            "SELECT id, title, source_filename, model_id, voice, language "
            "FROM audiobook WHERE id = ?",
            ("book-001",),
        ).fetchone()

        assert row is not None
        assert row[0] == "book-001"
        assert row[1] == "my book"  # derived from "my-book.txt"
        assert row[2] == "my-book.txt"
        assert row[3] == "hexgrad/Kokoro-82M"
        assert row[4] == "af_heart"
        assert row[5] == "en"

    def test_created_at_is_populated(
        self, library_service: LibraryService, db_conn
    ):
        _insert_job(db_conn, "job-001")
        result = _make_result()
        library_service.create_audiobook_from_job(result)

        row = db_conn.execute(
            "SELECT created_at FROM audiobook WHERE id = ?",
            ("book-001",),
        ).fetchone()
        assert row is not None
        assert row[0] is not None

    def test_voice_and_language_nullable(
        self, library_service: LibraryService, db_conn
    ):
        _insert_job(db_conn, "job-001")
        result = _make_result(voice=None, language=None)
        library_service.create_audiobook_from_job(result)

        row = db_conn.execute(
            "SELECT voice, language FROM audiobook WHERE id = ?",
            ("book-001",),
        ).fetchone()
        assert row[0] is None
        assert row[1] is None


# ---------------------------------------------------------------------------
# create_audiobook_from_job — chapter records
# ---------------------------------------------------------------------------


class TestCreateChapterRecords:
    def test_single_chapter_created(
        self, library_service: LibraryService, db_conn
    ):
        _insert_job(db_conn, "job-001")
        result = _make_result(
            chapter_results=[
                SynthesisResult(1, "Full Text", "chapter-01.mp3", 300.0),
            ]
        )
        library_service.create_audiobook_from_job(result)

        rows = db_conn.execute(
            "SELECT chapter_number, title, audio_filename, duration_seconds "
            "FROM chapter WHERE audiobook_id = ? ORDER BY chapter_number",
            ("book-001",),
        ).fetchall()

        assert len(rows) == 1
        assert rows[0][0] == 1
        assert rows[0][1] == "Full Text"
        assert rows[0][2] == "chapter-01.mp3"
        assert rows[0][3] == 300.0

    def test_multiple_chapters_created(
        self, library_service: LibraryService, db_conn
    ):
        _insert_job(db_conn, "job-001")
        result = _make_result(
            chapter_results=[
                SynthesisResult(1, "Introduction", "chapter-01.mp3", 60.0),
                SynthesisResult(2, "The Journey", "chapter-02.mp3", 120.0),
                SynthesisResult(3, "Conclusion", "chapter-03.mp3", 45.0),
            ]
        )
        library_service.create_audiobook_from_job(result)

        rows = db_conn.execute(
            "SELECT chapter_number, title, audio_filename, duration_seconds "
            "FROM chapter WHERE audiobook_id = ? ORDER BY chapter_number",
            ("book-001",),
        ).fetchall()

        assert len(rows) == 3
        assert rows[0] == (1, "Introduction", "chapter-01.mp3", 60.0)
        assert rows[1] == (2, "The Journey", "chapter-02.mp3", 120.0)
        assert rows[2] == (3, "Conclusion", "chapter-03.mp3", 45.0)

    def test_chapter_ids_are_unique_uuids(
        self, library_service: LibraryService, db_conn
    ):
        _insert_job(db_conn, "job-001")
        result = _make_result(
            chapter_results=[
                SynthesisResult(1, "Ch 1", "chapter-01.mp3", 60.0),
                SynthesisResult(2, "Ch 2", "chapter-02.mp3", 60.0),
            ]
        )
        library_service.create_audiobook_from_job(result)

        ids = db_conn.execute(
            "SELECT id FROM chapter WHERE audiobook_id = ?",
            ("book-001",),
        ).fetchall()

        assert len(ids) == 2
        assert ids[0][0] != ids[1][0]
        # Basic UUID format check (36 chars with hyphens)
        for (cid,) in ids:
            assert len(cid) == 36


# ---------------------------------------------------------------------------
# create_audiobook_from_job — job linkage
# ---------------------------------------------------------------------------


class TestJobLinkage:
    def test_job_audiobook_id_updated(
        self, library_service: LibraryService, db_conn
    ):
        _insert_job(db_conn, "job-001")
        result = _make_result()
        library_service.create_audiobook_from_job(result)

        row = db_conn.execute(
            "SELECT audiobook_id FROM job WHERE id = ?",
            ("job-001",),
        ).fetchone()

        assert row is not None
        assert row[0] == "book-001"

    def test_job_audiobook_id_was_null_before(
        self, library_service: LibraryService, db_conn
    ):
        _insert_job(db_conn, "job-001")

        # Verify it starts as NULL
        row = db_conn.execute(
            "SELECT audiobook_id FROM job WHERE id = ?",
            ("job-001",),
        ).fetchone()
        assert row[0] is None

        result = _make_result()
        library_service.create_audiobook_from_job(result)

        # Now it should be set
        row = db_conn.execute(
            "SELECT audiobook_id FROM job WHERE id = ?",
            ("job-001",),
        ).fetchone()
        assert row[0] == "book-001"


# ---------------------------------------------------------------------------
# Transactional behavior
# ---------------------------------------------------------------------------


class TestTransactionalBehavior:
    def test_all_records_committed_atomically(
        self, library_service: LibraryService, db_conn
    ):
        """Audiobook, chapters, and job linkage should all be present after success."""
        _insert_job(db_conn, "job-001")
        result = _make_result(
            chapter_results=[
                SynthesisResult(1, "Ch 1", "chapter-01.mp3", 60.0),
                SynthesisResult(2, "Ch 2", "chapter-02.mp3", 90.0),
            ]
        )
        library_service.create_audiobook_from_job(result)

        audiobook = db_conn.execute(
            "SELECT id FROM audiobook WHERE id = ?", ("book-001",)
        ).fetchone()
        chapters = db_conn.execute(
            "SELECT id FROM chapter WHERE audiobook_id = ?", ("book-001",)
        ).fetchall()
        job_link = db_conn.execute(
            "SELECT audiobook_id FROM job WHERE id = ?", ("job-001",)
        ).fetchone()

        assert audiobook is not None
        assert len(chapters) == 2
        assert job_link[0] == "book-001"
