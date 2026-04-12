# DEC-default-italian-language: Trail

> Companion to `DEC-default-italian-language.md`.
> AI agents read this only when evaluating whether the decision is still
> valid or when proposing a change or supersession.

## Alternatives considered

### Option A: Default to English (status quo)

- Pros: Matches upstream library defaults (Kokoro ships with American English as default).
- Cons: Italian text synthesized with English phonemes produces unintelligible output for the target audience. Every user must manually select Italian language on every synthesis request.

### Option B: Default to Italian

- Pros: Matches the primary audience and the API design specification (`"default_language": "it"`). Italian text works correctly out of the box.
- Cons: Users synthesizing English text must explicitly select English. This is acceptable since the application targets Italian-speaking users.

### Option C: No default — require explicit language on every request

- Pros: No assumptions about language.
- Cons: Poor usability; every request must include a language parameter. Contradicts the API design which specifies a default.

## Reasoning

The application's primary audience is Italian-speaking. The API design already specifies `"default_language": "it"`. Defaulting to English forces every user to manually override the language, and produces broken output if they forget. Option B aligns implementation with design intent and user expectations.

This decision would be invalidated if the target audience changes to a non-Italian market, in which case the default should be updated accordingly.

## Human involvement

**Type**: ai-proposed/human-approved

**Notes**: User reported Italian text being synthesized with English phonemes and explicitly requested that the default be changed to Italian and that this convention apply to all adapters.

## Changelog

| Date | Change | Involvement |
|------|--------|-------------|
| 2026-04-12 | Initial decision | ai-proposed/human-approved |
