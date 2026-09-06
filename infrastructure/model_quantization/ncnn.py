import shutil
import logging
import subprocess
from pathlib import Path

from infrastructure.exceptions.quantization.errors import NCNNQuantizationError
from infrastructure.model_quantization.yolo_export import export_yolo_model
from infrastructure.model_quantization.calibration import collect_calibration_images


logger = logging.getLogger(__name__)


class NCNNFP32Exporter:
    """
    Exports a model to NCNN FP32 format via an intermediate ONNX representation.
    """

    def export(self,
               pt_path: Path,
               ncnn_param_path: Path,
               ncnn_bin_path: Path) -> tuple[Path, Path]:
        """
        Converts a PyTorch model to NCNN `.param` and `.bin` files.

        Args:
            pt_path: Path to the source PyTorch model.
            ncnn_param_path: Target path for the NCNN `.param` file.
            ncnn_bin_path: Target path for the NCNN `.bin` weights file.

        Returns:
            tuple[Path, Path]: The resolved paths to the generated `.param` and `.bin` files.

        Raises:
            NCNNQuantizationError: If the `onnx2ncnn` CLI tool is missing or fails.
        """
        if ncnn_param_path.exists() and ncnn_bin_path.exists():
            return ncnn_param_path, ncnn_bin_path

        onnx_path = ncnn_param_path.with_suffix(".onnx")
        export_yolo_model(pt_path=pt_path,
                          export_format="onnx",
                          target_path=onnx_path,
        )

        if not shutil.which("onnx2ncnn"):
            raise NCNNQuantizationError(
                "Утилита 'onnx2ncnn' не найдена в PATH. Установите ncnn-tools."
            )

        try:
            subprocess.run(
                ["onnx2ncnn", str(onnx_path), str(ncnn_param_path), str(ncnn_bin_path)],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            raise NCNNQuantizationError(f"Ошибка onnx2ncnn: {e.stderr}") from e

        return ncnn_param_path, ncnn_bin_path


class NCNNINT8Quantizer:
    """
    Prepares an INT8 NCNN artifact via `ncnn2table` and `ncnn2int8` CLI tools.
    """

    def quantize(self,
                 pt_path: Path,
                 ncnn_int8_param_path: Path,
                 ncnn_int8_bin_path: Path,
                 dataset_config_path: Path,
                 input_size: int) -> tuple[Path, Path]:
        """
        Executes INT8 quantization on the NCNN model using a calibration dataset.

        Args:
            pt_path: Path to the source PyTorch model.
            ncnn_int8_param_path: Target path for the INT8 `.param` file.
            ncnn_int8_bin_path: Target path for the INT8 `.bin` file.
            dataset_config_path: Path to the dataset YAML for calibration.
            input_size: Target spatial resolution.

        Returns:
            tuple[Path, Path]: The resolved paths to the generated INT8 `.param` and `.bin` files.

        Raises:
            NCNNQuantizationError: If CLI tools are missing or quantization fails.
        """
        if ncnn_int8_param_path.exists() and ncnn_int8_bin_path.exists():
            return ncnn_int8_param_path, ncnn_int8_bin_path

        fp32_param_path = ncnn_int8_param_path.with_name(
            ncnn_int8_param_path.stem.replace("_int8", "") + ".param"
        )
        fp32_bin_path = ncnn_int8_bin_path.with_name(
            ncnn_int8_bin_path.stem.replace("_int8", "") + ".bin"
        )

        NCNNFP32Exporter().export(pt_path, fp32_param_path, fp32_bin_path)

        if not shutil.which("ncnn2table"):
            raise NCNNQuantizationError("Утилита 'ncnn2table' не найдена в PATH.")
        if not shutil.which("ncnn2int8"):
            raise NCNNQuantizationError("Утилита 'ncnn2int8' не найдена в PATH.")

        image_paths = collect_calibration_images(dataset_config_path)
        if not image_paths:
            raise NCNNQuantizationError("Не найдены изображения для калибровки NCNN.")

        calib_dir = ncnn_int8_param_path.parent / "ncnn_calib_images"
        calib_dir.mkdir(exist_ok=True)

        for i, img_path in enumerate(image_paths):
            link_path = calib_dir / f"calib_{i:04d}{img_path.suffix}"
            if not link_path.exists():
                link_path.symlink_to(img_path.resolve())

        table_path = ncnn_int8_param_path.with_suffix(".table")
        try:
            subprocess.run(
                [
                    "ncnn2table",
                    str(fp32_param_path),
                    str(fp32_bin_path),
                    str(calib_dir),
                    str(table_path),
                    "mean=[0,0,0]",
                    "norm=[0.0039215686,0.0039215686,0.0039215686]",
                    f"size={input_size},{input_size}",
                    "pixel=BGR",
                    "thread=4",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            raise NCNNQuantizationError(f"Ошибка ncnn2table: {e.stderr}") from e

        try:
            subprocess.run(
                [
                    "ncnn2int8",
                    str(fp32_param_path),
                    str(fp32_bin_path),
                    str(table_path),
                    str(ncnn_int8_param_path),
                    str(ncnn_int8_bin_path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            raise NCNNQuantizationError(f"Ошибка ncnn2int8: {e.stderr}") from e

        return ncnn_int8_param_path, ncnn_int8_bin_path

