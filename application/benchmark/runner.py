# application/benchmark/runner.py

import gc
import os
import cv2
import glob
import torch
import logging
import numpy as np
from pathlib import Path
from typing import Generator
from dataclasses import dataclass

from acmenra_cv import YOLOBackend
from ultralytics import YOLO

from application.benchmark.metrics.collector import MetricsCollector
from core.domain.config import BenchmarkConfig, BenchmarkRun
from core.domain.metrics import ModelBenchmarkResult, LatencyStats, CPUMetrics, GPUMetrics, QualityMetrics

from core.enums.model import (
    Coco,
    DeviceType,
    QuantizationLevel,
    TaskType,
    export_extension,
    ultralytics_export_format,
)
from infrastructure.metrics.quality import YOLOQualityMetricsCollector
from infrastructure.model_quantization.onnx import (
    ONNXINT8Quantizer,
    ONNXQuantizationError,
)
from infrastructure.model_quantization.openvino import (
    OpenVINOFP16Quantizer,
    OpenVINOINT8Quantizer,
    OpenVINOQuantizationError,
)
from infrastructure.model_quantization.yolo_export import (
    ModelExportError,
    ensure_yolo_pt_model,
    export_yolo_model,
)

logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class ResolvedModelArtifact:
    """Фактически выбранный артефакт модели."""

    path: Path
    quantization: str


