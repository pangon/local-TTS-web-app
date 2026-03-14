# DEC-python-backend-env: Trail

> Companion to `DEC-python-backend-env.md`.
> AI agents read this only when evaluating whether the decision is still
> valid or when proposing a change or supersession.

## Alternatives considered

### Option A: Virtual environment with src layout (chosen)

- Pros: standard Python packaging practice, clear separation of source and tests, editable install works well with pytest
- Cons: slightly more nesting than flat layout

### Option B: Flat layout (no src/ directory)

- Pros: simpler directory structure
- Cons: can cause import confusion (local imports shadow installed package), less standard for projects with pyproject.toml

### Option C: Poetry or PDM for dependency management

- Pros: lockfile support, more features
- Cons: extra tool dependency, more complexity for a solo developer project, setuptools is sufficient

## Reasoning

The src layout is the recommended practice for Python projects using pyproject.toml and setuptools. It prevents accidental imports from the working directory and works cleanly with editable installs. pytest is the de facto standard test runner. A plain venv is sufficient — no need for Poetry/PDM given the solo developer constraint.

## Human involvement

**Type**: ai-proposed/human-approved

**Notes**: Proposed during TASK-python-project-scaffold execution; user confirmed the conventions before implementation.

## Changelog

| Date | Change | Involvement |
|------|--------|-------------|
| 2026-03-14 | Initial decision | ai-proposed/human-approved |
