# infrastructure/model_quantization/onnx.py

import logging
from pathlib import Path

from infrastructure.exceptions import ONNXQuantizationError
from infrastructure.model_quantization.calibration import (
    collect_calibration_images,
    preprocess_yolo_image,
)
from infrastructure.model_quantization.yolo_export import export_yolo_model


logger = logging.getLogger(__name__)


class YoloONNXCalibrationDataReader:
    """
    CalibrationDataReader implementation for onnxruntime static quantization.

    Feeds preprocessed YOLO images to the ONNX Runtime quantizer one by one.
    """
    def __init__(self,
                 input_name: str,
                 image_paths: list[Path],
                 input_size: int) -> None:
        """
        Args:
            input_name: The name of the input tensor in the ONNX model.
            image_paths: List of paths to calibration images.
            input_size: Target spatial resolution for preprocessing.
        """
        self.input_name = input_name
        self.image_paths = image_paths
        self.input_size = input_size
        self._index = 0

    def get_next(self) -> dict[str, object] | None:
        """
        Returns the next preprocessed image batch, or None if exhausted.

        Returns:
            dict[str, object] | None: A dictionary mapping the input name to the
                                      preprocessed NCHW tensor.
        """
        if self._index >= len(self.image_paths):
            return None

        image_path = self.image_paths[self._index]
        self._index += 1
        return {
            self.input_name: preprocess_yolo_image(image_path, self.input_size),
        }


class ONNXINT8Quantizer:
    """
    Prepares an INT8 ONNX artifact via onnxruntime.quantization.
    """

    def quantize(self,
                 pt_path: Path,
                 fp32_onnx_path: Path,
                 int8_onnx_path: Path,
                 dataset_config_path: Path,
                 input_size: int) -> Path:
        """
        Executes static INT8 quantization on the exported ONNX model.

        Args:
            pt_path: Path to the source PyTorch model.
            fp32_onnx_path: Target path for the intermediate FP32 ONNX model.
            int8_onnx_path: Target path for the final INT8 ONNX model.
            dataset_config_path: Path to the dataset YAML for calibration.
            input_size: Target spatial resolution.

        Returns:
            Path: The resolved path to the INT8 ONNX artifact.

        Raises:
            ONNXQuantizationError: If dependencies are missing or quantization fails.
        """
        if int8_onnx_path.exists():
            return int8_onnx_path

        try:
            import onnxruntime as ort
            from onnxruntime.quantization import (
                CalibrationMethod,
                QuantFormat,
                QuantType,
                quantize_static,
            )
        except ImportError as error:
            raise ONNXQuantizationError(
                "Для ONNX INT8 нужны пакеты onnxruntime и onnx"
            ) from error

        fp32_onnx_path = export_yolo_model(
            pt_path=pt_path,
            export_format="onnx",
            target_path=fp32_onnx_path,
        )

        image_paths = collect_calibration_images(dataset_config_path)
        session = ort.InferenceSession(
            str(fp32_onnx_path),
            providers=["CPUExecutionProvider"],
        )
        input_name = session.get_inputs()[0].name

        reader = YoloONNXCalibrationDataReader(
            input_name=input_name,
            image_paths=image_paths,
            input_size=input_size,
        )

        quantize_static(
            model_input=str(fp32_onnx_path),
            model_output=str(int8_onnx_path),
            calibration_data_reader=reader,
            quant_format=QuantFormat.QDQ,
            activation_type=QuantType.QInt8,
            weight_type=QuantType.QInt8,
            calibrate_method=CalibrationMethod.MinMax,
            per_channel=True,
        )

        if not int8_onnx_path.exists():
            raise ONNXQuantizationError(
                f"ONNX INT8 quantization не создала файл: {int8_onnx_path}"
            )

        return int8_onnx_path

