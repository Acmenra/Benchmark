import shutil
import logging
import subprocess
from pathlib import Path

from infrastructure.exceptions.quantization.errors import NCNNQuantizationError
from infrastructure.model_quantization.yolo_export import export_yolo_model
from infrastructure.model_quantization.calibration import collect_calibration_images


logger = logging.getLogger(__name__)


class NCNNFP32Exporter:
    """Экспорт модели в формат NCNN (FP32) через промежуточный ONNX."""

    def export(
            self,
            pt_path: Path,
            ncnn_param_path: Path,
            ncnn_bin_path: Path,
    ) -> tuple[Path, Path]:
        if ncnn_param_path.exists() and ncnn_bin_path.exists():
            return ncnn_param_path, ncnn_bin_path

        # 1. Сначала экспортируем в ONNX (используем существующую логику)
        onnx_path = ncnn_param_path.with_suffix(".onnx")
        export_yolo_model(
            pt_path=pt_path,
            export_format="onnx",
            target_path=onnx_path,
        )

        # 2. Проверяем наличие утилиты конвертации
        if not shutil.which("onnx2ncnn"):
            raise NCNNQuantizationError(
                "Утилита 'onnx2ncnn' не найдена в PATH. Установите ncnn-tools."
            )

        # 3. Конвертируем ONNX в NCNN
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
    """Подготовка INT8 NCNN-артефакта через ncnn2table и ncnn2int8."""

    def quantize(
            self,
            pt_path: Path,
            ncnn_int8_param_path: Path,
            ncnn_int8_bin_path: Path,
            dataset_config_path: Path,
            input_size: int,
    ) -> tuple[Path, Path]:
        if ncnn_int8_param_path.exists() and ncnn_int8_bin_path.exists():
            return ncnn_int8_param_path, ncnn_int8_bin_path

        # 1. Получаем имена для FP32 версии (убираем суффикс _int8)
        fp32_param_path = ncnn_int8_param_path.with_name(
            ncnn_int8_param_path.stem.replace("_int8", "") + ".param"
        )
        fp32_bin_path = ncnn_int8_bin_path.with_name(
            ncnn_int8_bin_path.stem.replace("_int8", "") + ".bin"
        )

        # Экспортируем FP32 NCNN
        NCNNFP32Exporter().export(pt_path, fp32_param_path, fp32_bin_path)

        # 2. Проверяем наличие утилит квантования
        if not shutil.which("ncnn2table"):
            raise NCNNQuantizationError("Утилита 'ncnn2table' не найдена в PATH.")
        if not shutil.which("ncnn2int8"):
            raise NCNNQuantizationError("Утилита 'ncnn2int8' не найдена в PATH.")

        # 3. Собираем изображения для калибровки
        image_paths = collect_calibration_images(dataset_config_path)
        if not image_paths:
            raise NCNNQuantizationError("Не найдены изображения для калибровки NCNN.")

        # ncnn2table требует папку с картинками, создаем временную директорию
        calib_dir = ncnn_int8_param_path.parent / "ncnn_calib_images"
        calib_dir.mkdir(exist_ok=True)

        # Создаем симлинки для скорости (не копируем файлы)
        for i, img_path in enumerate(image_paths):
            link_path = calib_dir / f"calib_{i:04d}{img_path.suffix}"
            if not link_path.exists():
                link_path.symlink_to(img_path.resolve())

        table_path = ncnn_int8_param_path.with_suffix(".table")

        # 4. Генерируем таблицу калибровки
        # mean=[0,0,0], norm=[0.0039215686, 0.0039215686, 0.0039215686] — стандарт для YOLO (1/255.0)
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

        # 5. Квантуем в INT8
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

