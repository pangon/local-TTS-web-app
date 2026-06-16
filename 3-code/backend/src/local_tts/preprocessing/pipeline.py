"""The preprocessing pipeline runner.

A :class:`Pipeline` is an ordered list of :class:`~local_tts.preprocessing.stages.Stage`
instances; running it threads text through each stage in turn, supplying each
stage its resolved :class:`~local_tts.preprocessing.stages.StageConfig`.  The
runner is deliberately thin and contains no cleaning logic of its own, keeping
the cleaning concerns isolated in the individual stages
(``REQ-MNT-preprocessing-pipeline``).
"""

from __future__ import annotations

from typing import Callable

from local_tts.preprocessing.profiles import ModelProfile
from local_tts.preprocessing.stages import Stage, StageConfig, get_stage


class Pipeline:
    """Runs an ordered sequence of stages over input text."""

    def __init__(self, stages: list[Stage]) -> None:
        self._stages = list(stages)

    @property
    def stages(self) -> list[Stage]:
        return list(self._stages)

    @property
    def stage_names(self) -> list[str]:
        return [stage.name for stage in self._stages]

    def run(
        self, text: str, config_for: Callable[[Stage], StageConfig]
    ) -> str:
        """Run every stage in order, returning the transformed text.

        Args:
            text: Input text.
            config_for: Resolves the :class:`StageConfig` for a given stage.
        """
        for stage in self._stages:
            text = stage.run(text, config_for(stage))
        return text


def build_pipeline(profile: ModelProfile) -> Pipeline:
    """Build a pipeline from a model profile's ordered stage names.

    Each name must be registered; an unregistered name signals a
    misconfigured profile and raises ``KeyError`` (via
    :func:`~local_tts.preprocessing.stages.get_stage`).  The default profile
    only ever lists registered stages, so this is strict by design.
    """
    return Pipeline([get_stage(name) for name in profile.stages])
