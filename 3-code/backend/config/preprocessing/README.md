# Preprocessing configuration

This directory holds optional configuration for the text-preprocessing pipeline
(`DEC-text-preprocessing-pipeline`).

## Domain dictionary (optional)

The abbreviation-expansion stage (`REQ-F-abbreviation-expansion`) can apply an
optional **domain dictionary** that maps acronyms and technical terms to their
intended spoken form. This complements the language-specific built-in
abbreviation set.

- **File**: `domain_dictionary.json` in this directory.
  (Override the location with the `LOCAL_TTS_PREPROCESSING_CONFIG_DIR`
  environment variable.)
- **Format**: a flat JSON object mapping each term to its spoken form. See
  [`domain_dictionary.example.json`](domain_dictionary.example.json) for a
  sample — copy it to `domain_dictionary.json` to activate it.
- **Matching**: each key is matched as a whole token. Matching is
  **case-sensitive** by default, so an acronym such as `AI` does not collide
  with an ordinary lowercase word.
- **Optional**: when `domain_dictionary.json` is absent (or malformed), the
  pipeline proceeds with the built-in abbreviation set only — its absence never
  breaks preprocessing.

```json
{
  "AI": "intelligenza artificiale",
  "USB": "u esse bi"
}
```
