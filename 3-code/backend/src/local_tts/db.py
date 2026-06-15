"""SQLite database initialization and access.

Uses Python's built-in sqlite3 module per DEC-sqlite-metadata.
Schema defined in 2-design/data-model.md.
"""

import sqlite3
from pathlib import Path

SCHEMA_VERSION = 1

SCHEMA_SQL = """\
CREATE TABLE IF NOT EXISTS audiobook (
    id              TEXT PRIMARY KEY,
    title           TEXT NOT NULL,
    source_filename TEXT NOT NULL,
    model_id        TEXT NOT NULL,
    voice           TEXT,
    language        TEXT,
    created_at      DATETIME NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS chapter (
    id              TEXT PRIMARY KEY,
    audiobook_id    TEXT NOT NULL REFERENCES audiobook(id) ON DELETE CASCADE,
    chapter_number  INTEGER NOT NULL,
    title           TEXT NOT NULL,
    audio_filename  TEXT NOT NULL,
    duration_seconds REAL,
    UNIQUE(audiobook_id, chapter_number)
);

CREATE TABLE IF NOT EXISTS playback_position (
    audiobook_id        TEXT PRIMARY KEY REFERENCES audiobook(id) ON DELETE CASCADE,
    last_chapter_number INTEGER NOT NULL,
    updated_at          DATETIME NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS chapter_playback_position (
    audiobook_id    TEXT NOT NULL REFERENCES audiobook(id) ON DELETE CASCADE,
    chapter_number  INTEGER NOT NULL,
    position_seconds REAL NOT NULL,
    updated_at      DATETIME NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    PRIMARY KEY (audiobook_id, chapter_number)
);

CREATE TABLE IF NOT EXISTS job (
    id              TEXT PRIMARY KEY,
    audiobook_id    TEXT REFERENCES audiobook(id) ON DELETE SET NULL,
    type            TEXT NOT NULL CHECK (type IN ('synthesis', 'preview')),
    status          TEXT NOT NULL DEFAULT 'queued'
                    CHECK (status IN ('queued', 'processing', 'completed', 'failed')),
    progress        INTEGER NOT NULL DEFAULT 0,
    error_message   TEXT,
    created_at      DATETIME NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    started_at      DATETIME,
    completed_at    DATETIME
);

CREATE TABLE IF NOT EXISTS performance_metric (
    job_id                TEXT PRIMARY KEY REFERENCES job(id) ON DELETE CASCADE,
    total_duration_seconds REAL NOT NULL,
    audio_duration_seconds REAL NOT NULL,
    real_time_factor      REAL NOT NULL,
    peak_gpu_memory_mb    REAL,
    model_id              TEXT NOT NULL
);
"""

_DB_FILENAME = "local_tts.db"


def get_db_path(data_dir: Path) -> Path:
    """Return the full path to the SQLite database file."""
    return data_dir / _DB_FILENAME


def init_db(data_dir: Path) -> sqlite3.Connection:
    """Initialize the database: create the data directory, database file,
    and all tables if they don't already exist.

    Returns an open connection with WAL mode and foreign keys enabled.
    """
    data_dir.mkdir(parents=True, exist_ok=True)

    db_path = get_db_path(data_dir)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    return conn


def get_connection(data_dir: Path) -> sqlite3.Connection:
    """Open a connection to an existing database.

    Enables WAL mode and foreign keys on every connection.
    """
    db_path = get_db_path(data_dir)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn
