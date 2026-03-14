# DEC-python-backend-env: Python Backend Environment Conventions

**Status**: Active

**Category**: Convention

**Scope**: backend

**Source**: [DEC-fastapi-backend](DEC-fastapi-backend.md), [CON-solo-developer](../../1-objectives/constraints/CON-solo-developer.md)

**Last updated**: 2026-03-14

## Context

The backend component needs a consistent, reproducible Python development environment. Without a recorded convention, each task would re-discover how to manage dependencies, run tests, and isolate the runtime — wasting effort and risking inconsistency.

## Decision

The backend uses the following environment conventions:

- **Virtual environment**: `.venv` directory inside `3-code/backend/`, created with `python3 -m venv .venv`.
- **Package layout**: `src` layout — source code at `src/local_tts/` with package name `local_tts`.
- **Dependency management**: `pyproject.toml` with setuptools backend. Install in editable mode during development: `pip install -e ".[dev]"`.
- **Test runner**: pytest, configured in `pyproject.toml` under `[tool.pytest.ini_options]`. Tests live in `3-code/backend/tests/`.
- **Python version**: >= 3.10.

## Enforcement

### Trigger conditions

- **Code phase**: when installing dependencies, running tests, or adding new Python modules to the backend

### Required patterns

- Activate the venv before running any pip, pytest, or python commands: `. .venv/bin/activate` (or `.venv\Scripts\activate` on Windows).
- New dependencies go in `pyproject.toml` under `[project.dependencies]` (runtime) or `[project.optional-dependencies] dev` (dev-only).
- Tests use pytest and live in `tests/` under the backend directory.
- Source modules go under `src/local_tts/`.

### Required checks

1. Verify `.venv` exists before running commands; create it if missing.
2. After adding dependencies to `pyproject.toml`, re-run `pip install -e ".[dev]"`.

### Prohibited patterns

- Installing packages globally or outside the venv.
- Placing source code outside the `src/local_tts/` tree.
- Using alternative test runners (unittest directly, nose, etc.) instead of pytest.
