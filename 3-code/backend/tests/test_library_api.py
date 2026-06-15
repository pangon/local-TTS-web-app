"""Tests for the audiobook library API (TASK-library-api).

Covers:
- GET /api/v1/audiobooks — list audiobooks with chapter counts (REQ-F-library-listing)
- Empty library returns an empty list
- GET /api/v1/audiobooks/{id} — audiobook detail with chapter list
- GET unknown audiobook returns 404
- DELETE /api/v1/audiobooks/{id} — removes record, cascades chapters and
  playback positions, nulls the linked job, and deletes audio files on disk
  (REQ-F-delete-audiobook)
- DELETE unknown audiobook returns 404

These are integration tests: they run against a real SQLite database and a
real LibraryService, exercising the actual cascade and file-deletion behavior.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from local_tts.api.audiobooks import router
from local_tts.db import get_connection, init_db
from local_tts.services.library_service import LibraryService


# ---------------------------------------------------------------------------
# Fixtures & helpers
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
def app(tmp_data_dir: Path, db_conn) -> FastAPI:
    """Minimal app exposing the audiobooks router backed by a real service."""
    application = FastAPI()
    application.include_router(router, prefix="/api/v1")
    application.state.library_service = LibraryService(tmp_data_dir)
    return application


def _seed_audiobook(
    conn,
    data_dir: Path,
    *,
    audiobook_id: str,
    title: str = "My Book",
    source_filename: str = "my-book.txt",
    model_id: str = "hexgrad/Kokoro-82M",
    voice: str | None = "if_sara",
    language: str | None = "it",
    created_at: str = "2026-06-01 10:00:00",
    chapters: list[tuple[int, str, float]] | None = None,
    with_audio_files: bool = True,
) -> None:
    """Insert an audiobook + chapters and (optionally) write audio files on disk."""
    if chapters is None:
        chapters = [(1, "Chapter 1", 120.5), (2, "Chapter 2", 98.3)]

    conn.execute(
        "INSERT INTO audiobook "
        "(id, title, source_filename, model_id, voice, language, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (audiobook_id, title, source_filename, model_id, voice, language, created_at),
    )

    audio_dir = data_dir / "audiobooks" / audiobook_id
    if with_audio_files:
        audio_dir.mkdir(parents=True, exist_ok=True)

    for number, ch_title, duration in chapters:
        audio_filename = f"chapter-{number:02d}.mp3"
        conn.execute(
            "INSERT INTO chapter "
            "(id, audiobook_id, chapter_number, title, audio_filename, duration_seconds) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (f"{audiobook_id}-ch{number}", audiobook_id, number, ch_title, audio_filename, duration),
        )
        if with_audio_files:
            (audio_dir / audio_filename).write_bytes(b"fake-mp3-data")

    conn.commit()


# ---------------------------------------------------------------------------
# GET /audiobooks — listing
# ---------------------------------------------------------------------------


class TestListAudiobooks:
    @pytest.mark.anyio
    async def test_empty_library_returns_empty_list(self, app: FastAPI):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/audiobooks")

        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.anyio
    async def test_lists_audiobook_with_metadata_and_chapter_count(
        self, app: FastAPI, db_conn, tmp_data_dir: Path
    ):
        _seed_audiobook(db_conn, tmp_data_dir, audiobook_id="book-001")

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/audiobooks")

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        entry = body[0]
        assert entry["id"] == "book-001"
        assert entry["title"] == "My Book"
        assert entry["source_filename"] == "my-book.txt"
        assert entry["created_at"] == "2026-06-01 10:00:00"
        assert entry["chapter_count"] == 2

    @pytest.mark.anyio
    async def test_audiobook_with_no_chapters_reports_zero_count(
        self, app: FastAPI, db_conn, tmp_data_dir: Path
    ):
        _seed_audiobook(db_conn, tmp_data_dir, audiobook_id="book-001", chapters=[])

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/audiobooks")

        body = response.json()
        assert body[0]["chapter_count"] == 0

    @pytest.mark.anyio
    async def test_audiobooks_ordered_newest_first(
        self, app: FastAPI, db_conn, tmp_data_dir: Path
    ):
        _seed_audiobook(
            db_conn, tmp_data_dir, audiobook_id="older",
            created_at="2026-05-01 10:00:00",
        )
        _seed_audiobook(
            db_conn, tmp_data_dir, audiobook_id="newer",
            created_at="2026-06-10 10:00:00",
        )

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/audiobooks")

        ids = [e["id"] for e in response.json()]
        assert ids == ["newer", "older"]


# ---------------------------------------------------------------------------
# GET /audiobooks/{id} — detail
# ---------------------------------------------------------------------------


class TestGetAudiobook:
    @pytest.mark.anyio
    async def test_returns_audiobook_with_chapters(
        self, app: FastAPI, db_conn, tmp_data_dir: Path
    ):
        _seed_audiobook(
            db_conn, tmp_data_dir, audiobook_id="book-001",
            chapters=[(1, "Intro", 60.0), (2, "Body", 120.0), (3, "End", 30.0)],
        )

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/audiobooks/book-001")

        assert response.status_code == 200
        body = response.json()
        assert body["id"] == "book-001"
        assert body["language"] == "it"
        assert len(body["chapters"]) == 3
        assert body["chapters"][0] == {
            "chapter_number": 1,
            "title": "Intro",
            "duration_seconds": 60.0,
        }
        # Chapters are ordered by chapter_number
        assert [c["chapter_number"] for c in body["chapters"]] == [1, 2, 3]

    @pytest.mark.anyio
    async def test_unknown_audiobook_returns_404(self, app: FastAPI):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/audiobooks/does-not-exist")

        assert response.status_code == 404
        assert response.json()["detail"] == "Audiobook not found"


# ---------------------------------------------------------------------------
# DELETE /audiobooks/{id}
# ---------------------------------------------------------------------------


class TestDeleteAudiobook:
    @pytest.mark.anyio
    async def test_delete_returns_204_and_removes_record(
        self, app: FastAPI, db_conn, tmp_data_dir: Path
    ):
        _seed_audiobook(db_conn, tmp_data_dir, audiobook_id="book-001")

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.delete("/api/v1/audiobooks/book-001")

        assert response.status_code == 204
        # Use a fresh connection to observe the committed state.
        check = get_connection(tmp_data_dir)
        try:
            row = check.execute(
                "SELECT id FROM audiobook WHERE id = ?", ("book-001",)
            ).fetchone()
        finally:
            check.close()
        assert row is None

    @pytest.mark.anyio
    async def test_delete_cascades_chapters_and_positions(
        self, app: FastAPI, db_conn, tmp_data_dir: Path
    ):
        _seed_audiobook(db_conn, tmp_data_dir, audiobook_id="book-001")
        db_conn.execute(
            "INSERT INTO playback_position (audiobook_id, last_chapter_number) "
            "VALUES (?, ?)",
            ("book-001", 2),
        )
        db_conn.execute(
            "INSERT INTO chapter_playback_position "
            "(audiobook_id, chapter_number, position_seconds) VALUES (?, ?, ?)",
            ("book-001", 2, 42.0),
        )
        db_conn.commit()

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.delete("/api/v1/audiobooks/book-001")

        assert response.status_code == 204

        check = get_connection(tmp_data_dir)
        try:
            chapters = check.execute(
                "SELECT COUNT(*) FROM chapter WHERE audiobook_id = ?", ("book-001",)
            ).fetchone()[0]
            positions = check.execute(
                "SELECT COUNT(*) FROM playback_position WHERE audiobook_id = ?",
                ("book-001",),
            ).fetchone()[0]
            ch_positions = check.execute(
                "SELECT COUNT(*) FROM chapter_playback_position WHERE audiobook_id = ?",
                ("book-001",),
            ).fetchone()[0]
        finally:
            check.close()

        assert chapters == 0
        assert positions == 0
        assert ch_positions == 0

    @pytest.mark.anyio
    async def test_delete_removes_audio_files_from_disk(
        self, app: FastAPI, db_conn, tmp_data_dir: Path
    ):
        _seed_audiobook(db_conn, tmp_data_dir, audiobook_id="book-001")
        audio_dir = tmp_data_dir / "audiobooks" / "book-001"
        assert audio_dir.exists()

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.delete("/api/v1/audiobooks/book-001")

        assert response.status_code == 204
        assert not audio_dir.exists()

    @pytest.mark.anyio
    async def test_delete_nulls_linked_job(
        self, app: FastAPI, db_conn, tmp_data_dir: Path
    ):
        _seed_audiobook(db_conn, tmp_data_dir, audiobook_id="book-001")
        db_conn.execute(
            "INSERT INTO job (id, audiobook_id, type, status, progress) "
            "VALUES (?, ?, 'synthesis', 'completed', 100)",
            ("job-001", "book-001"),
        )
        db_conn.commit()

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.delete("/api/v1/audiobooks/book-001")

        assert response.status_code == 204

        check = get_connection(tmp_data_dir)
        try:
            row = check.execute(
                "SELECT audiobook_id FROM job WHERE id = ?", ("job-001",)
            ).fetchone()
        finally:
            check.close()
        # Job is preserved, link is nulled (ON DELETE SET NULL).
        assert row is not None
        assert row[0] is None

    @pytest.mark.anyio
    async def test_delete_unknown_audiobook_returns_404(self, app: FastAPI):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.delete("/api/v1/audiobooks/does-not-exist")

        assert response.status_code == 404
        assert response.json()["detail"] == "Audiobook not found"

    @pytest.mark.anyio
    async def test_delete_succeeds_when_audio_dir_missing(
        self, app: FastAPI, db_conn, tmp_data_dir: Path
    ):
        """Deletion should not fail if the audio directory is already gone."""
        _seed_audiobook(
            db_conn, tmp_data_dir, audiobook_id="book-001", with_audio_files=False
        )

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.delete("/api/v1/audiobooks/book-001")

        assert response.status_code == 204
