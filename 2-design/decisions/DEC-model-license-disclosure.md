# DEC-model-license-disclosure: Permit Open-Weight Non-FOSS Models with Frontend License Disclosure

**Status**: Active

**Category**: Convention

**Scope**: system-wide

**Source**: [REQ-COMP-foss-only](../../1-objectives/requirements/REQ-COMP-foss-only.md), [CON-zero-budget](../../1-objectives/constraints/CON-zero-budget.md), [REQ-F-model-listing](../../1-objectives/requirements/REQ-F-model-listing.md)

**Last updated**: 2026-06-20

## Context

The supported TTS models split into two license classes. Most (Kokoro, Qwen3-TTS, VoxCPM2, MOSS-TTSD, …) are OSI open-source (Apache-2.0 / MIT). A subset are **open-weight but released under research / non-commercial licenses** — currently Fish Audio S2-Pro (`fishaudio/s2-pro`, Fish Audio Research License) and Higgs Audio v3 (`bosonai/higgs-audio-v3-tts-4b`, Boson Research & Non-Commercial License). These run fully locally and are free for personal use, but are **not** OSI open-source and require a separate paid license for commercial use.

`REQ-COMP-foss-only` is internally graded: its description says "free and open-source" and AC3 forbids a "proprietary license", yet AC2 only requires each model be "open-weight and **freely licensed for personal use**". For this personal, single-user, local-only deployment (`CON-single-user`), the AC2 personal-use reading governs model eligibility. Without an explicit policy, either these capable models would be wrongly excluded, or they would be offered with no signal that their license differs from the FOSS norm — leaving the user unaware of the usage terms.

## Decision

Permit open-weight models that are **freely licensed for personal use** even when their license is not OSI open-source (e.g. research / non-commercial), under the AC2 personal-use reading of `REQ-COMP-foss-only`. Every such model **must** be accompanied by a clear license disclosure in the UI: each model in `COMPATIBLE_MODELS` carries license metadata, `GET /models` exposes it, and the frontend model-listing view displays a visible license notice for any model whose license is not FOSS, so the user sees the usage terms before downloading or using it.

The objectives artifacts (`REQ-COMP-foss-only`, `CON-zero-budget`) are intentionally left unchanged (user choice, 2026-06-20); this decision records the personal-use interpretation and the disclosure obligation that together make non-FOSS-but-free models acceptable.

## Enforcement

### Trigger conditions

- **Design phase**: when adding a model to the architecture Compatibility Table, defining model metadata, or changing the `GET /models` / model-listing contract.
- **Code phase**: backend — when adding or editing an entry in `COMPATIBLE_MODELS` or the `GET /models` response; frontend — when implementing or modifying the model-listing view.

### Required patterns

- Each `COMPATIBLE_MODELS` entry records its license: a license name (e.g. `Apache-2.0`), a `license_is_foss` boolean, and, when not FOSS, a `license_notice` string describing the terms (free for personal use; commercial use requires a separate license).
- `GET /models` returns `license`, `license_is_foss`, and `license_notice` for every model.
- The frontend model-listing view renders a clearly visible license notice for every model with `license_is_foss = false`.

### Required checks

1. A newly added model has accurate license metadata, verified against the model's HuggingFace card / license file.
2. If the license is not OSI open-source, `license_is_foss = false` and a non-empty `license_notice` is present.
3. The model-listing view shows the notice for non-FOSS models.

### Prohibited patterns

- Offering a non-FOSS model in the UI without a visible license notice.
- Adding a model whose license is not at least free for personal use (that would violate `REQ-COMP-foss-only` AC2 / `CON-zero-budget`).
- Silently editing `REQ-COMP-foss-only` or `CON-zero-budget` to accommodate a model (objectives changes require `/SDLC-elicit`).
