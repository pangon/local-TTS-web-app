# DEC-sqlite-metadata: Trail

> Companion to `DEC-sqlite-metadata.md`.
> AI agents read this only when evaluating whether the decision is still
> valid or when proposing a change or supersession.

## Alternatives considered

### Option A: SQLite
- Pros: Zero-config, embedded, cross-platform. Bundled with Python — no extra dependency. Perfect for single-user, single-process apps. No server to install or maintain.
- Cons: Not suitable for multi-user concurrent access (not a concern here).

### Option B: PostgreSQL / MySQL
- Pros: Powerful, supports concurrent access, rich query features.
- Cons: Requires installing and configuring a separate server. Violates REQ-USA-simple-setup (≤ 5 commands). Overkill for single-user metadata.

### Option C: File-based (JSON/YAML files)
- Pros: No database at all, maximum simplicity for very small datasets.
- Cons: No query capability, no transactional safety, becomes unwieldy with growing audiobook libraries. Playback position updates would require rewriting entire files.

## Reasoning

SQLite is the clear fit for a single-user local application. It requires zero configuration (satisfies REQ-USA-simple-setup), is bundled with Python (no extra dependency, satisfies CON-zero-budget), handles concurrent reads from the same process safely, and supports SQL queries for listing and filtering audiobooks. The decision would be invalidated if the application needed multi-user concurrent writes or if the metadata grew beyond SQLite's practical limits (unlikely for a personal audiobook library).

## Human involvement

**Type**: ai-proposed/human-approved

**Notes**: Proposed as part of the architecture draft; user approved the full tech stack.

## Changelog

| Date | Change | Involvement |
|------|--------|-------------|
| 2026-03-11 | Initial decision | ai-proposed/human-approved |
