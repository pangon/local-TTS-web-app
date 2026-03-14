"""TTS subpackage — all TTS inference and GPU interaction.

The ``TTSEngine`` class is the public interface for this subpackage.
Backend application services should import and use it directly::

    from local_tts.tts import TTSEngine

    engine = TTSEngine()
    gpu_info = engine.validate_gpu()
"""

from local_tts.tts.engine import TTSEngine

__all__ = ["TTSEngine"]
