# infrastructure/model_quantization/openvino.py

import shutil
import logging
from pathlib import Path

from infrastructure.exceptions import OpenVINOQuantizationError
from infrastructure.model_quantization.calibration import (
    collect_calibration_images,
    preprocess_yolo_image,
)
from infrastructure.model_quantization.yolo_export import export_yolo_model


logger = logging.getLogger(__name__)


class OpenVINOFP16Quantizer:
    """
    Prepares an FP16 OpenVINO artifact via model compression.
    """

    def quantize(self,
                 pt_path: Path,
                 fp32_openvino_path: Path,
                 fp16_openvino_path: Path) -> Path:
        """
        Converts an FP32 OpenVINO model to FP16 precision.

        Args:
            pt_path: Path to the source PyTorch model.
            fp32_openvino_path: Target path for the intermediate FP32 OpenVINO model.
            fp16_openvino_path: Target path for the final FP16 OpenVINO model.

        Returns:
            Path: The resolved path to the FP16 OpenVINO artifact directory.

        Raises:
            OpenVINOQuantizationError: If dependencies are missing or conversion fails.
        """
        if fp16_openvino_path.exists():
            return fp16_openvino_path

        try:
            import openvino as ov
        except ImportError as error:
            raise OpenVINOQuantizationError(
                "Для OpenVINO FP16 нужен пакет openvino"
            ) from error

        fp32_openvino_path = export_yolo_model(
            pt_path=pt_path,
            export_format="openvino",
            target_path=fp32_openvino_path,
        )

        source_xml = _find_openvino_xml(fp32_openvino_path)
        try:
            model = ov.Core().read_model(str(source_xml))
        except Exception as error:
            raise OpenVINOQuantizationError(
                f"Не удалось прочитать OpenVINO FP32 модель: {source_xml}"
            ) from error

        fp16_openvino_path.mkdir(parents=True, exist_ok=True)
        target_xml = fp16_openvino_path / source_xml.name
        try:
            ov.save_model(model, str(target_xml), compress_to_fp16=True)
        except Exception as error:
            raise OpenVINOQuantizationError(
                f"Не удалось сохранить OpenVINO FP16 модель: {target_xml}"
            ) from error

        _copy_openvino_metadata(fp32_openvino_path, fp16_openvino_path)
        if not target_xml.exists():
            raise OpenVINOQuantizationError(
                f"OpenVINO FP16 quantization не создала файл: {target_xml}"
            )

        return fp16_openvino_path


class OpenVINOINT8Quantizer:
    """
    Prepares an INT8 OpenVINO artifact via Post-Training Quantization (PTQ) with NNCF.
    """

    def quantize(self,
                 pt_path: Path,
                 fp32_openvino_path: Path,
                 int8_openvino_path: Path,
                 dataset_config_path: Path,
                 input_size: int) -> Path:
        """
        Executes INT8 quantization on the OpenVINO model using a calibration dataset.

        Args:
            pt_path: Path to the source PyTorch model.
            fp32_openvino_path: Target path for the intermediate FP32 OpenVINO model.
            int8_openvino_path: Target path for the final INT8 OpenVINO model.
            dataset_config_path: Path to the dataset YAML for calibration.
            input_size: Target spatial resolution.

        Returns:
            Path: The resolved path to the INT8 OpenVINO artifact directory.

        Raises:
            OpenVINOQuantizationError: If dependencies are missing or NNCF quantization fails.
        """
        if int8_openvino_path.exists():
            return int8_openvino_path

        try:
            import nncf
            import openvino as ov
        except ImportError as error:
            raise OpenVINOQuantizationError(
                "Для OpenVINO INT8 нужны пакеты openvino и nncf"
            ) from error

        fp32_openvino_path = export_yolo_model(
            pt_path=pt_path,
            export_format="openvino",
            target_path=fp32_openvino_path,
        )

        source_xml = _find_openvino_xml(fp32_openvino_path)
        image_paths = collect_calibration_images(dataset_config_path)
        core = ov.Core()
        model = core.read_model(str(source_xml))
        input_name = model.inputs[0].get_any_name()

        calibration_items = [
            {input_name: preprocess_yolo_image(image_path, input_size)}
            for image_path in image_paths
        ]
        calibration_dataset = nncf.Dataset(calibration_items)
        try:
            quantized_model = nncf.quantize(
                model,
                calibration_dataset,
                subset_size=len(calibration_items),
            )
        except Exception as error:
            raise OpenVINOQuantizationError(
                "OpenVINO/NNCF не смог выполнить INT8-квантование"
            ) from error

        int8_openvino_path.mkdir(parents=True, exist_ok=True)
        target_xml = int8_openvino_path / source_xml.name
        try:
            ov.save_model(quantized_model, str(target_xml))
        except Exception as error:
            raise OpenVINOQuantizationError(
                f"Не удалось сохранить OpenVINO INT8 модель: {target_xml}"
            ) from error
        _copy_openvino_metadata(fp32_openvino_path, int8_openvino_path)

        if not target_xml.exists():
            raise OpenVINOQuantizationError(
                f"OpenVINO INT8 quantization не создала файл: {target_xml}"
            )

        return int8_openvino_path


def _find_openvino_xml(openvino_path: Path) -> Path:
    """
    Locates the XML file within an OpenVINO export directory.

    Args:
        openvino_path: Path to the OpenVINO directory or XML file.

    Returns:
        Path: The resolved path to the `.xml` model file.

    Raises:
        OpenVINOQuantizationError: If no XML file is found.
    """
    openvino_path = Path(openvino_path)
    if openvino_path.is_file() and openvino_path.suffix == ".xml":
        return openvino_path

    xml_files = sorted(openvino_path.glob("*.xml"))
    if not xml_files:
        raise OpenVINOQuantizationError(
            f"OpenVINO XML-файл не найден в {openvino_path}"
        )

    return xml_files[0]


def _copy_openvino_metadata(source_dir: Path, target_dir: Path) -> None:
    """
    Copies `metadata.yaml` if Ultralytics generated it during export.

    Args:
        source_dir: The source OpenVINO directory.
        target_dir: The target OpenVINO directory.
    """
    metadata_path = source_dir / "metadata.yaml"
    if metadata_path.is_file():
        shutil.copy2(metadata_path, target_dir / metadata_path.name)
