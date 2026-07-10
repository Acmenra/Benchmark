from typing import Any

from application.benchmark.inference.onnx_backend import ONNXBackend
from application.benchmark.inference.pytorch_backend import PyTorchBackend
from core.enums.model import ModelFormat


class BackendFactory:
    """Создает backend моделей."""

    @staticmethod
    def create(model_format: ModelFormat, model: Any):
        # match model_format:
        #     case ModelFormat.PYTORCH:
        #         return PyTorchBackend(model)
        #     case ModelFormat.ONNX:
        #         return ONNXBackend(model)
            
        #     case _:
        #         raise ValueError
        ...