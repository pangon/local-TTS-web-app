"""Pipeline stage abstraction for the text-preprocessing service.

The preprocessing capability is decomposed into discrete, independently
unit-testable stages (``DEC-text-preprocessing-pipeline``,
``REQ-MNT-preprocessing-pipeline``).  Each stage is a small object that
transforms input text given a resolved :class:`StageConfig`, and registers
itself under a stable ``name`` in the stage registry.  The pipeline runner
(:mod:`local_tts.preprocessing.pipeline`) and model profiles
(:mod:`local_tts.preprocessing.profiles`) refer to stages by that name.

This module provides only the abstraction and the registry — the concrete
cleaning stages (Unicode sanitization, layout repair, numeric/symbolic
verbalization, abbreviation expansion) are added by their respective tasks
and registered via :func:`register_stage`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol, runtime_checkable

# Canonical stage names and default execution order.  Concrete stage classes
# must declare ``name`` equal to one of these so that the default model
# profile can reference them (see ``profiles.DEFAULT_STAGE_ORDER``).  Order is
# config-driven and refined through testing (DEC-text-preprocessing-pipeline).
STAGE_UNICODE_SANITIZATION = "unicode_sanitization"
STAGE_LAYOUT_REPAIR = "layout_repair"
STAGE_NUMERIC_SYMBOLIC_VERBALIZATION = "numeric_symbolic_verbalization"
STAGE_ABBREVIATION_EXPANSION = "abbreviation_expansion"
STAGE_SENTENCE_SEGMENTATION = "sentence_segmentation"


@dataclass(frozen=True)
class StageConfig:
    """Resolved configuration handed to a stage at run time.

    A stage instance is shared across requests; per-request parameters
    (language, model, dictionaries) arrive through this immutable config so
    stages stay stateless and independently testable.

    Attributes:
        language: Output language code (e.g. ``"it"``) selecting
            language-appropriate behavior.
        model_id: Currently loaded model whose profile was applied, or
            ``None`` when no model-specific profile is in effect.
        language_data: Language-specific tables (verbalization rules,
            built-in abbreviation sets) from the resolved language profile.
        params: Stage-specific parameters from the resolved model profile.
        domain_dictionary: Optional acronym/term → spoken-form mapping; empty
            when no domain dictionary is supplied.
    """

    language: str
    model_id: str | None = None
    language_data: Mapping[str, Any] = field(default_factory=dict)
    params: Mapping[str, Any] = field(default_factory=dict)
    domain_dictionary: Mapping[str, str] = field(default_factory=dict)


@runtime_checkable
class Stage(Protocol):
    """A single, independently testable text-transformation stage.

    Each stage exposes a stable ``name`` used by the registry and model
    profiles, and a :meth:`run` method that transforms text given a resolved
    :class:`StageConfig`.  Stages must be pure with respect to their inputs:
    no language- or model-specific rules are hardcoded into shared logic;
    such variation arrives via ``config`` (DEC-text-preprocessing-pipeline).
    """

    name: str

    def run(self, text: str, config: StageConfig) -> str:
        """Transform *text* and return the result."""
        ...


# ---------------------------------------------------------------------------
# Stage registry
# ---------------------------------------------------------------------------

# Maps stage name -> concrete stage class.  Each stage-implementation task
# registers its class here (typically from ``local_tts.preprocessing``'s
# package init), so adding a stage never requires editing shared logic.
_STAGE_REGISTRY: dict[str, type[Stage]] = {}


def register_stage(stage_cls: type[Stage]) -> None:
    """Register *stage_cls* under its declared ``name``.

    Raises:
        ValueError: If the class has no non-empty ``name`` attribute.
    """
    name = getattr(stage_cls, "name", None)
    if not name or not isinstance(name, str):
        raise ValueError(
            f"Stage class {stage_cls!r} must declare a non-empty 'name' attribute"
        )
    _STAGE_REGISTRY[name] = stage_cls


def unregister_stage(name: str) -> None:
    """Remove a registered stage (primarily for testing)."""
    _STAGE_REGISTRY.pop(name, None)


def has_stage(name: str) -> bool:
    """Whether a stage is registered under *name*."""
    return name in _STAGE_REGISTRY


def get_stage(name: str) -> Stage:
    """Instantiate and return a fresh stage registered under *name*.

    Raises:
        KeyError: If no stage is registered under *name*.
    """
    return _STAGE_REGISTRY[name]()


def registered_stage_names() -> set[str]:
    """The set of currently registered stage names."""
    return set(_STAGE_REGISTRY)
