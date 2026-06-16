"""Text-preprocessing service: a modular, configurable normalization pipeline.

Transforms raw input text (uploaded files or pasted text) into TTS-ready text
before synthesis (``GOAL-text-normalization``,
``DEC-text-preprocessing-pipeline``).  The capability is decomposed into
discrete, independently unit-testable stages run by a thin pipeline runner,
and configured along two axes — output language and TTS model
(``REQ-MNT-preprocessing-pipeline``).

Public surface:

- :class:`PreprocessingService` / :class:`PreprocessResult` — the orchestrator.
- :class:`Stage` / :class:`StageConfig` — the stage abstraction.
- :class:`Pipeline` / :func:`build_pipeline` — the runner.
- :class:`LanguageProfile` / :class:`ModelProfile` and their resolvers —
  two-axis configuration.

Concrete stages (Unicode sanitization, layout repair, numeric/symbolic
verbalization, abbreviation expansion) live in their own modules and are
registered below; each stage-implementation task adds its import and
``register_stage`` call here, mirroring the model-adapter registry.
"""

from __future__ import annotations

from local_tts.preprocessing.pipeline import Pipeline, build_pipeline
from local_tts.preprocessing.profiles import (
    DEFAULT_LANGUAGE,
    DEFAULT_STAGE_ORDER,
    LanguageProfile,
    ModelProfile,
    default_model_profile,
    load_domain_dictionary,
    register_language_data,
    register_model_profile,
    resolve_language_profile,
    resolve_model_profile,
)
from local_tts.preprocessing.service import PreprocessingService, PreprocessResult
from local_tts.preprocessing.stages import (
    STAGE_ABBREVIATION_EXPANSION,
    STAGE_LAYOUT_REPAIR,
    STAGE_NUMERIC_SYMBOLIC_VERBALIZATION,
    STAGE_UNICODE_SANITIZATION,
    Stage,
    StageConfig,
    get_stage,
    has_stage,
    register_stage,
)

# ---------------------------------------------------------------------------
# Built-in stage registration
# ---------------------------------------------------------------------------
# Each stage-implementation task imports its stage class and registers it
# here, e.g.:
#     from local_tts.preprocessing.unicode_sanitization import UnicodeSanitizationStage
#     register_stage(UnicodeSanitizationStage)
# Until a stage is registered it is simply absent from the default pipeline,
# so the system stays functional as stages are added incrementally.

__all__ = [
    "PreprocessingService",
    "PreprocessResult",
    "Stage",
    "StageConfig",
    "Pipeline",
    "build_pipeline",
    "LanguageProfile",
    "ModelProfile",
    "DEFAULT_LANGUAGE",
    "DEFAULT_STAGE_ORDER",
    "STAGE_UNICODE_SANITIZATION",
    "STAGE_LAYOUT_REPAIR",
    "STAGE_NUMERIC_SYMBOLIC_VERBALIZATION",
    "STAGE_ABBREVIATION_EXPANSION",
    "register_stage",
    "get_stage",
    "has_stage",
    "register_language_data",
    "register_model_profile",
    "resolve_language_profile",
    "resolve_model_profile",
    "default_model_profile",
    "load_domain_dictionary",
]
