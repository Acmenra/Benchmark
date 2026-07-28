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
    """Подготовка INT8 PyTorch-артефакта через torch.quantization."""

    def quantize(
            self,
            pt_path: Path,
            int8_pt_path: Path,
            dataset_config_path: Path,
            input_size: int,
    ) -> Path:
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
            # Загружаем модель
            model = torch.load(pt_path, map_location="cpu")
            if hasattr(model, "model"):
                # Ultralytics YOLO
                model = model.model
            model.eval()

            # Применяем dynamic quantization (проще, не требует калибровки)
            quantized_model = torch.ao.quantization.quantize_dynamic(
                model,
                {torch.nn.Linear, torch.nn.Conv2d},
                dtype=torch.qint8,
            )

            # Сохраняем квантованную модель
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