class BenchmarkRunner:
    """Координирует загрузку модели, инференс и сбор метрик."""

    def __init__(self, benchmark_config: BenchmarkConfig) -> None:
        self.benchmark_config = benchmark_config

    def run_suite(self) -> Generator[ModelBenchmarkResult, None, None]:
        """Запустить все benchmark-кейсы и возвращать результаты по мере готовности.

        Returns:
            Generator[ModelBenchmarkResult, None, None]: Генератор, выдающий результаты
            по одному для каждой модели в каждом кейсе.
        """
        for case in self.benchmark_config.runs:
            yield from self._run_case(case)

    def _run_case(self, case: BenchmarkRun) -> Generator[ModelBenchmarkResult, None, None]:
        """Выполнить один benchmark-кейс и возвращать результаты моделей по мере готовности.

        Args:
            case (BenchmarkRun): Конфигурация запуска для одного кейса.

        Returns:
            Generator[ModelBenchmarkResult, None, None]: Генератор, выдающий результаты
            по одной модели за раз (включая skipped, failed и success).

        Yields:
            ModelBenchmarkResult: Результат прогона для каждой комбинации
            (модель, формат, квантование).
        """
        dataset_path = self._get_dataset_path()
        image_paths = self._collect_image_paths(dataset_path)

        for model_config in case.models:
            family = model_config.family
            size = model_config.size

            for format_ in self._get_supported_formats():
                for quantization in self._get_quantization_levels():
                    artifact = self.resolve_model_artifact(
                        family,
                        size,
                        format_,
                        quantization,
                    )
                    if artifact is None:
                        yield self._build_status_result(
                            family=family,
                            size=size,
                            format_=format_,
                            actual_quantization=None,
                            status="skipped",
                            error=(
                                "Модель не подготовлена: формат или квантование "
                                "не поддержаны текущим pipeline"
                            ),
                        )
                        continue

                    collector = MetricsCollector(case)
                    model: YOLOBackend | None = None
                    run_failed = False
                    try:
                        model = self._build_yolo_backend(
                            artifact.path,
                            artifact.quantization,
                        )
                        self._warmup(model)
                        collector.start_run()
                        self._run_model_on_images(model, image_paths, collector)
                    except Exception as error:
                        logger.exception(
                            "Ошибка benchmark-прогона %s%s/%s/%s",
                            family,
                            size,
                            format_,
                            quantization,
                        )
                        run_failed = True
                        raw_result = self._safe_get_collector_result(collector)
                        yield self._build_status_result(
                            family=family,
                            size=size,
                            format_=format_,
                            actual_quantization=artifact.quantization,
                            status="failed",
                            error=str(error),
                            performance=raw_result.performance,
                            cpu=raw_result.cpu,
                            gpu=raw_result.gpu,
                        )
                        self._finalize_run(collector, model)
                        continue

                    raw_result = self._safe_get_collector_result(collector)

                    try:
                        quality_metrics = self._collect_quality_metrics(model, family, size)
                    except Exception as error:
                        logger.warning(
                            "Не удалось собрать метрики качества для %s%s/%s/%s: %s",
                            family,
                            size,
                            format_,
                            quantization,
                            error,
                        )
                        quality_metrics = None
                    finally:
                        self._finalize_run(collector, model)

                    yield ModelBenchmarkResult(
                        model={
                            "family": family,
                            "size": size,
                            "task_type": self._get_task_type().value,
                            "format": format_,
                            "quantization": artifact.quantization,
                        },
                        status="success",
                        performance=raw_result.performance,
                        cpu=raw_result.cpu,
                        gpu=raw_result.gpu,
                        quality=quality_metrics,
                    )

    def _build_status_result(
        self,
        family: str,
        size: str,
        format_: str,
        actual_quantization: str | None,
        status: str,
        error: str | None,
        performance: LatencyStats | None = None,
        cpu: CPUMetrics | None = None,
        gpu: GPUMetrics | None = None,
    ) -> ModelBenchmarkResult:
        """Собрать результат для success/skipped/failed статусов."""
        return ModelBenchmarkResult(
            model={
                "family": family,
                "size": size,
                "task_type": self._get_task_type().value,
                "format": format_,
                "quantization": actual_quantization,
            },
            status=status,
            error=error,
            performance=performance,
            cpu=cpu,
            gpu=gpu,
            quality=None,
        )

    def _safe_get_collector_result(self, collector: MetricsCollector) -> object:
        """Безопасное получение метрик из collector, чтобы не ломать весь прогон при ошибке."""
        try:
            return collector.get()
        except Exception as error:
            logger.warning("Не удалось получить метрики benchmark-прогона: %s", error)
            return type(
                "FallbackBenchmarkResult",
                (),
                {
                    "performance": None,
                    "cpu": None,
                    "gpu": None,
                },
            )()

    def _finalize_run(
        self,
        collector: MetricsCollector,
        model: YOLOBackend | None,
    ) -> None:
        """Останавливает collector и освобождает ресурсы, не ломая весь прогон."""
        try:
            collector.stop_run()
        except Exception as error:
            logger.exception("Не удалось остановить collector benchmark-прогона: %s", error)

        if model is None:
            return

        try:
            self._cleanup_model_resources(model)
        except Exception as error:
            logger.exception("Не удалось освободить ресурсы модели: %s", error)

    def _get_dataset_path(self) -> Path:
        if self.benchmark_config.test_images is None:
            raise ValueError("benchmark.test_images is required for benchmark run")

        dataset_path = Path(self.benchmark_config.test_images)
        if not dataset_path.is_dir():
            raise ValueError(f"Dataset path not found: {dataset_path}")
        
        # Если в папке есть подпапка 'images/', используем её
        # (для структур где датасет содержит images/ и labels/)
        images_subdir = dataset_path / "images"
        if images_subdir.is_dir():
            return images_subdir
        
        return dataset_path

    def _collect_image_paths(self, dataset_path: Path) -> list[Path]:
        extensions = (".jpg", ".jpeg", ".png", ".bmp", ".tiff")
        image_paths: list[Path] = []

        for ext in extensions:
            image_paths.extend(Path(path) for path in glob.glob(os.path.join(dataset_path, f"*{ext}")))
            image_paths.extend(Path(path) for path in glob.glob(os.path.join(dataset_path, f"*{ext.upper()}")))

        if not image_paths:
            raise ValueError(f"No images found in {dataset_path}")

        return sorted(image_paths)

    def _get_supported_formats(self) -> tuple[str, ...]:
        return self.benchmark_config.formats or ("pytorch",)

    def _get_quantization_levels(self) -> tuple[str, ...]:
        return self.benchmark_config.quantization or (QuantizationLevel.FP32.value,)

    def _get_task_type(self) -> TaskType:
        """Вернуть тип задачи YOLO из конфига."""
        return self.benchmark_config.task_type or TaskType.DETECT

    def _run_model_on_images(
        self,
        model: YOLOBackend,
        image_paths: list[Path],
        collector: MetricsCollector,
    ) -> None:
        main_iterations = self.benchmark_config.main_iterations or len(image_paths)

        for iteration in range(main_iterations):
            img_path = image_paths[iteration % len(image_paths)]
            frame = cv2.imread(str(img_path))
            if frame is None:
                logger.warning("Could not read %s, skipping", img_path)
                continue

            collector.mark_start()
            try:
                model.predict(frame)
            finally:
                collector.mark_stop()

    def resolve_model_artifact(
        self,
        family: str,
        size: str,
        format_: str,
        quantization: str = QuantizationLevel.FP32.value,
    ) -> ResolvedModelArtifact | None:
        """Вернуть модель строго в запрошенном формате и квантовании."""
        requested_quantization = self._normalize_quantization(quantization)

        return self._try_resolve_model_artifact(
            family,
            size,
            format_,
            requested_quantization,
        )

    def resolve_model_path(
        self,
        family: str,
        size: str,
        format_: str,
        quantization: str = QuantizationLevel.FP32.value,
    ) -> Path | None:
        """Backward-compatible wrapper: вернуть только путь к модели."""
        artifact = self.resolve_model_artifact(family, size, format_, quantization)
        return artifact.path if artifact is not None else None

    def _try_resolve_model_artifact(
        self,
        family: str,
        size: str,
        format_: str,
        quantization: str,
    ) -> ResolvedModelArtifact | None:
        """Возвращает путь к модели нужного формата.

        Для pytorch — прямой путь к .pt. 
        Для остальных форматов:
        если артефакт уже существует на диске — вернуть его; иначе
        сконвертировать через YOLO.export() и вернуть путь к результату.
        Возвращает None, если формат неизвестен или экспорт не удался.
        """
        quantization = self._normalize_quantization(quantization)
        if not self._is_quantization_supported(format_, quantization):
            return None

        model_stem = self._build_model_stem(family, size)
        pt_path = Path(f"{model_stem}.pt")
        if format_ == "pytorch":
            try:
                pt_path = ensure_yolo_pt_model(pt_path)
            except ModelExportError as error:
                logger.warning("Не удалось подготовить исходную .pt модель: %s", error)
                return None

            return ResolvedModelArtifact(
                path=pt_path,
                quantization=quantization,
            )

        export_format = ultralytics_export_format(format_)
        extension = export_extension(format_)
        if export_format is None or extension is None:
            logger.warning("Неизвестный формат модели: %s", format_)
            return None

        cached = self._find_cached_artifact(family, size, extension, quantization)
        if cached is not None:
            logger.info(
                "Найден закэшированный артефакт %s/%s: %s",
                format_,
                quantization,
                cached,
            )
            return ResolvedModelArtifact(path=cached, quantization=quantization)

        try:
            pt_path = ensure_yolo_pt_model(pt_path)
        except ModelExportError as error:
            logger.warning("Не удалось подготовить исходную .pt модель: %s", error)
            return None

        if (
            format_ == "openvino"
            and quantization == QuantizationLevel.FP16.value
        ):
            fp16_artifact = self._prepare_openvino_fp16_artifact(
                pt_path=pt_path,
                family=family,
                size=size,
                extension=extension,
            )
            if fp16_artifact is None:
                return None

            return ResolvedModelArtifact(
                path=fp16_artifact,
                quantization=quantization,
            )

        if quantization == QuantizationLevel.INT8.value:
            int8_artifact = self._prepare_int8_artifact(
                pt_path=pt_path,
                family=family,
                size=size,
                format_=format_,
                extension=extension,
            )
            if int8_artifact is None:
                return None

            return ResolvedModelArtifact(
                path=int8_artifact,
                quantization=quantization,
            )

        export_kwargs = self._build_export_kwargs(export_format, quantization)
        if export_kwargs is None:
            return None

        logger.info("Экспорт %s -> %s/%s", model_stem, format_, quantization)
        try:
            exported_path = export_yolo_model(
                pt_path=pt_path,
                export_format=export_format,
                target_path=self._build_cached_artifact_path(
                    family,
                    size,
                    extension,
                    quantization,
                ),
                export_kwargs=export_kwargs,
            )
        except (ModelExportError, Exception):
            logger.exception(
                "Не удалось экспортировать %s в формат %s/%s",
                pt_path,
                format_,
                quantization,
            )
            return None

        logger.info("Экспорт завершён: %s", exported_path)
        return ResolvedModelArtifact(path=exported_path, quantization=quantization)

    def _prepare_openvino_fp16_artifact(
        self,
        pt_path: Path,
        family: str,
        size: str,
        extension: str,
    ) -> Path | None:
        """Подготовить OpenVINO FP16-артефакт через отдельный quantizer."""
        fp32_path = self._build_cached_artifact_path(
            family,
            size,
            extension,
            QuantizationLevel.FP32.value,
        )
        fp16_path = self._build_cached_artifact_path(
            family,
            size,
            extension,
            QuantizationLevel.FP16.value,
        )

        try:
            return OpenVINOFP16Quantizer().quantize(
                pt_path=pt_path,
                fp32_openvino_path=fp32_path,
                fp16_openvino_path=fp16_path,
            )
        except (OpenVINOQuantizationError, ModelExportError) as error:
            logger.warning(
                "Не удалось подготовить FP16 OpenVINO артефакт для %s%s: %s",
                family,
                size,
                error,
            )
            return None
        except Exception:
            logger.exception(
                "Неожиданная ошибка подготовки FP16 OpenVINO артефакта для %s%s",
                family,
                size,
            )
            return None

    def _prepare_int8_artifact(
        self,
        pt_path: Path,
        family: str,
        size: str,
        format_: str,
        extension: str,
    ) -> Path | None:
        """Подготовить INT8-артефакт через специализированный quantizer."""
        dataset_config_path = self._find_quality_dataset_config()
        if dataset_config_path is None:
            logger.warning("INT8 требует data.yaml для калибровки, датасет не найден")
            return None

        input_size = self.benchmark_config.input_size or 640
        fp32_path = self._build_cached_artifact_path(
            family,
            size,
            extension,
            QuantizationLevel.FP32.value,
        )
        int8_path = self._build_cached_artifact_path(
            family,
            size,
            extension,
            QuantizationLevel.INT8.value,
        )

        try:
            if format_ == "onnx":
                return ONNXINT8Quantizer().quantize(
                    pt_path=pt_path,
                    fp32_onnx_path=fp32_path,
                    int8_onnx_path=int8_path,
                    dataset_config_path=dataset_config_path,
                    input_size=input_size,
                )

            if format_ == "openvino":
                return OpenVINOINT8Quantizer().quantize(
                    pt_path=pt_path,
                    fp32_openvino_path=fp32_path,
                    int8_openvino_path=int8_path,
                    dataset_config_path=dataset_config_path,
                    input_size=input_size,
                )

            if format_ == "tensorrt":
                export_kwargs = self._build_export_kwargs("engine", QuantizationLevel.INT8.value)
                if export_kwargs is None:
                    raise ModelExportError("Не удалось собрать kwargs для TensorRT INT8")

                exported_path = export_yolo_model(
                    pt_path=pt_path,
                    export_format="engine",
                    target_path=int8_path,
                    export_kwargs=export_kwargs,
                )
                if exported_path.exists():
                    return exported_path
        except (ONNXQuantizationError, OpenVINOQuantizationError, ModelExportError) as error:
            logger.warning(
                "Не удалось подготовить INT8 артефакт для %s%s/%s: %s",
                family,
                size,
                format_,
                error,
            )
            return None
        except Exception:
            logger.exception(
                "Неожиданная ошибка подготовки INT8 артефакта для %s%s/%s",
                family,
                size,
                format_,
            )
            return None

        logger.warning("INT8 quantizer для формата %s не реализован", format_)
        return None

    def _is_quantization_supported(self, format_: str, quantization: str) -> bool:
        """Проверить, есть ли смысл пробовать квантование для формата."""
        if quantization == QuantizationLevel.FP32.value:
            return True

        unsupported_message = (
            "Квантование %s для формата %s сейчас не поддержано, кейс будет пропущен"
        )

        if format_ == "pytorch":
            # .pt остается исходным PyTorch-файлом
            logger.warning(unsupported_message, quantization, format_)
            return False

        if quantization == QuantizationLevel.INT4.value:
            logger.warning("INT4 пока не поддержан через Ultralytics export")
            return False

        supported_formats_by_quantization = {
            QuantizationLevel.FP16.value: {"onnx", "openvino", "tensorrt"},
            QuantizationLevel.INT8.value: {"onnx", "openvino", "tensorrt"},
        }
        supported_formats = supported_formats_by_quantization.get(quantization, set())
        if format_ not in supported_formats:
            logger.warning(unsupported_message, quantization, format_)
            return False

        return True

    def _find_cached_artifact(
        self,
        family: str,
        size: str,
        extension: str,
        quantization: str,
    ) -> Path | None:
        """Найти ранее экспортированный артефакт модели по расширению."""
        candidate = self._build_cached_artifact_path(
            family,
            size,
            extension,
            quantization,
        )
        return candidate if candidate.exists() else None

    def _build_cached_artifact_path(
        self,
        family: str,
        size: str,
        extension: str,
        quantization: str,
    ) -> Path:
        """Собрать имя export-артефакта с учётом типа задачи и квантования."""
        model_stem = self._build_model_stem(family, size)
        if quantization == QuantizationLevel.FP32.value:
            return Path(f"{model_stem}{extension}")
        return Path(f"{model_stem}_{quantization}{extension}")

    def _build_model_stem(self, family: str, size: str) -> str:
        """Собрать базовое имя модели с суффиксом task-specific моделей."""
        return f"{family}{size}{self._get_task_model_suffix()}"

    def _get_task_model_suffix(self) -> str:
        """
        Вернуть суффикс стандартных Ultralytics-моделей для выбранной задачи.

        Для detection суффикса нет: yolov8n.pt.
        Для segment/pose/classify/obb модели обычно называются yolov8n-seg.pt
        и так далее, поэтому без суффикса подтянется не та архитектура.
        """
        suffixes_by_task = {
            TaskType.SEGMENT.value: "-seg",
            TaskType.POSE.value: "-pose",
            TaskType.CLASSIFY.value: "-cls",
            TaskType.OBB.value: "-obb",
        }
        return suffixes_by_task.get(self._get_task_type().value, "")

    def _build_export_kwargs(
        self,
        export_format: str,
        quantization: str,
    ) -> dict[str, object] | None:
        """Собрать параметры YOLO.export() для нужного уровня квантования."""
        export_kwargs: dict[str, object] = {"format": export_format}

        if quantization == QuantizationLevel.FP32.value:
            return export_kwargs

        if quantization == QuantizationLevel.FP16.value:
            export_kwargs["half"] = True
            return export_kwargs

        if quantization == QuantizationLevel.INT8.value:
            dataset_config_path = self._find_quality_dataset_config()
            if dataset_config_path is None:
                logger.warning(
                    "INT8 export требует data.yaml для калибровки, датасет не найден"
                )
                return None

            export_kwargs["int8"] = True
            export_kwargs["data"] = str(dataset_config_path)
            return export_kwargs

        return None

    def _normalize_quantization(self, quantization: str) -> str:
        """Нормализовать значение квантования из конфига."""
        try:
            return QuantizationLevel(quantization).value
        except ValueError:
            logger.warning("Неизвестный уровень квантования %s, используется fp32", quantization)
            return QuantizationLevel.FP32.value

    def _build_yolo_backend(
        self,
        model_path: Path,
        quantization: str = QuantizationLevel.FP32.value,
    ) -> YOLOBackend:
        device = self._normalize_device(self.benchmark_config.device_type)
        task_type = self._get_task_type()
        return YOLOBackend(
            model=YOLO(str(model_path), task=task_type.value),
            device=device,
            category=Coco,
            task_type=task_type,
            threshold=self.benchmark_config.confidence_threshold or 0.25,
            iou=0.7,
            imgsz=self.benchmark_config.input_size or 640,
            half=quantization == QuantizationLevel.FP16.value,
        )

    def _normalize_device(self, device_type: DeviceType | None) -> DeviceType:
        """Преобразует DeviceType enum в значение, поддерживаемое ultralytics.
        
        Значение 'auto' конвертируется в 'cpu' или 'cuda' в зависимости от доступности.
        """
        if device_type is None:
            return DeviceType.CPU
        
        device_str = device_type.value
        
        # Значения, которые ultralytics не поддерживает напрямую
        if device_str == 'auto':
            normalized = 'cuda' if torch.cuda.is_available() else 'cpu'
            return DeviceType(normalized)
        
        if device_str in ('npu', 'gpu', 'tpu', 'tensorrt', 'npu:rk3588', 'npu:intel', 'npu:hailo', 'tpu:coral'):
            logger.warning(f"Device '{device_str}' не поддерживается ultralytics, используется 'cpu'")
        return DeviceType.CPU
        
        return device_type

    def _cleanup_model_resources(self, model: YOLOBackend | None) -> None:
        """Освободить ресурсы модели после одного benchmark-прогона."""
        if model is None:
            return

        raw_model = getattr(model, "model", None)
        self._call_cleanup_method(model)
        self._call_cleanup_method(raw_model)

        predictor = getattr(raw_model, "predictor", None)
        if predictor is not None:
            self._clear_predictor_resources(predictor)

        self._clear_torch_caches()
        self._destroy_cv2_windows()
        gc.collect()

    def _call_cleanup_method(self, value: object | None) -> None:
        """Вызвать close/release, если объект backend это поддерживает."""
        if value is None:
            return

        for method_name in ("close", "release"):
            method = getattr(value, method_name, None)
            if callable(method):
                try:
                    method()
                except Exception as error:
                    logger.debug("Не удалось вызвать %s(): %s", method_name, error)

    def _clear_predictor_resources(self, predictor: object) -> None:
        """Очистить тяжелые ссылки predictor после завершения прогона."""
        for attribute_name in (
            "dataset",
            "vid_writer",
            "plotted_img",
            "results",
            "batch",
        ):
            try:
                setattr(predictor, attribute_name, None)
            except Exception as error:
                logger.debug(
                    "Не удалось очистить predictor.%s: %s",
                    attribute_name,
                    error,
                )

    def _clear_torch_caches(self) -> None:
        """Очистить кэши torch-устройств, если они доступны."""
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            try:
                torch.cuda.ipc_collect()
            except Exception as error:
                logger.debug("Не удалось очистить CUDA IPC cache: %s", error)

        if hasattr(torch, "mps") and torch.backends.mps.is_available():
            try:
                torch.mps.empty_cache()
            except Exception as error:
                logger.debug("Не удалось очистить MPS cache: %s", error)

    def _destroy_cv2_windows(self) -> None:
        """Закрыть окна OpenCV, если backend их создавал."""
        try:
            cv2.destroyAllWindows()
        except Exception as error:
            logger.debug("Не удалось закрыть окна OpenCV: %s", error)

    def _collect_quality_metrics(
        self, model: YOLOBackend, family: str, size: str
    ) -> QualityMetrics | None:
        """Собирает метрики качества модели.
        
        Args:
            model: Загруженная модель для инференса.
            family: Семейство модели.
            size: Размер модели.
            
        Returns:
            QualityMetrics с рассчитанными метриками или None если сбор не удалось выполнить.
        """
        try:
            dataset_config_path = self._find_quality_dataset_config()

            if dataset_config_path is None:
                logger.debug(
                    "Датасет с разметкой не найден для %s%s, пропускаю сбор метрик качества",
                    family,
                    size,
                )
                return None

            logger.info("Собираю метрики качества для %s%s на датасете: %s", 
                       family, size, dataset_config_path)

            collector = YOLOQualityMetricsCollector(
                yolo_backend=model,
                dataset_path=dataset_config_path,
                task_type=self._get_task_type(),
                imgsz=self.benchmark_config.input_size or 640,
                conf_threshold=self.benchmark_config.confidence_threshold or 0.25,
            )
            
            quality_metrics = collector.collect()
            return quality_metrics
            
        except Exception as e:
            logger.warning(
                "Не удалось собрать метрики качества для %s%s: %s",
                family,
                size,
                e,
            )
            return None

    def _find_quality_dataset_config(self) -> Path | None:
        """Найти YAML-конфиг датасета для Ultralytics validation."""
        validation_paths: list[Path] = []

        if self.benchmark_config.test_images is not None:
            benchmark_dataset_path = Path(self.benchmark_config.test_images)
            validation_paths.extend(
                [
                    benchmark_dataset_path / "data.yaml",
                    benchmark_dataset_path.parent / "data.yaml",
                ]
            )

        validation_paths.extend(
            [
                Path("dataset/data.yaml"),
                Path("dataset/val/data.yaml"),
                Path("dataset/validation/data.yaml"),
                Path("dataset/coco/data.yaml"),
                Path("data/val/data.yaml"),
            ]
        )

        for path in validation_paths:
            if path.is_file():
                return path

        return None

    def _warmup(self, backend: YOLOBackend) -> None:
        input_size = self.benchmark_config.input_size or 640
        warmup_iterations = self.benchmark_config.warmup_iterations or 10
        fake_frame = np.zeros((input_size, input_size, 3), dtype=np.uint8)
        for _ in range(warmup_iterations):
            backend.predict(fake_frame)
