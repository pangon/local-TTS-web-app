# DEC-sse-progress: Trail

> Companion to `DEC-sse-progress.md`.
> AI agents read this only when evaluating whether the decision is still
> valid or when proposing a change or supersession.

## Alternatives considered

### Option A: Server-Sent Events (SSE)
- Pros: Simple, built on HTTP. Native browser support via EventSource API with automatic reconnection. One-way server→client is exactly the pattern needed. Easy to implement in FastAPI (StreamingResponse). No additional dependencies.
- Cons: One-directional only (not a limitation here). Not supported in some older browsers (not a concern given target browsers).

### Option B: WebSocket
- Pros: Bidirectional communication. Well-supported.
- Cons: More complex to implement and manage (connection lifecycle, ping/pong, reconnection logic). Bidirectionality is unnecessary — client→server communication already uses REST. Adds complexity without benefit.

### Option C: Client-side polling
- Pros: Simplest to implement. Works everywhere.
- Cons: Delayed updates (latency proportional to polling interval). Wastes bandwidth with repeated requests. Poor user experience for progress tracking. Higher server load per active client.

## Reasoning

SSE is the simplest technology that satisfies the requirement. All real-time updates flow server→client (progress percentages, status changes, resource metrics). The client never needs to push data through this channel — REST endpoints handle all client actions. SSE's built-in reconnection and HTTP compatibility make it easier to implement than WebSocket with no functional trade-off. The decision would be invalidated if bidirectional real-time communication became necessary (e.g., collaborative editing).

## Human involvement

**Type**: ai-proposed/human-approved

**Notes**: Proposed as part of the architecture draft; user approved the full architecture.

## Changelog

| Date | Change | Involvement |
|------|--------|-------------|
| 2026-03-11 | Initial decision | ai-proposed/human-approved |
