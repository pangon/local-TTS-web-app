"""Tests for the GPU validator module."""

from unittest.mock import MagicMock, patch

import pytest

from local_tts.tts.gpu_validator import (
    GPUInfo,
    GPUValidationError,
    VRAMCheckResult,
    check_vram,
    get_gpu_status,
    validate_gpu,
)


class TestValidateGpu:
    """Tests for validate_gpu()."""

    def test_no_cuda_available_raises_clear_error(self):
        """AC: when no NVIDIA GPU with CUDA support is detected,
        the system displays a clear error identifying the issue."""
        with patch("local_tts.tts.gpu_validator.torch") as mock_torch:
            mock_torch.cuda.is_available.return_value = False
            with pytest.raises(GPUValidationError, match="No NVIDIA GPU with CUDA support detected"):
                validate_gpu()

    def test_error_message_includes_actionable_guidance(self):
        """The error message should tell the user what to check."""
        with patch("local_tts.tts.gpu_validator.torch") as mock_torch:
            mock_torch.cuda.is_available.return_value = False
            with pytest.raises(GPUValidationError, match="nvidia-smi"):
                validate_gpu()

    def test_compatible_gpu_returns_gpu_info(self):
        """AC: given a compatible GPU with sufficient VRAM,
        startup and model loading proceed normally."""
        with patch("local_tts.tts.gpu_validator.torch") as mock_torch:
            mock_torch.cuda.is_available.return_value = True
            mock_torch.cuda.get_device_name.return_value = "NVIDIA RTX 3080"
            props = MagicMock()
            props.total_memory = 10 * 1024 * 1024 * 1024  # 10 GB
            mock_torch.cuda.get_device_properties.return_value = props
            mock_torch.cuda.memory_reserved.return_value = 2 * 1024 * 1024 * 1024  # 2 GB reserved
            mock_torch.version.cuda = "12.1"

            info = validate_gpu()

            assert isinstance(info, GPUInfo)
            assert info.name == "NVIDIA RTX 3080"
            assert info.cuda_version == "12.1"
            assert abs(info.vram_total_mb - 10240.0) < 1.0
            assert abs(info.vram_free_mb - 8192.0) < 1.0

    def test_returns_correct_vram_values(self):
        """VRAM total and free are correctly calculated in MB."""
        with patch("local_tts.tts.gpu_validator.torch") as mock_torch:
            mock_torch.cuda.is_available.return_value = True
            mock_torch.cuda.get_device_name.return_value = "NVIDIA RTX 4090"
            props = MagicMock()
            props.total_memory = 24 * 1024 * 1024 * 1024  # 24 GB
            mock_torch.cuda.get_device_properties.return_value = props
            mock_torch.cuda.memory_reserved.return_value = 0
            mock_torch.version.cuda = "12.4"

            info = validate_gpu()

            assert abs(info.vram_total_mb - 24576.0) < 1.0
            assert abs(info.vram_free_mb - 24576.0) < 1.0

    def test_cuda_version_unknown_when_none(self):
        """When torch.version.cuda is None, cuda_version is 'unknown'."""
        with patch("local_tts.tts.gpu_validator.torch") as mock_torch:
            mock_torch.cuda.is_available.return_value = True
            mock_torch.cuda.get_device_name.return_value = "GPU"
            props = MagicMock()
            props.total_memory = 4 * 1024 * 1024 * 1024
            mock_torch.cuda.get_device_properties.return_value = props
            mock_torch.cuda.memory_reserved.return_value = 0
            mock_torch.version.cuda = None

            info = validate_gpu()
            assert info.cuda_version == "unknown"


class TestCheckVram:
    """Tests for check_vram()."""

    def test_insufficient_vram_returns_not_sufficient(self):
        """AC: when the model's VRAM requirement exceeds available VRAM,
        the result shows required and available VRAM."""
        with patch("local_tts.tts.gpu_validator.validate_gpu") as mock_validate:
            mock_validate.return_value = GPUInfo(
                name="NVIDIA RTX 3060",
                vram_total_mb=6144.0,
                vram_free_mb=3000.0,
                cuda_version="12.1",
            )

            result = check_vram(required_mb=4096.0)

            assert isinstance(result, VRAMCheckResult)
            assert result.sufficient is False
            assert result.required_mb == 4096.0
            assert result.available_mb == 3000.0

    def test_sufficient_vram_returns_sufficient(self):
        """AC: given a compatible GPU with sufficient VRAM,
        model loading proceeds normally."""
        with patch("local_tts.tts.gpu_validator.validate_gpu") as mock_validate:
            mock_validate.return_value = GPUInfo(
                name="NVIDIA RTX 3080",
                vram_total_mb=10240.0,
                vram_free_mb=8192.0,
                cuda_version="12.1",
            )

            result = check_vram(required_mb=4096.0)

            assert result.sufficient is True
            assert result.required_mb == 4096.0
            assert result.available_mb == 8192.0

    def test_exact_vram_match_is_sufficient(self):
        """When available VRAM equals required, it should be sufficient."""
        with patch("local_tts.tts.gpu_validator.validate_gpu") as mock_validate:
            mock_validate.return_value = GPUInfo(
                name="GPU",
                vram_total_mb=4096.0,
                vram_free_mb=4096.0,
                cuda_version="12.1",
            )

            result = check_vram(required_mb=4096.0)
            assert result.sufficient is True

    def test_no_gpu_raises_validation_error(self):
        """check_vram raises GPUValidationError if no GPU is available."""
        with patch("local_tts.tts.gpu_validator.validate_gpu") as mock_validate:
            mock_validate.side_effect = GPUValidationError("No GPU")
            with pytest.raises(GPUValidationError):
                check_vram(required_mb=4096.0)


class TestGetGpuStatus:
    """Tests for get_gpu_status()."""

    def test_returns_gpu_info_when_available(self):
        """Returns GPUInfo when a GPU is detected."""
        expected = GPUInfo(
            name="NVIDIA RTX 3080",
            vram_total_mb=10240.0,
            vram_free_mb=8192.0,
            cuda_version="12.1",
        )
        with patch("local_tts.tts.gpu_validator.validate_gpu", return_value=expected):
            assert get_gpu_status() == expected

    def test_returns_none_when_no_gpu(self):
        """Returns None instead of raising when no GPU is available."""
        with patch(
            "local_tts.tts.gpu_validator.validate_gpu",
            side_effect=GPUValidationError("No GPU"),
        ):
            assert get_gpu_status() is None
