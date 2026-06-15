"""Timestamp helpers shared across the backend.

The API uses ISO 8601 UTC with a trailing ``Z`` for every timestamp
(api-design.md § Conventions). Service-layer code that writes timestamps
explicitly (e.g. the UPDATE branch of an upsert, where the SQLite column
default does not fire) uses :func:`utcnow_iso` so the format stays identical
to the values produced by ``strftime('%Y-%m-%dT%H:%M:%SZ', 'now')`` in the
schema defaults.
"""

from __future__ import annotations

from datetime import datetime, timezone


def utcnow_iso() -> str:
    """Return the current UTC time as ISO 8601 with a trailing ``Z``."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
