# DEC-single-process: Trail

> Companion to `DEC-single-process.md`.
> AI agents read this only when evaluating whether the decision is still
> valid or when proposing a change or supersession.

## Alternatives considered

### Option A: Single process with background threads
- Pros: Simplest deployment — one command to start. No inter-process communication needed. No external dependencies (Redis, RabbitMQ). Easy to debug. Minimal setup.
- Cons: Background thread shares the GIL (but TTS inference releases it during CUDA operations). If the process crashes, everything goes down (acceptable for single-user).

### Option B: Separate worker process (e.g., Celery + Redis)
- Pros: True process isolation for long-running jobs. Job persistence across crashes. Scalable to multiple workers.
- Cons: Requires installing and running Redis (or another broker). Two processes to manage. Significantly more complex setup. Violates REQ-USA-simple-setup. Overkill for single-user with sequential jobs.

### Option C: Microservices (API + TTS engine as separate services)
- Pros: Independent scaling, clear service boundaries.
- Cons: Massive operational overhead for a solo developer. Requires inter-service communication, health checks, container orchestration. Completely disproportionate to the problem scope.

## Reasoning

For a single-user application maintained by a solo developer, operational simplicity is paramount. A single process with background threads is sufficient because: (1) only one synthesis job runs at a time (CON-single-user), (2) PyTorch/CUDA operations release the GIL so the web server remains responsive during synthesis, (3) setup requires just one command. The decision would be invalidated if multi-user support or job persistence across crashes became requirements.

## Human involvement

**Type**: ai-proposed/human-approved

**Notes**: Proposed as part of the architecture draft; user approved the full architecture.

## Changelog

| Date | Change | Involvement |
|------|--------|-------------|
| 2026-03-11 | Initial decision | ai-proposed/human-approved |
