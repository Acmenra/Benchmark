from typing import Any

from application.benchmark.loader.onnx_loader import ONNXModelLoader
from application.benchmark.loader.pytorch_loader import PyTorchModelLoader
from core.enums.model import ModelFormat


class LoaderFactory:
    """Создает загрузчики моделей."""

    @staticmethod
    def create(model_format: ModelFormat, model_path: Any):
        # match model_format:
        #     case ModelFormat.PYTORCH:
        #         return PyTorchModelLoader(model_path)

        #     case ModelFormat.ONNX:
        #         return ONNXModelLoader(model_path)
        ...
