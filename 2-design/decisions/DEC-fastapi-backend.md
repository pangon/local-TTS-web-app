# DEC-fastapi-backend: Python + FastAPI Backend

**Status**: Active

**Category**: Architecture

**Scope**: backend

**Source**: [CON-solo-developer](../../1-objectives/constraints/CON-solo-developer.md), [CON-gpu-inference](../../1-objectives/constraints/CON-gpu-inference.md), [REQ-USA-simple-setup](../../1-objectives/requirements/REQ-USA-simple-setup.md)

**Last updated**: 2026-03-11

## Context

The backend must serve a REST API, handle file uploads, manage background TTS jobs, and interact with PyTorch/CUDA for GPU inference. The solo developer constraint requires an established, well-documented framework with low maintenance overhead. The TTS/ML ecosystem is Python-native (PyTorch, HuggingFace Transformers, huggingface_hub).

## Decision

Use **Python** as the backend language and **FastAPI** as the web framework, with **Uvicorn** as the ASGI server.

## Enforcement

### Trigger conditions

- **Design phase**: when defining API endpoints, data flow, or backend component interfaces
- **Code phase**: when implementing any backend functionality
- **Deploy phase**: when configuring the server or defining startup commands

### Required patterns

- All backend code is Python.
- Web endpoints use FastAPI route decorators.
- The ASGI server is Uvicorn.
- Dependencies are managed via a standard Python tool (pip, requirements.txt, or pyproject.toml).

### Required checks

1. New backend dependencies must be Python packages available via pip.
2. API endpoints must use FastAPI's type-annotated request/response models.

### Prohibited patterns

- No alternative web frameworks (Flask, Django, etc.) in the backend.
- No non-Python backend services (Node.js, Go, etc.).
