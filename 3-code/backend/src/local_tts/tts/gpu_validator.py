"""GPU and VRAM validation for TTS inference.

Provides NVIDIA GPU + CUDA detection and VRAM availability checking.
Used at application startup and before model loading.
"""

from __future__ import annotations

from dataclasses import dataclass

import torch


@dataclass(frozen=True)
class GPUInfo:
    """Information about a detected NVIDIA GPU."""

    name: str
    vram_total_mb: float
    vram_free_mb: float
    cuda_version: str


@dataclass(frozen=True)
class VRAMCheckResult:
    """Result of a VRAM availability check."""

    sufficient: bool
    required_mb: float
    available_mb: float


class GPUValidationError(Exception):
    """Raised when GPU/CUDA validation fails."""


def validate_gpu() -> GPUInfo:
    """Verify that a compatible NVIDIA GPU with CUDA support is available.

    Returns GPU information if validation succeeds.

    Raises:
        GPUValidationError: If no compatible GPU or CUDA support is detected,
            with a clear message describing the problem.
    """
    if not torch.cuda.is_available():
        raise GPUValidationError(
            "No NVIDIA GPU with CUDA support detected. "
            "This application requires an NVIDIA GPU with CUDA drivers installed. "
            "Please verify that: "
            "(1) an NVIDIA GPU is present in the system, "
            "(2) the latest NVIDIA drivers are installed, "
            "(3) CUDA is available (run 'nvidia-smi' to check)."
        )

    device_index = 0
    name = torch.cuda.get_device_name(device_index)
    vram_total = torch.cuda.get_device_properties(device_index).total_memory
    vram_free = vram_total - torch.cuda.memory_reserved(device_index)
    cuda_version = torch.version.cuda or "unknown"

    return GPUInfo(
        name=name,
        vram_total_mb=vram_total / (1024 * 1024),
        vram_free_mb=vram_free / (1024 * 1024),
        cuda_version=cuda_version,
    )


def check_vram(required_mb: float) -> VRAMCheckResult:
    """Check whether sufficient VRAM is available for a model.

    Args:
        required_mb: The amount of VRAM needed in megabytes.

    Returns:
        A VRAMCheckResult indicating whether VRAM is sufficient.

    Raises:
        GPUValidationError: If no GPU is available (delegates to validate_gpu).
    """
    gpu_info = validate_gpu()
    return VRAMCheckResult(
        sufficient=gpu_info.vram_free_mb >= required_mb,
        required_mb=required_mb,
        available_mb=gpu_info.vram_free_mb,
    )


def get_gpu_status() -> GPUInfo | None:
    """Return current GPU information, or None if no GPU is available.

    Unlike validate_gpu(), this does not raise on missing GPU — it is
    intended for monitoring/status reporting.
    """
    try:
        return validate_gpu()
    except GPUValidationError:
        return None
