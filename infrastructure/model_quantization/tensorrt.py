# infrastructure/model_quantization/tensorrt.py

import logging
from pathlib import Path

from infrastructure.exceptions.quantization.errors import TensorRTQuantizationError
from infrastructure.model_quantization.calibration import collect_calibration_images, preprocess_yolo_image
from infrastructure.model_quantization.yolo_export import export_yolo_model


logger = logging.getLogger(__name__)


class TensorRTFP16Quantizer:
    """
    Prepares an FP16 TensorRT engine artifact.
    """

    def quantize(self,
                 pt_path: Path,
                 fp16_engine_path: Path) -> Path:
        """
        Builds an FP16 TensorRT engine from the source model.

        Args:
            pt_path: Path to the source PyTorch model.
            fp16_engine_path: Target path for the final FP16 `.engine` file.

        Returns:
            Path: The resolved path to the FP16 TensorRT engine.

        Raises:
            TensorRTQuantizationError: If TensorRT is unavailable or engine building fails.
        """
        if fp16_engine_path.exists():
            return fp16_engine_path

        try:
            import tensorrt as trt
        except ImportError as error:
            raise TensorRTQuantizationError(
                "Для TensorRT нужен пакет tensorrt (только на NVIDIA GPU)"
            ) from error

        onnx_path = fp16_engine_path.with_suffix(".onnx")
        export_yolo_model(
            pt_path=pt_path,
            export_format="onnx",
            target_path=onnx_path,
        )

        TRT_LOGGER = trt.Logger(trt.Logger.WARNING)
        builder = trt.Builder(TRT_LOGGER)
        network = builder.create_network(1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH))
        parser = trt.OnnxParser(network, TRT_LOGGER)

        with open(onnx_path, "rb") as model_file:
            if not parser.parse(model_file.read()):
                raise TensorRTQuantizationError(
                    f"Не удалось распарсить ONNX модель: {onnx_path}"
                )

        config = builder.create_builder_config()
        config.set_flag(trt.BuilderFlag.FP16)
        config.max_workspace_size = 1 << 30  # 1GB

        engine = builder.build_engine(network, config)
        if engine is None:
            raise TensorRTQuantizationError("Не удалось создать TensorRT engine")

        with open(fp16_engine_path, "wb") as engine_file:
            engine_file.write(engine.serialize())

        if not fp16_engine_path.exists():
            raise TensorRTQuantizationError(
                f"TensorRT FP16 quantization не создала файл: {fp16_engine_path}"
            )

        return fp16_engine_path


class TensorRTINT8Quantizer:
    """
    Prepares an INT8 TensorRT engine artifact with custom entropy calibration.
    """

    def quantize(self,
                 pt_path: Path,
                 int8_engine_path: Path,
                 dataset_config_path: Path,
                 input_size: int) -> Path:
        """
        Builds an INT8 TensorRT engine using a calibration dataset.

        Args:
            pt_path: Path to the source PyTorch model.
            int8_engine_path: Target path for the final INT8 `.engine` file.
            dataset_config_path: Path to the dataset YAML for calibration.
            input_size: Target spatial resolution.

        Returns:
            Path: The resolved path to the INT8 TensorRT engine.

        Raises:
            TensorRTQuantizationError: If TensorRT is unavailable or engine building fails.
        """
        if int8_engine_path.exists():
            return int8_engine_path

        try:
            import tensorrt as trt
            import numpy as np
        except ImportError as error:
            raise TensorRTQuantizationError(
                "Для TensorRT INT8 нужен пакет tensorrt (только на NVIDIA GPU)"
            ) from error

        onnx_path = int8_engine_path.with_suffix(".onnx")
        export_yolo_model(
            pt_path=pt_path,
            export_format="onnx",
            target_path=onnx_path,
        )

        image_paths = collect_calibration_images(dataset_config_path)
        calibration_data = [
            preprocess_yolo_image(img_path, input_size)
            for img_path in image_paths
        ]

        class Int8Calibrator(trt.IInt8EntropyCalibrator2):
            """
             Custom INT8 Entropy Calibrator for TensorRT.
             Feeds preprocessed batches directly to the GPU via CUDA memory allocation.
             """
            def __init__(self, data, batch_size=1):
                trt.IInt8EntropyCalibrator2.__init__(self)
                self.data = data
                self.batch_size = batch_size
                self.current_index = 0

                self.device_input = trt.cuda.DeviceAllocation(
                    np.zeros((batch_size, 3, input_size, input_size), dtype=np.float32).nbytes
                )

            def get_batch_size(self):
                return self.batch_size

            def get_batch(self, names):
                if self.current_index + self.batch_size > len(self.data):
                    return None

                batch = np.array(self.data[self.current_index:self.current_index + self.batch_size])
                self.current_index += self.batch_size

                trt.cuda.memcpy_host_to_device(
                    self.device_input,
                    np.ascontiguousarray(batch),
                    batch.nbytes
                )
                return [int(self.device_input)]

            def read_calibration_cache(self):
                return None

            def write_calibration_cache(self, cache):
                pass

        calibrator = Int8Calibrator(calibration_data)

        TRT_LOGGER = trt.Logger(trt.Logger.WARNING)
        builder = trt.Builder(TRT_LOGGER)
        network = builder.create_network(1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH))
        parser = trt.OnnxParser(network, TRT_LOGGER)

        with open(onnx_path, "rb") as model_file:
            if not parser.parse(model_file.read()):
                raise TensorRTQuantizationError(
                    f"Не удалось распарсить ONNX модель: {onnx_path}"
                )

        config = builder.create_builder_config()
        config.set_flag(trt.BuilderFlag.INT8)
        config.int8_calibrator = calibrator
        config.max_workspace_size = 1 << 30  # 1GB

        engine = builder.build_engine(network, config)
        if engine is None:
            raise TensorRTQuantizationError("Не удалось создать TensorRT INT8 engine")

        with open(int8_engine_path, "wb") as engine_file:
            engine_file.write(engine.serialize())

        if not int8_engine_path.exists():
            raise TensorRTQuantizationError(
                f"TensorRT INT8 quantization не создала файл: {int8_engine_path}"
            )

        return int8_engine_path