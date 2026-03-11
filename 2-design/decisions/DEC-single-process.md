# DEC-single-process: Monolithic Single-Process Architecture

**Status**: Active

**Category**: Architecture

**Scope**: system-wide

**Source**: [CON-solo-developer](../../1-objectives/constraints/CON-solo-developer.md), [CON-single-user](../../1-objectives/constraints/CON-single-user.md), [REQ-USA-simple-setup](../../1-objectives/requirements/REQ-USA-simple-setup.md)

**Last updated**: 2026-03-11

## Context

The application needs a web server, background job processing (TTS synthesis), model management, and system monitoring. These could be deployed as separate services or as a single process. The solo developer and single-user constraints strongly favor minimizing operational complexity.

## Decision

Deploy the entire application as a **single Python process**. Background synthesis jobs run in a **background thread** within the same process. There are no separate worker processes, message brokers, or external services (except HuggingFace Hub for model downloads).

## Enforcement

### Trigger conditions

- **Design phase**: when defining component boundaries or inter-component communication
- **Code phase**: when implementing background processing or adding new services
- **Deploy phase**: when defining startup commands or infrastructure

### Required patterns

- One Python process serves the API, runs background jobs, and manages models.
- Background work (synthesis, model downloads) uses threading or asyncio within the process.
- Job queue is in-memory (no external broker).
- All components communicate via direct function calls or shared in-process state.

### Required checks

1. Startup requires only one command (starting the FastAPI/Uvicorn server).
2. No external services are needed beyond the Python process itself.

### Prohibited patterns

- No separate worker processes (Celery, RQ, etc.).
- No message brokers (Redis, RabbitMQ, etc.).
- No microservice decomposition.
