# CON-solo-developer: Solo Developer

**Category**: Business

**Status**: Active

**Source stakeholder**: [STK-developer](../stakeholders.md)

## Description

A single developer builds and maintains the entire project. There is no team for code review, shared on-call, or parallel workstreams.

## Rationale

This is a personal project driven by one person. All design and technology choices must account for the limited bandwidth of a solo developer.

## Impact

- Prefer established frameworks and libraries over custom solutions.
- Minimize the number of moving parts (services, languages, build tools).
- Favor simple, well-documented tooling with low maintenance overhead.
- Scope must remain realistic for one person — avoid features that require significant ongoing maintenance.
- No formal code review process; rely on automated checks (linting, tests) for quality.
