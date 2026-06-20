# DEC-model-license-disclosure: Trail

> Companion to `DEC-model-license-disclosure.md`.
> AI agents read this only when evaluating whether the decision is still
> valid or when proposing a change or supersession.

## Alternatives considered

### Option A: Permit all 4 models, with a frontend license notice for the non-FOSS ones (chosen)
- Pros: keeps the user's chosen models (incl. Fish S2-Pro, Higgs v3); honest disclosure of usage terms; objectives artifacts untouched; fits a personal single-user deployment under AC2.
- Cons: relies on the personal-use reading of an internally ambiguous Must-have requirement; the tension with AC3 / the "open-source" wording remains on record, unresolved.

### Option B: Permit all 4 and amend REQ-COMP-foss-only / CON-zero-budget to explicitly allow personal-use-free models
- Pros: removes the requirement ambiguity at the source.
- Cons: changes an approved Must-have compliance requirement; broader objectives impact than the user wanted.

### Option C: Include only the OSI-FOSS models (VoxCPM2, MOSS-TTSD); drop Fish S2-Pro and Higgs v3
- Pros: strict, unambiguous FOSS compliance.
- Cons: drops two capable models the user explicitly requested.

## Reasoning

The app is personal, single-user, and local (`CON-single-user`, `CON-solo-developer`); `REQ-COMP-foss-only` AC2 only requires models be "open-weight and freely licensed for personal use", which Fish S2-Pro and Higgs v3 satisfy. The user chose to keep all four and to disclose the differing license in the UI rather than amend the objectives. A visible notice keeps the user informed of the commercial-use limits without overstating compliance.

## Human involvement

**Type**: ai-proposed/human-approved

**Notes**: Surfaced as a Must-have constraint conflict during the SDLC-design update that added the Phase 5.2 models (2026-06-20). The user selected "keep all 4, caveat only" and explicitly requested that models under such licenses carry a note on the frontend model-listing page. The user declined to modify the objectives artifacts.

## Changelog

| Date | Change | Involvement |
|------|--------|-------------|
| 2026-06-20 | Initial decision | ai-proposed/human-approved |
