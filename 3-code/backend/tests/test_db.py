"""Tests for SQLite database initialization (TASK-sqlite-schema-init).

Covers:
- Schema creation with all 6 tables
- Foreign key enforcement
- CASCADE delete behavior
- Idempotent initialization (safe to call twice)
- WAL journal mode
- Data directory creation
"""

import re
import sqlite3

import pytest

from local_tts.db import get_db_path, init_db

EXPECTED_TABLES = {
    "audiobook",
    "chapter",
    "playback_position",
    "chapter_playback_position",
    "job",
    "performance_metric",
}


@pytest.fixture
def data_dir(tmp_path):
    return tmp_path / "data"


@pytest.fixture
def db(data_dir):
    conn = init_db(data_dir)
    yield conn
    conn.close()


class TestSchemaCreation:
    def test_creates_data_directory(self, data_dir):
        conn = init_db(data_dir)
        conn.close()
        assert data_dir.is_dir()

    def test_creates_database_file(self, data_dir):
        conn = init_db(data_dir)
        conn.close()
        assert get_db_path(data_dir).is_file()

    def test_creates_all_tables(self, db):
        cursor = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        tables = {row[0] for row in cursor.fetchall()}
        assert tables == EXPECTED_TABLES

    def test_idempotent_initialization(self, data_dir):
        """Calling init_db twice does not raise or duplicate tables."""
        conn1 = init_db(data_dir)
        conn1.close()
        conn2 = init_db(data_dir)
        cursor = conn2.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        tables = {row[0] for row in cursor.fetchall()}
        conn2.close()
        assert tables == EXPECTED_TABLES

    def test_creates_nested_data_directory(self, tmp_path):
        nested = tmp_path / "a" / "b" / "data"
        conn = init_db(nested)
        conn.close()
        assert nested.is_dir()


class TestPragmas:
    def test_wal_journal_mode(self, db):
        mode = db.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode == "wal"

    def test_foreign_keys_enabled(self, db):
        fk = db.execute("PRAGMA foreign_keys").fetchone()[0]
        assert fk == 1


class TestAudiobookTable:
    def test_insert_audiobook(self, db):
        db.execute(
            "INSERT INTO audiobook (id, title, source_filename, model_id) "
            "VALUES ('ab-1', 'Test Book', 'test.txt', 'model/test')"
        )
        db.commit()
        row = db.execute("SELECT id, title FROM audiobook WHERE id='ab-1'").fetchone()
        assert row == ("ab-1", "Test Book")

    def test_created_at_default(self, db):
        db.execute(
            "INSERT INTO audiobook (id, title, source_filename, model_id) "
            "VALUES ('ab-2', 'Book', 'b.txt', 'model/x')"
        )
        db.commit()
        row = db.execute("SELECT created_at FROM audiobook WHERE id='ab-2'").fetchone()
        assert row[0] is not None
        # Default timestamps are ISO 8601 UTC with a trailing Z (api-design Conventions)
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", row[0])


class TestChapterTable:
    @pytest.fixture(autouse=True)
    def _audiobook(self, db):
        db.execute(
            "INSERT INTO audiobook (id, title, source_filename, model_id) "
            "VALUES ('ab-1', 'Book', 'b.txt', 'model/x')"
        )
        db.commit()

    def test_insert_chapter(self, db):
        db.execute(
            "INSERT INTO chapter (id, audiobook_id, chapter_number, title, audio_filename) "
            "VALUES ('ch-1', 'ab-1', 1, 'Chapter 1', 'chapter-01.mp3')"
        )
        db.commit()
        row = db.execute("SELECT title FROM chapter WHERE id='ch-1'").fetchone()
        assert row[0] == "Chapter 1"

    def test_unique_chapter_number_per_audiobook(self, db):
        db.execute(
            "INSERT INTO chapter (id, audiobook_id, chapter_number, title, audio_filename) "
            "VALUES ('ch-1', 'ab-1', 1, 'Ch 1', 'chapter-01.mp3')"
        )
        db.commit()
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "INSERT INTO chapter (id, audiobook_id, chapter_number, title, audio_filename) "
                "VALUES ('ch-2', 'ab-1', 1, 'Ch 1 dup', 'chapter-01-dup.mp3')"
            )

    def test_cascade_delete_chapters(self, db):
        db.execute(
            "INSERT INTO chapter (id, audiobook_id, chapter_number, title, audio_filename) "
            "VALUES ('ch-1', 'ab-1', 1, 'Ch 1', 'chapter-01.mp3')"
        )
        db.commit()
        db.execute("DELETE FROM audiobook WHERE id='ab-1'")
        db.commit()
        row = db.execute("SELECT COUNT(*) FROM chapter WHERE audiobook_id='ab-1'").fetchone()
        assert row[0] == 0


