# DEC-sqlite-metadata: SQLite for Metadata Storage

**Status**: Active

**Category**: Architecture

**Scope**: backend

**Source**: [CON-single-user](../../1-objectives/constraints/CON-single-user.md), [CON-solo-developer](../../1-objectives/constraints/CON-solo-developer.md), [REQ-USA-simple-setup](../../1-objectives/requirements/REQ-USA-simple-setup.md)

**Last updated**: 2026-03-11

## Context

The application needs to persist audiobook metadata, playback positions, job history, and performance metrics. The single-user constraint means no concurrent access concerns. The simple setup requirement means no external database servers to install.

## Decision

Use **SQLite** (via Python's `sqlite3` standard library module) for all metadata storage. Audio files are stored on the file system, not in the database.

## Enforcement

### Trigger conditions

- **Design phase**: when defining data models or storage patterns
- **Code phase**: when implementing any data persistence
- **Deploy phase**: when documenting setup or data backup procedures

### Required patterns

- All structured metadata is stored in SQLite.
- Database access uses Python's built-in `sqlite3` module (no ORM required, but one may be added if it simplifies code).
- The database file lives in the application's data directory.
- Audio files (MP3) are stored on the file system, referenced by path in the database.

### Required checks

1. No external database server dependencies (PostgreSQL, MySQL, etc.).
2. Database schema changes must be handled via migration scripts or versioned initialization.

### Prohibited patterns

- No storing binary audio data in the database.
- No requiring the user to install or configure a separate database server.
