# infrastructure/exceptions/__init__.py

import logging
from infrastructure.exceptions.base import RaBenchmarkException, ConfigError, DatasetError, ModelError
from infrastructure.exceptions.quantization import (
    CalibrationDataError,
    ModelExportError,
    NCNNQuantizationError,
    ONNXQuantizationError,
    OpenVINOQuantizationError,
    PyTorchQuantizationError,
    TensorRTQuantizationError,
)


logger = logging.getLogger(__name__)


__all__ = [
    # Base
    "RaBenchmarkException",
    "ConfigError",
    "DatasetError",
    "ModelError",
    # Quantization & Export
    "CalibrationDataError",
    "ModelExportError",
    "NCNNQuantizationError",
    "ONNXQuantizationError",
    "OpenVINOQuantizationError",
    "PyTorchQuantizationError",
    "TensorRTQuantizationError",
]