class TestPlaybackPositionTable:
    @pytest.fixture(autouse=True)
    def _audiobook(self, db):
        db.execute(
            "INSERT INTO audiobook (id, title, source_filename, model_id) "
            "VALUES ('ab-1', 'Book', 'b.txt', 'model/x')"
        )
        db.commit()

    def test_insert_playback_position(self, db):
        db.execute(
            "INSERT INTO playback_position (audiobook_id, last_chapter_number) "
            "VALUES ('ab-1', 3)"
        )
        db.commit()
        row = db.execute(
            "SELECT last_chapter_number FROM playback_position WHERE audiobook_id='ab-1'"
        ).fetchone()
        assert row[0] == 3

    def test_cascade_delete_playback_position(self, db):
        db.execute(
            "INSERT INTO playback_position (audiobook_id, last_chapter_number) "
            "VALUES ('ab-1', 1)"
        )
        db.commit()
        db.execute("DELETE FROM audiobook WHERE id='ab-1'")
        db.commit()
        row = db.execute("SELECT COUNT(*) FROM playback_position").fetchone()
        assert row[0] == 0


class TestChapterPlaybackPositionTable:
    @pytest.fixture(autouse=True)
    def _audiobook(self, db):
        db.execute(
            "INSERT INTO audiobook (id, title, source_filename, model_id) "
            "VALUES ('ab-1', 'Book', 'b.txt', 'model/x')"
        )
        db.commit()

    def test_insert_chapter_playback_position(self, db):
        db.execute(
            "INSERT INTO chapter_playback_position (audiobook_id, chapter_number, position_seconds) "
            "VALUES ('ab-1', 2, 45.5)"
        )
        db.commit()
        row = db.execute(
            "SELECT position_seconds FROM chapter_playback_position "
            "WHERE audiobook_id='ab-1' AND chapter_number=2"
        ).fetchone()
        assert row[0] == 45.5

    def test_composite_primary_key(self, db):
        db.execute(
            "INSERT INTO chapter_playback_position (audiobook_id, chapter_number, position_seconds) "
            "VALUES ('ab-1', 1, 10.0)"
        )
        db.commit()
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "INSERT INTO chapter_playback_position (audiobook_id, chapter_number, position_seconds) "
                "VALUES ('ab-1', 1, 20.0)"
            )

    def test_cascade_delete_chapter_playback_position(self, db):
        db.execute(
            "INSERT INTO chapter_playback_position (audiobook_id, chapter_number, position_seconds) "
            "VALUES ('ab-1', 1, 10.0)"
        )
        db.commit()
        db.execute("DELETE FROM audiobook WHERE id='ab-1'")
        db.commit()
        row = db.execute("SELECT COUNT(*) FROM chapter_playback_position").fetchone()
        assert row[0] == 0


class TestJobTable:
    def test_insert_job(self, db):
        db.execute(
            "INSERT INTO job (id, type) VALUES ('job-1', 'synthesis')"
        )
        db.commit()
        row = db.execute("SELECT status, progress FROM job WHERE id='job-1'").fetchone()
        assert row == ("queued", 0)

    def test_type_check_constraint(self, db):
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("INSERT INTO job (id, type) VALUES ('job-bad', 'invalid')")

    def test_status_check_constraint(self, db):
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "INSERT INTO job (id, type, status) VALUES ('job-bad', 'synthesis', 'invalid')"
            )

    def test_audiobook_id_set_null_on_delete(self, db):
        db.execute(
            "INSERT INTO audiobook (id, title, source_filename, model_id) "
            "VALUES ('ab-1', 'Book', 'b.txt', 'model/x')"
        )
        db.execute(
            "INSERT INTO job (id, audiobook_id, type) VALUES ('job-1', 'ab-1', 'synthesis')"
        )
        db.commit()
        db.execute("DELETE FROM audiobook WHERE id='ab-1'")
        db.commit()
        row = db.execute("SELECT audiobook_id FROM job WHERE id='job-1'").fetchone()
        assert row[0] is None


class TestPerformanceMetricTable:
    @pytest.fixture(autouse=True)
    def _job(self, db):
        db.execute("INSERT INTO job (id, type) VALUES ('job-1', 'synthesis')")
        db.commit()

    def test_insert_performance_metric(self, db):
        db.execute(
            "INSERT INTO performance_metric "
            "(job_id, total_duration_seconds, audio_duration_seconds, real_time_factor, model_id) "
            "VALUES ('job-1', 300.0, 3600.0, 0.083, 'model/x')"
        )
        db.commit()
        row = db.execute(
            "SELECT real_time_factor FROM performance_metric WHERE job_id='job-1'"
        ).fetchone()
        assert row[0] == pytest.approx(0.083)

    def test_cascade_delete_performance_metric(self, db):
        db.execute(
            "INSERT INTO performance_metric "
            "(job_id, total_duration_seconds, audio_duration_seconds, real_time_factor, model_id) "
            "VALUES ('job-1', 300.0, 3600.0, 0.083, 'model/x')"
        )
        db.commit()
        db.execute("DELETE FROM job WHERE id='job-1'")
        db.commit()
        row = db.execute("SELECT COUNT(*) FROM performance_metric").fetchone()
        assert row[0] == 0
