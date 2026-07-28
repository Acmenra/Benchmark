# infrastructure/exceptions/quantization/errors.py

from infrastructure.exceptions.base import ModelError


class CalibrationDataError(ModelError):
    """Ошибка подготовки calibration dataset."""
    pass

class NCNNQuantizationError(ModelError):
    """Ошибка INT8-квантования ONNX-модели."""
    pass


class TensorRTQuantizationError(ModelError):
    """Ошибка INT8-квантования ONNX-модели."""
    pass

class ONNXQuantizationError(ModelError):
    """Ошибка INT8-квантования ONNX-модели."""
    pass


class OpenVINOQuantizationError(ModelError):
    """Ошибка квантования OpenVINO-модели."""
    pass


class PyTorchQuantizationError(ModelError):
    """Ошибка квантования PyTorch модели."""


class TensorRTQuantizationError(ModelError):
    """Ошибка квантования TensorRT модели."""


class ModelExportError(ModelError):
    """Ошибка экспорта модели в runtime-формат."""
    pass