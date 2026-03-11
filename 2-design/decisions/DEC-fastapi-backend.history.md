# DEC-fastapi-backend: Trail

> Companion to `DEC-fastapi-backend.md`.
> AI agents read this only when evaluating whether the decision is still
> valid or when proposing a change or supersession.

## Alternatives considered

### Option A: Python + FastAPI
- Pros: Native fit for ML/TTS ecosystem (PyTorch, HuggingFace). Async support. Modern, well-documented, strong typing. Built-in OpenAPI docs. Low boilerplate.
- Cons: Slightly newer than Flask (smaller legacy ecosystem).

### Option B: Python + Flask
- Pros: Mature, widely used, extensive community resources.
- Cons: No built-in async support (needs extensions). No built-in type validation. More boilerplate for typed APIs.

### Option C: Node.js + Express
- Pros: Large ecosystem, fast I/O.
- Cons: Python is required anyway for PyTorch/HuggingFace — adding Node.js doubles the runtime stack. Violates CON-solo-developer (minimize moving parts).

## Reasoning

Python is non-negotiable given the TTS/ML dependency chain (PyTorch, HuggingFace Transformers). Between Python frameworks, FastAPI offers async support, built-in request validation, and automatic OpenAPI documentation with less boilerplate than Flask. Its type-annotated style reduces bugs in a solo-developer context. The decision would be invalidated if the project moved away from Python-based TTS inference.

## Human involvement

**Type**: ai-proposed/human-approved

**Notes**: Proposed as part of the architecture draft; user approved the full tech stack.

## Changelog

| Date | Change | Involvement |
|------|--------|-------------|
| 2026-03-11 | Initial decision | ai-proposed/human-approved |
