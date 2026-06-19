"""The Preprocessing Service — orchestrates the text-normalization pipeline.

This is a dedicated backend application service (a sibling to the Library /
Job / Model / Monitor services), **not** part of the TTS subpackage, which
stays focused on GPU inference (``DEC-text-preprocessing-pipeline``).  Given
raw input text plus an output language and the currently loaded model, it
resolves the language and model profiles, builds the stage pipeline, runs it
synchronously, and returns the normalized text with before/after char counts
for the review step (``REQ-USA-normalized-text-review``).

The service does not persist anything and does not run TTS inference.  The
``model_id`` of the currently loaded model is supplied by the caller (the
``POST /preprocess`` API layer reads it from the Model Service and is
responsible for the "no model loaded" error); keeping it a parameter leaves
the service decoupled and unit-testable without a GPU or loaded model.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from local_tts.preprocessing.pipeline import Pipeline, build_pipeline
from local_tts.preprocessing.profiles import (
    LanguageProfile,
    ModelProfile,
    load_domain_dictionary,
    resolve_language_profile,
    resolve_model_profile,
)
from local_tts.preprocessing.stages import Stage, StageConfig


@dataclass(frozen=True)
class PreprocessResult:
    """Outcome of a preprocessing run.

    Mirrors the ``POST /preprocess`` response fields: the normalized text the
    user reviews, the language and model whose profiles were applied, and the
    before/after character counts that support a review display.
    """

    normalized_text: str
    language: str
    model_id: str | None
    original_char_count: int
    normalized_char_count: int


class PreprocessingService:
    """Runs the modular text-preprocessing pipeline.

    Args:
        domain_dictionary_path: Optional override for the domain-dictionary
            location.  When ``None`` the configured default path is used; an
            absent or malformed dictionary yields an empty mapping.
    """

    def __init__(self, domain_dictionary_path: Path | None = None) -> None:
        self._domain_dictionary: Mapping[str, str] = load_domain_dictionary(
            domain_dictionary_path
        )

    @property
    def domain_dictionary(self) -> Mapping[str, str]:
        return self._domain_dictionary

    def preprocess(
        self,
        text: str,
        *,
        language: str | None = None,
        model_id: str | None = None,
    ) -> PreprocessResult:
        """Normalize *text* and return the result.

        Args:
            text: Raw input text.
            language: Output language code; defaults to the configured default
                language when ``None`` or empty.
            model_id: Currently loaded model selecting the model profile;
                ``None`` uses the default profile.

        Raises:
            UnsupportedLanguageError: If *language* has no registered data
                (preprocessing rewrites are language-specific, so an
                unsupported language is rejected rather than no-op'd).
        """
        language_profile = resolve_language_profile(language)
        model_profile = resolve_model_profile(model_id)
        pipeline = build_pipeline(model_profile)

        config_for = self._config_factory(
            language_profile, model_profile, model_id
        )
        normalized = pipeline.run(text, config_for)

        return PreprocessResult(
            normalized_text=normalized,
            language=language_profile.language,
            model_id=model_id,
            original_char_count=len(text),
            normalized_char_count=len(normalized),
        )

    def _config_factory(
        self,
        language_profile: LanguageProfile,
        model_profile: ModelProfile,
        model_id: str | None,
    ):
        """Build the per-stage :class:`StageConfig` resolver for a run."""

        def config_for(stage: Stage) -> StageConfig:
            return StageConfig(
                language=language_profile.language,
                model_id=model_id,
                language_data=language_profile.data,
                params=model_profile.stage_params.get(stage.name, {}),
                domain_dictionary=self._domain_dictionary,
            )

        return config_for

    def stage_names_for(self, model_id: str | None = None) -> list[str]:
        """The ordered stage names that would run for *model_id*.

        Useful for diagnostics and tests; reflects the currently registered
        stages selected by the resolved model profile.
        """
        return build_pipeline(resolve_model_profile(model_id)).stage_names
