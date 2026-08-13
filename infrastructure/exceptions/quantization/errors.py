# infrastructure/exceptions/quantization/errors.py

import logging
from infrastructure.exceptions.base import ModelError


logger = logging.getLogger(__name__)


class CalibrationDataError(ModelError):
    """
    Exception raised when calibration data preparation fails.

    Raised when:
        - The `data.yaml` configuration file for INT8 calibration is missing.
        - The calibration dataset path is invalid or contains no valid images.
    """
    pass


class ModelExportError(ModelError):
    """
    Exception raised when exporting a model to a runtime format fails.

    Raised when:
        - The underlying export engine (e.g., Ultralytics export, ONNX exporter)
          throws an error or produces an invalid file.
        - The target format is incompatible with the model architecture.
    """
    pass


class ONNXQuantizationError(ModelError):
    """
    Exception raised during ONNX model quantization or export.

    Raised when:
        - ONNX Runtime quantization fails (e.g., unsupported opset, missing operators).
        - The exported ONNX graph is invalid or corrupted.
    """
    pass


class OpenVINOQuantizationError(ModelError):
    """
    Exception raised during OpenVINO model conversion or quantization.

    Raised when:
        - The OpenVINO Model Optimizer fails to convert the source model.
        - Post-Training Quantization (PTQ) fails due to calibration data issues.
    """
    pass


class PyTorchQuantizationError(ModelError):
    """
    Exception raised during PyTorch model quantization.

    Raised when:
        - Dynamic or static quantization via `torch.quantization` fails.
        - The model architecture contains layers unsupported by the PyTorch quantization engine.
    """
    pass


class TensorRTQuantizationError(ModelError):
    """
    Exception raised during TensorRT engine building or quantization.

    Raised when:
        - The TensorRT builder fails to parse the ONNX model.
        - INT8/FP16 calibration fails due to missing CUDA support or invalid calibration cache.
    """
    pass


class NCNNQuantizationError(ModelError):
    """
    Exception raised during NCNN model export or INT8 quantization.

    Raised when:
        - The `onnx2ncnn` conversion tool fails or is not installed.
        - NCNN INT8 calibration fails due to invalid histogram generation.
    """
    pass