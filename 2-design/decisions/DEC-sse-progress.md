# DEC-sse-progress: Server-Sent Events for Real-Time Updates

**Status**: Active

**Category**: Architecture

**Scope**: system-wide

**Source**: [REQ-F-synthesis-progress](../../1-objectives/requirements/REQ-F-synthesis-progress.md), [REQ-F-model-download](../../1-objectives/requirements/REQ-F-model-download.md)

**Last updated**: 2026-03-11

## Context

The UI needs real-time updates for synthesis job progress, model download progress, and potentially resource monitoring. The communication is one-directional: server pushes updates to the client. The client does not need to send data back through the same channel (REST API handles all client→server actions).

## Decision

Use **Server-Sent Events (SSE)** for all real-time server-to-client updates. The FastAPI backend exposes an SSE endpoint that the Vue frontend connects to for receiving progress and status events.

## Enforcement

### Trigger conditions

- **Design phase**: when defining real-time communication patterns between backend and frontend
- **Code phase**: when implementing progress reporting or live status updates

### Required patterns

- Real-time updates use SSE (not WebSocket or polling).
- FastAPI serves SSE via `StreamingResponse` with `text/event-stream` content type.
- The Vue frontend uses the `EventSource` API to consume SSE.
- Events are typed (e.g., `synthesis-progress`, `download-progress`, `job-status`).

### Required checks

1. SSE endpoint returns proper `text/event-stream` headers.
2. Client reconnects automatically on connection loss (built into EventSource API).

### Prohibited patterns

- No WebSocket connections for progress updates.
- No client-side polling for job status or progress (SSE replaces polling for these use cases).
