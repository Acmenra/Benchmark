# infrastructure/model_quantization/pytorch.py

import logging
from pathlib import Path

from infrastructure.exceptions.quantization.errors import PyTorchQuantizationError
from infrastructure.model_quantization.calibration import (
    collect_calibration_images,
    preprocess_yolo_image,
)
from infrastructure.model_quantization.yolo_export import ensure_yolo_pt_model


logger = logging.getLogger(__name__)


class PyTorchINT8Quantizer:
    """
    Prepares an INT8 PyTorch artifact via torch.ao.quantization.

    Note:
        This implementation uses dynamic quantization, which applies quantization
        to weights at runtime and activations dynamically. It does not require
        a calibration dataset, making it faster to execute but potentially less
        accurate than static quantization.
    """

    def quantize(self,
                 pt_path: Path,
                 int8_pt_path: Path,
                 dataset_config_path: Path,
                 input_size: int) -> Path:
        """
        Applies dynamic INT8 quantization to the PyTorch model.

        Args:
            pt_path: Path to the source PyTorch model.
            int8_pt_path: Target path for the quantized INT8 model.
            dataset_config_path: Unused in dynamic quantization, but kept for interface consistency.
            input_size: Unused in dynamic quantization, but kept for interface consistency.

        Returns:
            Path: The resolved path to the INT8 PyTorch artifact.

        Raises:
            PyTorchQuantizationError: If dependencies are missing or quantization fails.
        """
        if int8_pt_path.exists():
            return int8_pt_path

        try:
            import torch
            import torch.ao.quantization as quantization
        except ImportError as error:
            raise PyTorchQuantizationError(
                "Для PyTorch INT8 нужен пакет torch>=1.13"
            ) from error

        pt_path = ensure_yolo_pt_model(pt_path)

        try:
            model = torch.load(pt_path, map_location="cpu")
            if hasattr(model, "model"):
                model = model.model
            model.eval()

            quantized_model = torch.ao.quantization.quantize_dynamic(
                model,
                {torch.nn.Linear, torch.nn.Conv2d},
                dtype=torch.qint8,
            )

            torch.save(quantized_model, int8_pt_path)

            if not int8_pt_path.exists():
                raise PyTorchQuantizationError(
                    f"PyTorch INT8 quantization не создала файл: {int8_pt_path}"
                )

            logger.info(f"PyTorch INT8 модель сохранена: {int8_pt_path}")
            return int8_pt_path

        except Exception as error:
            raise PyTorchQuantizationError(
                f"PyTorch INT8 quantization не удалась: {error}"
            ) from error