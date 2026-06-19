"""Two-axis configuration resolution for the preprocessing pipeline.

The pipeline is configurable along two axes (``REQ-MNT-preprocessing-pipeline``,
``DEC-text-preprocessing-pipeline``):

- **Language profile** — keyed by output language code (default ``it`` per
  ``DEC-default-italian-language``): the verbalization rule tables and the
  built-in abbreviation set consumed by stages.
- **Model profile** — keyed by ``model_id`` with a default fallback: which
  stages run and their parameters, accommodating different models' input
  expectations without modifying shared stage logic.

An optional on-disk domain dictionary augments abbreviation expansion; it is
applied only when present and its absence must not break preprocessing.

Adding a new language or model is done by registering a profile / contributing
language data here, never by editing shared stage logic.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from local_tts.preprocessing.stages import (
    STAGE_ABBREVIATION_EXPANSION,
    STAGE_LAYOUT_REPAIR,
    STAGE_NUMERIC_SYMBOLIC_VERBALIZATION,
    STAGE_UNICODE_SANITIZATION,
    has_stage,
)

logger = logging.getLogger(__name__)

# Default output language (DEC-default-italian-language).
DEFAULT_LANGUAGE = "it"


class UnsupportedLanguageError(ValueError):
    """Raised when a requested output language has no registered data.

    Preprocessing rewrites (number/date/currency/abbreviation verbalization)
    are language-specific. A language with no registered data would silently
    pass the text through unchanged, misrepresenting the reviewed "normalized"
    text as if normalization had succeeded (``REQ-USA-normalized-text-review``).
    The pipeline therefore rejects an unsupported language rather than
    degrading to a no-op, so the caller can surface a clear error.
    """

    def __init__(self, language: str, supported: tuple[str, ...]) -> None:
        self.language = language
        self.supported = supported
        supported_list = ", ".join(supported) if supported else "(none)"
        super().__init__(
            f"Unsupported output language '{language}'. "
            f"Supported languages: {supported_list}."
        )

# Canonical full stage order.  The default model profile runs the subset of
# these that is actually registered, in this order — so a stage joins the
# pipeline automatically once its task registers it.
DEFAULT_STAGE_ORDER: tuple[str, ...] = (
    STAGE_UNICODE_SANITIZATION,
    STAGE_LAYOUT_REPAIR,
    STAGE_NUMERIC_SYMBOLIC_VERBALIZATION,
    STAGE_ABBREVIATION_EXPANSION,
)


@dataclass(frozen=True)
class LanguageProfile:
    """Language-specific data tables consumed by stages.

    ``data`` is a namespaced mapping (e.g. ``{"numeric": {...},
    "abbreviations": {...}}``); each stage reads the namespace it owns.
    Empty data keeps the pipeline functional with no language-specific
    behavior.
    """

    language: str
    data: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ModelProfile:
    """Per-model pipeline configuration.

    Attributes:
        model_id: The model this profile targets, or ``None`` for the default
            fallback profile.
        stages: Ordered stage names to run for this model.
        stage_params: Per-stage parameter overrides, keyed by stage name.
    """

    model_id: str | None
    stages: tuple[str, ...]
    stage_params: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Language profiles
# ---------------------------------------------------------------------------

# Accumulated language data, keyed by language code.  Stage tasks contribute
# their tables via register_language_data; contributions merge so multiple
# stages can populate the same language without overwriting each other.
_LANGUAGE_DATA: dict[str, dict[str, Any]] = {}


def register_language_data(language: str, data: Mapping[str, Any]) -> None:
    """Merge *data* into the language profile for *language*.

    Later contributions update (shallow-merge) earlier ones, letting several
    stages contribute distinct namespaces to the same language.
    """
    _LANGUAGE_DATA.setdefault(language, {}).update(data)


def clear_language_data(language: str | None = None) -> None:
    """Drop registered language data (primarily for testing)."""
    if language is None:
        _LANGUAGE_DATA.clear()
    else:
        _LANGUAGE_DATA.pop(language, None)


def supported_languages() -> tuple[str, ...]:
    """Output languages with registered data, sorted for stable display."""
    return tuple(sorted(_LANGUAGE_DATA))


def resolve_language_profile(language: str | None) -> LanguageProfile:
    """Resolve the language profile for *language*.

    Falls back to :data:`DEFAULT_LANGUAGE` when *language* is ``None`` or
    empty.  A language with no registered data is rejected with
    :class:`UnsupportedLanguageError` — preprocessing rewrites are
    language-specific, so silently passing the text through for an
    unsupported language would misrepresent the reviewed "normalized" text.
    """
    code = language or DEFAULT_LANGUAGE
    if code not in _LANGUAGE_DATA:
        raise UnsupportedLanguageError(code, supported_languages())
    return LanguageProfile(language=code, data=dict(_LANGUAGE_DATA[code]))


# ---------------------------------------------------------------------------
# Model profiles
# ---------------------------------------------------------------------------

# Per-model profile overrides, keyed by model_id.  Empty by default: every
# model uses the default profile until a model-specific one is registered.
_MODEL_PROFILES: dict[str, ModelProfile] = {}


def register_model_profile(profile: ModelProfile) -> None:
    """Register a model-specific profile.

    Raises:
        ValueError: If the profile has no ``model_id``.
    """
    if profile.model_id is None:
        raise ValueError("A registered model profile must have a model_id")
    _MODEL_PROFILES[profile.model_id] = profile


def unregister_model_profile(model_id: str) -> None:
    """Remove a registered model profile (primarily for testing)."""
    _MODEL_PROFILES.pop(model_id, None)


def default_model_profile() -> ModelProfile:
    """The fallback profile: the registered subset of the canonical order."""
    return ModelProfile(
        model_id=None,
        stages=tuple(name for name in DEFAULT_STAGE_ORDER if has_stage(name)),
        stage_params={},
    )


def resolve_model_profile(model_id: str | None) -> ModelProfile:
    """Resolve the model profile for *model_id*, falling back to the default."""
    if model_id is not None and model_id in _MODEL_PROFILES:
        return _MODEL_PROFILES[model_id]
    return default_model_profile()


# ---------------------------------------------------------------------------
# Optional domain dictionary
# ---------------------------------------------------------------------------


def load_domain_dictionary(path: Path | None = None) -> dict[str, str]:
    """Load the optional domain dictionary, or return an empty mapping.

    The dictionary maps acronyms/technical terms to spoken forms and is
    applied by the abbreviation-expansion stage when supplied.  Its absence
    must not break preprocessing, so a missing file, unreadable file, or
    malformed JSON yields an empty mapping with a logged warning rather than
    an exception.

    Args:
        path: Location of the dictionary JSON.  Defaults to
            ``config.DOMAIN_DICTIONARY_PATH`` when ``None``.
    """
    if path is None:
        from local_tts import config

        path = config.DOMAIN_DICTIONARY_PATH

    if not path.is_file():
        return {}

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        logger.warning("Could not read domain dictionary at %s: %s", path, exc)
        return {}

    if not isinstance(raw, dict):
        logger.warning(
            "Domain dictionary at %s is not a JSON object; ignoring", path
        )
        return {}

    return {str(k): str(v) for k, v in raw.items()}
