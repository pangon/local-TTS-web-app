# DEC-default-italian-language: Italian as Default Language for All Adapters

**Status**: Active

**Category**: Convention

**Scope**: backend

**Source**: [REQ-F-default-voice-quality](../../1-objectives/requirements/REQ-F-default-voice-quality.md)

**Last updated**: 2026-04-12

## Context

The application targets Italian-speaking users as its primary audience. The API design specifies `"default_language": "it"` for model voice metadata. Without an explicit convention, adapters default to English, causing Italian text to be synthesized with English phonemes — producing unintelligible output for the primary use case.

## Decision

Every model adapter **must** default to Italian when no explicit language is provided by the caller:

- The adapter's built-in default language code must map to Italian (e.g., Kokoro uses `"i"`, other adapters may use `"it"` or an equivalent code for their library).
- The adapter's built-in default voice must be an Italian voice compatible with the default language.
- Adapters that do not support Italian must document this limitation clearly and raise a descriptive error at load time.

## Enforcement

### Trigger conditions

- **Code phase**: when implementing a new model adapter (`TASK-loader-*`) or modifying an existing adapter's default configuration.

### Required patterns

- Default language constant or configuration is set to the adapter's Italian language code.
- Default voice is an Italian voice (e.g., Kokoro: `"if_sara"` or `"im_nicola"`).
- Adapter docstring or module-level comment references this decision (`DEC-default-italian-language`).

### Required checks

1. Verify the adapter synthesizes Italian text with Italian phonemes when no language kwarg is provided.
2. Verify the default voice name prefix matches the Italian language code for that adapter.

### Prohibited patterns

- Defaulting to English or any non-Italian language code.
- Using a non-Italian voice as the default (e.g., `"af_heart"` for Kokoro).
