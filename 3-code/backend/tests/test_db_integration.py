"""Integration tests for database initialization via FastAPI lifespan (TASK-sqlite-schema-init).

Verifies that the database is initialized when the app starts and
cleaned up when the app shuts down.
"""

import sqlite3
from unittest.mock import MagicMock, patch

import pytest

from local_tts.app import create_app, lifespan
from local_tts.db import get_db_path
from local_tts.tts.gpu_validator import GPUInfo

FAKE_GPU_INFO = GPUInfo(
    name="Test GPU", vram_total_mb=8192.0, vram_free_mb=7000.0, cuda_version="12.1"
)


@pytest.fixture
def data_dir(tmp_path):
    return tmp_path / "data"


@pytest.fixture
def app(data_dir):
    with (
        patch("local_tts.config.DATA_DIR", data_dir),
        patch("local_tts.app.TTSEngine") as MockEngine,
    ):
        engine_instance = MagicMock()
        engine_instance.validate_gpu.return_value = FAKE_GPU_INFO
        MockEngine.return_value = engine_instance
        yield create_app()


class TestLifespanDatabaseInit:
    @pytest.mark.anyio
    async def test_database_created_on_startup(self, app, data_dir):
        """The database file exists after the lifespan startup runs."""
        async with lifespan(app):
            assert get_db_path(data_dir).is_file()

    @pytest.mark.anyio
    async def test_tables_exist_after_startup(self, app, data_dir):
        """All schema tables are present after lifespan startup."""
        async with lifespan(app):
            conn = sqlite3.connect(str(get_db_path(data_dir)))
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
            tables = {row[0] for row in cursor.fetchall()}
            conn.close()
            expected = {
                "audiobook", "chapter", "playback_position",
                "chapter_playback_position", "job", "performance_metric",
            }
            assert tables == expected

    @pytest.mark.anyio
    async def test_connection_stored_in_app_state(self, app, data_dir):
        """The DB connection is stored in app.state.db_conn during lifespan."""
        async with lifespan(app):
            assert hasattr(app.state, "db_conn")
            assert app.state.db_conn is not None

    @pytest.mark.anyio
    async def test_connection_closed_after_shutdown(self, app, data_dir):
        """The DB connection is closed when the lifespan exits."""
        async with lifespan(app):
            conn = app.state.db_conn
        # After context exit, the connection should be closed
        with pytest.raises(sqlite3.ProgrammingError):
            conn.execute("SELECT 1")
