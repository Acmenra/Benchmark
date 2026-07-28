# infrastructure/exceptions/quantization/errors.py

from infrastructure.exceptions.base import ModelError


class CalibrationDataError(ModelError):
    """Ошибка подготовки calibration dataset."""
    pass


class ONNXQuantizationError(ModelError):
    """Ошибка INT8-квантования ONNX-модели."""
    pass


class OpenVINOQuantizationError(ModelError):
    """Ошибка квантования OpenVINO-модели."""
    pass


class ModelExportError(ModelError):
    """Ошибка экспорта модели в runtime-формат."""
    pass