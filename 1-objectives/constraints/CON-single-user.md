# CON-single-user: Single-User Deployment

**Category**: Operational

**Status**: Active

**Source stakeholder**: [STK-end-user](../stakeholders.md)

## Description

The application is designed for a single user running it on their own machine. Multi-user access, authentication, and concurrent job management are not required.

## Rationale

The target use case is a personal tool for local TTS and audiobook creation. Designing for a single user avoids the complexity of authentication, authorization, resource sharing, and concurrent access control.

## Impact

- No authentication or user management system needed.
- Job queue can be simple (sequential or single-concurrent) — no fairness or priority scheduling required.
- Storage management does not need per-user quotas.
- The UI does not need session management or user switching.
