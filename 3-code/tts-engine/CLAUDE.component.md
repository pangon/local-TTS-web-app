# TTS Engine

**Responsibility**: All TTS inference and GPU interaction — standalone Python module independent of the web framework.

**Technology**: Python, PyTorch (CUDA), HuggingFace Transformers, huggingface_hub

## Interfaces

- Python class API (`TTSEngine`) consumed by backend: GPU validation, model listing/download/loading, chapter parsing, audio synthesis with progress callbacks

## Requirements Addressed

| File | Type | Priority | Summary |
|------|------|----------|---------|
| [REQ-F-synthesize-audiobook](../../1-objectives/requirements/REQ-F-synthesize-audiobook.md) | Functional | Must-have | Convert text to MP3 audio via GPU inference |
| [REQ-F-chapter-split-output](../../1-objectives/requirements/REQ-F-chapter-split-output.md) | Functional | Must-have | Detect and split chapter structure in text |
| [REQ-F-model-download](../../1-objectives/requirements/REQ-F-model-download.md) | Functional | Must-have | Download and cache HuggingFace models |
| [REQ-F-gpu-validation](../../1-objectives/requirements/REQ-F-gpu-validation.md) | Functional | Must-have | Verify NVIDIA GPU + CUDA availability and VRAM |
| [REQ-PORT-linux-windows](../../1-objectives/requirements/REQ-PORT-linux-windows.md) | Portability | Must-have | Run on Linux and Windows |
| [REQ-COMP-foss-only](../../1-objectives/requirements/REQ-COMP-foss-only.md) | Compliance | Must-have | Use only FOSS dependencies |
| [REQ-F-voice-language-selection](../../1-objectives/requirements/REQ-F-voice-language-selection.md) | Functional | Should-have | Support voice and language selection per model |
| [REQ-F-resource-monitoring](../../1-objectives/requirements/REQ-F-resource-monitoring.md) | Functional | Should-have | Report GPU status metrics |
| [REQ-MNT-modular-ai-layer](../../1-objectives/requirements/REQ-MNT-modular-ai-layer.md) | Maintainability | Should-have | Clean interface boundary, independently usable |
| [REQ-PERF-synthesis-latency](../../1-objectives/requirements/REQ-PERF-synthesis-latency.md) | Performance | Should-have | Meet synthesis performance targets |
| [REQ-F-default-voice-quality](../../1-objectives/requirements/REQ-F-default-voice-quality.md) | Functional | Should-have | Provide good default voice quality |

## Relevant Decisions

| File | Title | Trigger |
|------|-------|---------|
| [DEC-fastapi-backend](../../2-design/decisions/DEC-fastapi-backend.md) | Python + FastAPI Backend | Establishes Python as the backend language |
| [DEC-single-process](../../2-design/decisions/DEC-single-process.md) | Monolithic Single-Process Architecture | TTS engine runs in-process with backend via direct function calls |
